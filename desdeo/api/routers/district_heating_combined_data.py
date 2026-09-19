"""Data layer for the JINA combined multi-scenario method.

Where the JINA multi-scenario method (`district_heating_robust_data`) aggregates each objective
to its worst case over the scenarios and asks the decision maker for one aspiration level per
objective, this method drops that aggregation entirely. The combined problem holds one objective
per (objective, scenario) *cell* — plus one for each objective that is shared across scenarios,
because it depends only on the here-and-now decision — and the decision maker sets an aspiration
level for every cell independently.

That is the whole point: worst-case aggregation forces one target to speak for every scenario, so
"zero unmet demand under a demand spike, but a loose cost target under a price spike" cannot be
expressed. Per-cell aspirations can say exactly that, and one ASF solve honours all of them at
once.

Ported from the decision maker's `only-combined-multiscenario-multiobjective.ipynb`. The problem,
scenario model and `JinaMultiScenarioMetaData` settings are shared with the multi-scenario
method — this module reuses that method's cached `JinaScenarioContext` (which already builds the
combined problem) and adds only what is specific to per-cell scalarization.
"""

from __future__ import annotations

import json
import logging
import math
import threading
from dataclasses import dataclass

from desdeo.api.routers.district_heating_robust_data import (
    GUROBI_OPTIONS,
    JinaScenarioContext,
    JinaScenarioError,
    ScalarizerDef,
    get_context,
)
from desdeo.problem.schema import Problem
from desdeo.tools import GurobipySolver, payoff_table_method
from desdeo.tools.partial_scalarization import add_asf_partial_diff
from desdeo.tools.scenarios import build_scenario_problem

logger = logging.getLogger(__name__)

# Matches the notebook. Larger than the multi-scenario method's 1e-3: with 25 competing cells the
# augmentation term is what breaks ties between solutions that share the same max-term value, and
# too small a rho leaves those ties to the solver.
ASF_RHO = 0.01

# `nadir - ideal` can be exactly zero for a cell no design can move (an objective already at its
# bound in that scenario). The ASF requires strictly positive weights, so those collapse to this.
MIN_WEIGHT = 1e-9


@dataclass
class CombinedCell:
    """One (objective, scenario) pair the decision maker can set an aspiration level for."""

    symbol: str
    """The objective symbol in the combined problem, e.g. `price_spike_january_obj1`."""
    obj_symbol: str
    """The base objective this cell measures, e.g. `obj1`."""
    scenario: str
    """The leaf scenario it measures it in. For a shared objective this is every scenario at
    once, and `shared` is True."""
    shared: bool
    """True when the objective does not vary by scenario (it depends only on the first-stage
    decision), so the combined problem carries a single objective for it rather than one per
    scenario. Such a cell appears once, not once per scenario."""
    label: str
    unit: str | None
    maximize: bool
    ideal: float
    nadir: float
    weight: float
    """`max(|nadir - ideal|, MIN_WEIGHT)` — the ASF normalization for this cell."""


@dataclass
class CombinedContext:
    """Everything the combined method needs for one problem, built once and cached."""

    problem_id: int
    base: JinaScenarioContext
    combined_problem: Problem
    cells: list[CombinedCell]
    cells_by_symbol: dict[str, CombinedCell]
    scalarizer_defs: list[ScalarizerDef]
    """One ASF solve per entry: a balanced variant using the decision maker's reference point
    as given, plus one per base objective that asks for more on that objective. Same variants the
    multi-scenario method offers, and the same `emphasis_factor` behind them — the difference is
    only that an emphasis here shifts all of that objective's *cells*, since the reference point
    is per (objective, scenario) rather than per objective."""

    @property
    def symbols(self) -> list[str]:
        return [c.symbol for c in self.cells]

    @property
    def weights(self) -> dict[str, float]:
        return {c.symbol: c.weight for c in self.cells}


_cache: dict[int, CombinedContext] = {}
_cache_lock = threading.Lock()


def get_combined_context(problem_id: int) -> CombinedContext:
    """Cached per problem. Building one runs a payoff table per scenario, so it is far too slow
    to redo per request.
    """
    with _cache_lock:
        ctx = _cache.get(problem_id)
        if ctx is None:
            ctx = _build_combined_context(problem_id)
            _cache[problem_id] = ctx
        return ctx


def invalidate_combined_context(problem_id: int) -> None:
    with _cache_lock:
        _cache.pop(problem_id, None)


def _build_combined_context(problem_id: int) -> CombinedContext:
    base = get_context(problem_id)
    combined = base.combined_problem

    # Per-cell ranges come from a payoff table on each scenario's *standalone* problem, not from
    # the combined problem. A cell's ideal is therefore what that objective could reach if the
    # investment were tailored to that scenario alone — optimistic, and deliberately so: it is
    # the honest upper bound on what an aspiration level there could ever buy. A shared objective
    # gets the envelope (best ideal, worst nadir) across the scenarios, since the same symbol is
    # written once per scenario.
    scenario_model = base_scenario_model(base)

    # Normal operation until a scenario is known. Only problems with information hours get these
    # constraints; for every other problem the combined problem is used exactly as before. They do
    # not change the per-cell ranges, which come from each scenario's standalone problem.
    information_hours = load_information_hours(problem_id)
    if information_hours:
        combined = add_information_constraints(base, scenario_model, combined, information_hours)

    stored = load_stored_cell_ranges(problem_id, base)
    if stored is not None:
        ideal, nadir = stored
        logger.info("Using precomputed cell ranges for problem %s; skipping the payoff tables.", problem_id)
    else:
        ideal, nadir = compute_cell_ranges(base, scenario_model)

    combined_symbols = [o.symbol for o in combined.objectives]
    shared_set = set(base.shared_obj_symbols)

    # Reverse the per-leaf map so a combined symbol can name the cell it came from.
    origin: dict[str, tuple[str, str]] = {}
    for obj, by_leaf in base.per_leaf_obj.items():
        for leaf, sym in by_leaf.items():
            origin[sym] = (obj, leaf)

    cells: list[CombinedCell] = []
    for symbol in combined_symbols:
        obj_symbol, scenario = origin.get(symbol, (symbol, ""))
        if obj_symbol not in base.obj_meta:
            # A combined objective that maps back to nothing this problem declares. Skipping it
            # rather than guessing keeps the DM's grid to cells that actually have a meaning.
            continue
        meta = base.obj_meta[obj_symbol]
        is_shared = obj_symbol in shared_set
        lo = ideal.get(symbol)
        hi = nadir.get(symbol)
        if lo is None or hi is None:
            continue
        cells.append(
            CombinedCell(
                symbol=symbol,
                obj_symbol=obj_symbol,
                scenario="" if is_shared else scenario,
                shared=is_shared,
                label=meta.label,
                unit=meta.unit,
                maximize=meta.maximize,
                ideal=lo,
                nadir=hi,
                weight=max(abs(hi - lo), MIN_WEIGHT),
            )
        )

    if not cells:
        raise JinaScenarioError(
            f"Problem {problem_id}'s combined scenario problem produced no (objective, scenario) "
            "cells — nothing for the decision maker to set aspiration levels on."
        )

    # Balanced first, then one emphasis variant per objective that actually has cells. The order
    # is the priority order used when trimming to `max_solutions`, so the DM's own reference point
    # is never the result that gets dropped.
    cell_obj_symbols = [o for o in base.obj_symbols if any(c.obj_symbol == o for c in cells)]
    scalarizer_defs = [ScalarizerDef(name="balanced", emphasize=None, label="Balanced")]
    scalarizer_defs += [
        ScalarizerDef(name=f"emphasize_{o}", emphasize=o, label=f"Emphasize {base.obj_meta[o].label}")
        for o in cell_obj_symbols
    ]

    return CombinedContext(
        problem_id=problem_id,
        base=base,
        combined_problem=combined,
        cells=cells,
        cells_by_symbol={c.symbol: c for c in cells},
        scalarizer_defs=scalarizer_defs,
    )


def required_cell_symbols(base: JinaScenarioContext) -> list[str]:
    """Every combined-problem symbol the per-cell ranges have to cover.

    A shared objective resolves to the same symbol in every scenario, so it appears once.
    """
    out: list[str] = []
    for obj in base.obj_symbols:
        for leaf in base.all_scenarios:
            symbol = base.per_leaf_obj.get(obj, {}).get(leaf, obj)
            if symbol not in out:
                out.append(symbol)
    return out


def compute_cell_ranges(
    base: JinaScenarioContext, scenario_model: "object"
) -> tuple[dict[str, float], dict[str, float]]:
    """Run one payoff table per scenario to get every cell's attainable range.

    A cell's ideal is what that objective could reach if the investment were tailored to that
    scenario *alone* - optimistic, and deliberately so: it is the honest upper bound on what an
    aspiration level there could ever buy. A shared objective gets the envelope (best ideal, worst
    nadir) across the scenarios, since the same symbol is written once per scenario.

    This is the slow part of a first load, which is why `store_cell_ranges` exists to do it ahead
    of time.
    """

    def solver_factory(p: Problem):
        return GurobipySolver(p, options=GUROBI_OPTIONS)

    ideal: dict[str, float] = {}
    nadir: dict[str, float] = {}
    for leaf in base.all_scenarios:
        try:
            scenario_problem = build_scenario_problem(scenario_model, leaf)
            ideal_s, nadir_s = payoff_table_method(scenario_problem, solver_factory)
        except Exception as e:  # noqa: BLE001
            raise JinaScenarioError(
                f"Could not compute the payoff table for scenario {leaf!r}: {type(e).__name__}: {e}"
            ) from e
        for obj in base.obj_symbols:
            symbol = base.per_leaf_obj.get(obj, {}).get(leaf, obj)
            lo, hi = float(ideal_s[obj]), float(nadir_s[obj])
            ideal[symbol] = min(lo, ideal.get(symbol, lo))
            nadir[symbol] = max(hi, nadir.get(symbol, hi))
    return ideal, nadir


def _jina_metadata_row(session, problem_id: int):
    """The problem's `JinaMultiScenarioMetaData` row, or None if it has none."""
    from desdeo.api.models.problem import ProblemDB

    problem_db = session.get(ProblemDB, problem_id)
    if problem_db is None or problem_db.problem_metadata is None:
        return None
    rows = problem_db.problem_metadata.jina_multiscenario_metadata or []
    return rows[0] if rows else None


def load_stored_cell_ranges(
    problem_id: int, base: JinaScenarioContext
) -> tuple[dict[str, float], dict[str, float]] | None:
    """Precomputed ranges for this problem, or None to compute them live.

    Deliberately strict: anything short of a complete, numerically sane set for exactly the cells
    this problem has now returns None and the ranges are recomputed. The stored values are only an
    optimisation, so a stale or partial cache must cost time, never correctness - a wrong range
    would silently mis-scale every aspiration level in the ASF.
    """
    from sqlmodel import Session

    from desdeo.api.db import engine

    try:
        with Session(engine) as session:
            row = _jina_metadata_row(session, problem_id)
            stored = dict(row.combined_cell_ranges or {}) if row is not None else {}
    except Exception:  # noqa: BLE001 - a cache read must never be able to break the method
        logger.exception("Could not read stored cell ranges for problem %s; recomputing.", problem_id)
        return None

    if not stored:
        return None

    needed = required_cell_symbols(base)
    missing = [sym for sym in needed if sym not in stored]
    if missing:
        logger.info(
            "Stored cell ranges for problem %s cover %d of %d cells (missing e.g. %s); recomputing.",
            problem_id,
            len(needed) - len(missing),
            len(needed),
            missing[:3],
        )
        return None

    ideal: dict[str, float] = {}
    nadir: dict[str, float] = {}
    for sym in needed:
        pair = stored[sym]
        try:
            lo, hi = float(pair[0]), float(pair[1])
        except (TypeError, ValueError, IndexError):
            logger.warning("Stored range for %s on problem %s is malformed; recomputing.", sym, problem_id)
            return None
        if not (math.isfinite(lo) and math.isfinite(hi)):
            logger.warning("Stored range for %s on problem %s is not finite; recomputing.", sym, problem_id)
            return None
        ideal[sym] = lo
        nadir[sym] = hi
    return ideal, nadir


def store_cell_ranges(problem_id: int) -> int:
    """Compute every cell's range for a problem and save it on its metadata row.

    Returns how many cells were stored. Raises `JinaScenarioError` if the problem has no
    `JinaMultiScenarioMetaData` row to attach them to - that row is where the method's other
    per-problem settings live, so a problem without one is not set up for this method at all.
    """
    from sqlmodel import Session

    from desdeo.api.db import engine

    base = get_context(problem_id)
    scenario_model = base_scenario_model(base)
    ideal, nadir = compute_cell_ranges(base, scenario_model)

    payload = {sym: [ideal[sym], nadir[sym]] for sym in required_cell_symbols(base) if sym in ideal}

    with Session(engine) as session:
        row = _jina_metadata_row(session, problem_id)
        if row is None:
            raise JinaScenarioError(
                f"Problem {problem_id} has no JinaMultiScenarioMetaData row to store cell ranges on."
            )
        row.combined_cell_ranges = payload
        session.add(row)
        session.commit()

    invalidate_combined_context(problem_id)
    return len(payload)


def load_information_hours(problem_id: int) -> dict[str, int] | None:
    """The problem's `JinaMultiScenarioMetaData.information_hours`, or None when it has none.

    None - every problem registered without it - leaves the operation anticipative, as before.
    """
    from sqlmodel import Session

    from desdeo.api.db import engine

    with Session(engine) as session:
        row = _jina_metadata_row(session, problem_id)
        hours = getattr(row, "information_hours", None) if row is not None else None
    return {str(name): int(hour) for name, hour in hours.items()} if hours else None


def add_information_constraints(
    base: JinaScenarioContext, scenario_model: "object", combined: Problem, information_hours: dict[str, int]
) -> Problem:
    """Non-anticipativity: before its information hour, a scenario operates exactly like the baseline.

    For every scenario in `information_hours` and every scenario-specific hourly variable x:
    `x_scenario[t] == x_baseline[t]` for every hour t before the information hour. The operator sees
    an hour's data before deciding it, so decisions may differ from the information hour on. An
    information hour is never later than the scenario's first disrupted hour, so linking each
    scenario to the baseline also ties together any two scenarios that are both still unknown.

    The baseline is the problem's `baseline_scenario` setting, else the first scenario whose name
    contains "baseline". Only this method adds these constraints; the two-stage robustness method
    keeps using the context's combined problem as it is.
    """
    from desdeo.problem import Constraint, ConstraintTypeEnum
    from desdeo.tools.scenarios import build_combined_scenario_problem

    leaves = list(base.all_scenarios)
    baseline = base.settings.baseline_scenario or next((s for s in leaves if "baseline" in s.lower()), leaves[0])
    unknown = sorted(set(information_hours) - set(leaves))
    if unknown or baseline not in leaves:
        raise JinaScenarioError(
            f"information_hours names unknown scenario(s) {unknown}, or baseline {baseline!r} is not a scenario."
        )

    # Rebuilt only for its variable map, which the context does not keep; the problem itself is
    # the context's combined problem.
    _, symbol_maps = build_combined_scenario_problem(scenario_model)
    shapes = {v.symbol: getattr(v, "shape", None) for v in base.problem.variables}
    combined_vars = {v.symbol for v in combined.variables}

    constraints = []
    for scenario, hour in sorted(information_hours.items()):
        if scenario == baseline:
            continue
        for symbol, per_leaf in sorted(symbol_maps["variables"].items()):
            if len(set(per_leaf.values())) == 1:
                continue  # shared first-stage variable
            shape = shapes.get(symbol)
            if not shape:
                continue  # a scenario-specific scalar has no hours to align
            shared = min(int(hour), int(shape[0]))
            if shared <= 0:
                continue
            a, b = per_leaf[scenario], per_leaf[baseline]
            if a not in combined_vars or b not in combined_vars:
                raise JinaScenarioError(f"Variable {a!r} or {b!r} is not in the combined problem.")
            index = ["Tuple", 1, shared]  # 1-based, inclusive
            constraints.append(
                Constraint(
                    name=f"normal operation {symbol}: {scenario} = {baseline} for hours 1..{shared}",
                    symbol=f"NA_{scenario}__{baseline}__{symbol}",
                    func=["Subtract", ["Extract", a, index], ["Extract", b, index]],
                    cons_type=ConstraintTypeEnum.EQ,
                    is_linear=True,
                )
            )
    return combined.add_constraints(constraints) if constraints else combined


def base_scenario_model(base: JinaScenarioContext):
    """The `ScenarioModel` behind a context, rebuilt from the DB row it was created from.

    `JinaScenarioContext` keeps the scenario model's id rather than the model itself, so the
    per-scenario payoff tables above have to reload it.
    """
    from sqlmodel import Session

    from desdeo.api.db import engine
    from desdeo.api.models.scenario import ScenarioModelDB

    with Session(engine) as session:
        sm_db = session.get(ScenarioModelDB, base.scenario_model_id)
        if sm_db is None:
            raise JinaScenarioError(f"Scenario model {base.scenario_model_id} not found.")
        return sm_db.to_scenario_model(base.problem)


@dataclass
class CombinedCellResult:
    symbol: str
    aspiration: float
    achieved: float
    scaled: float
    """`(achieved - aspiration) / weight` — the cell's contribution to the max term. Every cell
    is on this one common scale, which is what lets them be compared at all."""
    binds: bool
    """True when this cell's scaled value equals the ASF's optimum `alpha`, i.e. it is one of the
    cells the solution is limited by. Relaxing a binding cell is what buys improvement elsewhere;
    relaxing a non-binding one buys nothing."""


@dataclass
class CombinedIterationResult:
    scalarizer: str
    """Which variant produced this — `balanced`, or `emphasize_<objective>`."""
    alpha: float
    all_reached: bool
    cell_results: list[CombinedCellResult]
    strategic_values: dict[str, float]
    objective_values: dict[str, float]


def build_shifted_reference_point(
    cctx: CombinedContext, g: dict[str, float], emphasize: str | None
) -> dict[str, float]:
    """Ask for more on one objective, using the same generic-ASF shift the other JINA methods use:
    `g_i' = ideal_i + (g_i - ideal_i) / emphasis_factor`.

    The difference from the multi-scenario method is only in what "one objective" means here. That
    method's reference point has a single level per objective, so a shift touches one number; this
    one's is per (objective, scenario) cell, so emphasising an objective shifts *every* cell of it,
    each toward its own per-scenario ideal. Emphasising a single cell instead would give one
    variant per cell — 25 solves for a decision the DM expressed per objective.

    The balanced variant returns the reference point untouched, so it reproduces exactly what a
    single-solve iteration would have produced.
    """
    if emphasize is None:
        return dict(g)

    factor = cctx.base.settings.emphasis_factor or 1.0
    shifted = dict(g)
    for cell in cctx.cells:
        if cell.obj_symbol != emphasize or cell.symbol not in shifted:
            continue
        shifted[cell.symbol] = cell.ideal + (shifted[cell.symbol] - cell.ideal) / factor
    return shifted


def run_combined_iteration(
    cctx: CombinedContext, reference_point: dict[str, float]
) -> list[CombinedIterationResult]:
    """Solve every scalarizer variant against the decision maker's per-cell aspiration levels.

    Each variant is the *same* scalarization of the *same* combined problem — `add_asf_partial_diff`
    with the same per-cell weights and rho. Only the reference point differs, so nothing about how
    this method optimizes changes by adding variants; there are simply more starting points, and
    the balanced one still reproduces the single-solve result exactly.

    Variants solve concurrently: Gurobi releases the GIL during optimization, so the wall-clock
    cost of five solves is far below five times one. A variant that fails or comes back
    non-optimal is skipped rather than failing the round — with the reference point shifted toward
    an ideal, an emphasis variant can legitimately be harder than the balanced one. If *every*
    variant fails, that is a real error and is raised.
    """
    from concurrent.futures import ThreadPoolExecutor

    g = {sym: float(reference_point[sym]) for sym in cctx.symbols}

    with ThreadPoolExecutor(max_workers=len(cctx.scalarizer_defs)) as pool:
        futures = {pool.submit(_solve_variant, cctx, g, sdef): sdef for sdef in cctx.scalarizer_defs}
        solved = {futures[fut].name: fut.result() for fut in futures}

    # Kept in `scalarizer_defs` order — balanced first — which is the priority order the caller
    # trims in when the decision maker asks for fewer solutions.
    results = [solved[sdef.name] for sdef in cctx.scalarizer_defs if solved[sdef.name] is not None]
    if not results:
        raise JinaScenarioError(
            "No scalarizer variant reached optimality for these aspiration levels. Levels far "
            "below a cell's ideal can make the scalarized problem hard or infeasible."
        )
    return results


def _solve_variant(
    cctx: CombinedContext, g_base: dict[str, float], sdef: ScalarizerDef
) -> CombinedIterationResult | None:
    """One ASF solve for one variant. Runs on a worker thread; returns None if it does not solve.

    Returns what each cell asked for, what it got, and which cells bind — the binding set is the
    actionable part of the answer, since those are the only aspirations whose relaxation would
    free anything up. Note the aspirations reported are the *shifted* ones this variant actually
    solved against, not the DM's originals, so `scaled` and `binds` stay internally consistent.
    """
    weights = cctx.weights
    g = build_shifted_reference_point(cctx, g_base, sdef.emphasize)

    try:
        asf_problem, target = add_asf_partial_diff(
            cctx.combined_problem, f"ASF_{sdef.name}", g, weights=weights, weights_aug=weights, rho=ASF_RHO
        )
        result = GurobipySolver(asf_problem, options=GUROBI_OPTIONS).solve(target)
    except Exception:  # noqa: BLE001 - one variant failing must not sink the whole round
        return None

    if not result.success:
        return None

    alpha = float(result.optimal_variables["_alpha"])
    objective_values = {sym: float(result.optimal_objectives[sym]) for sym in cctx.symbols}

    cell_results = []
    for cell in cctx.cells:
        achieved = objective_values[cell.symbol]
        scaled = (achieved - g[cell.symbol]) / cell.weight
        cell_results.append(
            CombinedCellResult(
                symbol=cell.symbol,
                aspiration=g[cell.symbol],
                achieved=achieved,
                scaled=scaled,
                # Same tolerance the notebook prints with; alpha is a scaled quantity, so this is
                # a comparison between two O(1) numbers rather than between raw objective values.
                binds=abs(scaled - alpha) < 1e-6,
            )
        )

    strategic_values = {
        sym: float(result.optimal_variables[sym])
        for sym in cctx.base.strategic_symbols
        if sym in result.optimal_variables
    }

    return CombinedIterationResult(
        scalarizer=sdef.name,
        alpha=alpha,
        # alpha <= 0 means the max term never had to exceed zero: every cell reached at least the
        # level it asked for.
        all_reached=alpha <= 0,
        cell_results=cell_results,
        strategic_values=strategic_values,
        objective_values=objective_values,
    )


# --------------------------------------------------------------------------------------------
# Per-scenario breakdown, design bookkeeping, and the wish-list analysis
# --------------------------------------------------------------------------------------------


def scenario_breakdown(cctx: CombinedContext, objective_values: dict[str, float]) -> list[dict]:
    """Re-key one solve's per-cell values into one row per scenario, in *base* objective symbols.

    This is the shape the trade-off/per-scenario views and `compute_robustness_metrics` both want,
    and it is free here: an ASF solve on the combined problem already produces every scenario's
    outcome, where the multi-scenario method has to read them out of a worst-case wrapper. A
    shared objective has no per-scenario cell, so its single value is repeated into every row —
    correct by construction, since it takes the same value in all of them.
    """
    shared_by_obj = {c.obj_symbol: c.symbol for c in cctx.cells if c.shared}
    per_scenario: dict[tuple[str, str], str] = {
        (c.obj_symbol, c.scenario): c.symbol for c in cctx.cells if not c.shared
    }

    rows = []
    for scenario in cctx.base.all_scenarios:
        row: dict = {"scenario": scenario}
        for obj in cctx.base.obj_symbols:
            symbol = per_scenario.get((obj, scenario)) or shared_by_obj.get(obj)
            if symbol is not None and symbol in objective_values:
                row[obj] = objective_values[symbol]
        rows.append(row)
    return rows


def design_signature(cctx: CombinedContext, strategic_values: dict[str, float]) -> tuple[int, ...]:
    """Rounded first-stage capacities, at the problem's configured dedup tolerance.

    Two iterations that land on the same physical build should be recognised as the same design
    even when the solver returns values that differ in the last decimals, which is what lets a
    design keep its solution number when it resurfaces in a later round.
    """
    tol = cctx.base.settings.design_tolerance or 1.0
    return tuple(round(float(strategic_values.get(sym, 0.0)) / tol) for sym in cctx.base.strategic_symbols)


def compute_combined_analysis(
    cctx: CombinedContext,
    design_registry: dict[int, dict],
    wish_list_ids: list[int],
    domain_thresholds: dict[str, float] | None = None,
) -> dict:
    """Domain criterion over the wish-listed designs.

    Reuses `compute_robustness_metrics` from the pool-matching method (it is pool-schema-agnostic)
    on a long frame built from each design's per-scenario breakdown. The domain criterion counts,
    per design and objective, how many scenarios meet that objective's threshold — a direct answer
    to "how often does this build actually hold up", which the per-cell aspirations alone do not
    give.

    Deliberately narrower than the multi-scenario method's `compute_wish_list_analysis`: no max
    regret and no antifragility. Both of those normalize against a *pool* of designs, and this
    method discovers one design per iteration, so with a handful of rounds that normalization
    would be too weak to report honestly.

    Known limitation, shared with the multi-scenario method: `maximize=True` objectives are not
    sign-adjusted — `compute_robustness_metrics` assumes every objective is minimized. Every
    objective this has been used with so far is a minimize objective.
    """
    import pandas as pd

    from desdeo.api.routers.district_heating_system_data import compute_robustness_metrics

    thresholds = (
        domain_thresholds
        if domain_thresholds is not None
        else (cctx.base.settings.default_domain_thresholds or {})
    )
    wish_design_ids = sorted(set(wish_list_ids))

    rows = []
    for design_id, entry in design_registry.items():
        if design_id not in wish_design_ids:
            continue
        for row in entry.get("breakdown", []):
            rows.append(
                {
                    "source_design_scenario": "combined",
                    "reference_id": design_id,
                    "scalarizer": "n/a",
                    "target_operation_scenario": row["scenario"],
                    **{obj: row[obj] for obj in cctx.base.obj_symbols if obj in row},
                }
            )

    if not rows or not thresholds:
        return {
            "wish_list": wish_design_ids,
            "domain_criterion": [],
            "domain_thresholds": thresholds,
            "scenario_count": len(cctx.base.all_scenarios),
        }

    wish_clean = pd.DataFrame(rows)
    robustness = compute_robustness_metrics(wish_clean, cctx.base.obj_symbols, thresholds=thresholds)
    domain_df = robustness["domain_criterion"].rename(columns={"reference_id": "design_id"})

    return {
        "wish_list": wish_design_ids,
        "domain_criterion": json.loads(domain_df.to_json(orient="records")) if not domain_df.empty else [],
        "domain_thresholds": thresholds,
        "scenario_count": len(cctx.base.all_scenarios),
    }
