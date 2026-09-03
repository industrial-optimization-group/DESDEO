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
import threading
from dataclasses import dataclass

from desdeo.api.routers.district_heating_robust_data import (
    GUROBI_OPTIONS,
    JinaScenarioContext,
    JinaScenarioError,
    get_context,
)
from desdeo.problem.schema import Problem
from desdeo.tools import GurobipySolver, payoff_table_method
from desdeo.tools.partial_scalarization import add_asf_partial_diff
from desdeo.tools.scenarios import build_scenario_problem

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
    def solver_factory(p: Problem):
        return GurobipySolver(p, options=GUROBI_OPTIONS)

    scenario_model = base_scenario_model(base)

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

    return CombinedContext(
        problem_id=problem_id,
        base=base,
        combined_problem=combined,
        cells=cells,
        cells_by_symbol={c.symbol: c for c in cells},
    )


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
    alpha: float
    all_reached: bool
    cell_results: list[CombinedCellResult]
    strategic_values: dict[str, float]
    objective_values: dict[str, float]


def run_combined_iteration(
    cctx: CombinedContext, reference_point: dict[str, float]
) -> CombinedIterationResult:
    """One ASF solve against per-cell aspiration levels.

    Returns what each cell asked for, what it got, and which cells bind — the binding set is the
    actionable part of the answer, since those are the only aspirations whose relaxation would
    free anything up.
    """
    weights = cctx.weights
    g = {sym: float(reference_point[sym]) for sym in cctx.symbols}

    try:
        asf_problem, target = add_asf_partial_diff(
            cctx.combined_problem, "ASF", g, weights=weights, weights_aug=weights, rho=ASF_RHO
        )
        result = GurobipySolver(asf_problem, options=GUROBI_OPTIONS).solve(target)
    except Exception as e:  # noqa: BLE001
        raise JinaScenarioError(f"ASF solve failed: {type(e).__name__}: {e}") from e

    if not result.success:
        raise JinaScenarioError(
            "The solver did not reach optimality for these aspiration levels "
            f"({result.message}). Aspiration levels far below a cell's ideal can make the "
            "scalarized problem hard or infeasible."
        )

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
