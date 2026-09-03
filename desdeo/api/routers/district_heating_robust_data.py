"""Data/solving layer for the JINA multi-scenario robust interactive method.

Generic: works with any `ProblemDB` that has an attached `ScenarioModelDB` whose
`anticipation_stop` declares at least one shared, first-stage ("strategic") variable. District
heating was the first problem this served, ported from a decision maker's own notebooks — it is
no longer special-cased here. See `desdeo/api/db_init_district_heating.py` for how it (and any
future problem) gets registered into the standard `ProblemDB`/`ScenarioModelDB` tables that this
module reads from.

Builds a real `desdeo.problem.Problem`, combines it across every leaf scenario into one *robust*
(worst-case) problem via `desdeo.tools.robust.add_worst_case_robust`, and solves it live with
Gurobi on every iteration. Building the context (payoff table included) is slow — cached per
`problem_id`.
"""

from __future__ import annotations

import json
import threading
from collections import defaultdict
from dataclasses import dataclass, field

from sqlmodel import Session

from desdeo.api.db import engine
from desdeo.api.models.problem import JinaMultiScenarioMetaData, ProblemDB
from desdeo.api.routers.district_heating_system_data import (
    DistrictHeatingDataError,
    JinaPoolError,
    compute_antifragility_metrics,
    compute_robustness_metrics,
    get_pool_context,
    load_candidate_pool,
)
from desdeo.problem.schema import Problem
from desdeo.tools import GurobipySolver, payoff_table_method
from desdeo.tools.partial_scalarization import add_asf_partial_diff
from desdeo.tools.robust import add_worst_case_robust
from desdeo.tools.scenarios import build_combined_scenario_problem

GUROBI_OPTIONS = {"OutputFlag": 0}


class JinaScenarioError(RuntimeError):
    """Raised when a problem can't be used with the JINA multi-scenario method — no scenario
    model attached, or its scenario model declares no shared first-stage variables.
    """


# --------------------------------------------------------------------------------------------
# Context: everything derived from one problem_id, built once and cached.
# --------------------------------------------------------------------------------------------


@dataclass
class ObjectiveMeta:
    symbol: str
    name: str
    unit: str | None
    maximize: bool
    label: str


@dataclass
class StrategicVarMeta:
    symbol: str
    name: str
    label: str
    component: str
    unit: str | None
    axis_max: float | None


@dataclass
class ScalarizerDef:
    name: str
    emphasize: str | None  # objective symbol, or None for the "balanced" variant
    label: str


@dataclass
class JinaSettings:
    """Resolved per-problem settings (from `JinaMultiScenarioMetaData`, or generic defaults if
    a problem hasn't configured any — every field is meaningful with no override).
    """

    default_domain_thresholds: dict[str, float] | None = None
    default_af_absolute_floors: dict[str, float] | None = None
    design_tolerance: float = 1.0
    emphasis_factor: float = 3.0
    baseline_scenario: str | None = None
    compound_scenario_hook: str | None = None
    compound_reference_hook: str | None = None
    regret_pool_source: str | None = None
    strategic_var_labels: dict[str, str] = field(default_factory=dict)
    strategic_var_components: dict[str, str] = field(default_factory=dict)
    strategic_var_units: dict[str, str] = field(default_factory=dict)


@dataclass
class JinaScenarioContext:
    """Everything needed to run the JINA multi-scenario method against one problem."""

    problem_id: int
    scenario_model_id: int
    problem: Problem
    robust_problem: Problem
    combined_problem: Problem
    """The un-aggregated combined problem: one objective per (base objective, leaf scenario)
    pair, plus one for each objective that is shared across scenarios. `robust_problem` is this
    with a worst-case-over-scenarios layer on top. Kept because the combined multi-scenario
    method (`district_heating_combined_data`) scalarizes these per-cell objectives directly
    instead of their worst case, and rebuilding it costs a full scenario-model expansion."""
    robust_symbol_map: dict[str, str]
    per_leaf_obj: dict[str, dict[str, str]]
    ideal: dict[str, float]
    nadir: dict[str, float]
    aug_weights: dict[str, float]
    all_scenarios: list[str]
    obj_symbols: list[str]
    obj_meta: dict[str, ObjectiveMeta]
    varying_obj_symbols: list[str]
    shared_obj_symbols: list[str]
    strategic_symbols: list[str]
    strategic_meta: dict[str, StrategicVarMeta]
    scalarizer_defs: list[ScalarizerDef]
    global_ideal_obj: dict[str, float]
    global_nadir_obj: dict[str, float]
    settings: JinaSettings


def _resolve_settings(problem_db: ProblemDB) -> JinaSettings:
    meta_row: JinaMultiScenarioMetaData | None = None
    if problem_db.problem_metadata is not None:
        rows = problem_db.problem_metadata.jina_multiscenario_metadata or []
        meta_row = rows[0] if rows else None

    if meta_row is None:
        return JinaSettings()

    return JinaSettings(
        default_domain_thresholds=meta_row.default_domain_thresholds,
        default_af_absolute_floors=meta_row.default_af_absolute_floors,
        design_tolerance=meta_row.design_tolerance,
        emphasis_factor=meta_row.emphasis_factor,
        baseline_scenario=meta_row.baseline_scenario,
        compound_scenario_hook=meta_row.compound_scenario_hook,
        compound_reference_hook=meta_row.compound_reference_hook,
        regret_pool_source=meta_row.regret_pool_source,
        strategic_var_labels=meta_row.strategic_var_labels or {},
        strategic_var_components=meta_row.strategic_var_components or {},
        strategic_var_units=meta_row.strategic_var_units or {},
    )


_context_cache: dict[int, JinaScenarioContext] = {}
_context_locks: "defaultdict[int, threading.Lock]" = defaultdict(threading.Lock)


def get_context(problem_id: int) -> JinaScenarioContext:
    """Get (building and caching if needed) the `JinaScenarioContext` for a problem.

    Building is slow (~1 minute — one payoff-table solve over the combined robust problem), so
    it's cached per `problem_id`. A per-`problem_id` lock means two concurrent first-requests
    for *different* problems don't serialize behind one build; two requests for the *same*
    uncached problem do (correctly) wait for the first to finish rather than both paying the
    cost.
    """
    if problem_id in _context_cache:
        return _context_cache[problem_id]

    with _context_locks[problem_id]:
        if problem_id in _context_cache:  # someone else finished building while we waited
            return _context_cache[problem_id]
        ctx = _build_context(problem_id)
        _context_cache[problem_id] = ctx
        return ctx


def invalidate_context(problem_id: int) -> None:
    """Drop a cached context — e.g. after re-seeding a problem's scenario model."""
    _context_cache.pop(problem_id, None)


def _build_context(problem_id: int) -> JinaScenarioContext:  # noqa: PLR0914
    with Session(engine) as session:
        problem_db = session.get(ProblemDB, problem_id)
        if problem_db is None:
            raise JinaScenarioError(f"Problem {problem_id} not found.")

        scenario_models = problem_db.scenario_models
        if not scenario_models:
            raise JinaScenarioError(
                f"Problem {problem_id} ({problem_db.name!r}) has no attached scenario model — "
                "JINA multi-scenario needs a ScenarioModelDB row linked to it via "
                "base_problem_id. See desdeo/api/db_init_district_heating.py for how to build "
                "and attach one."
            )
        sm_db = scenario_models[0]

        problem = Problem.from_problemdb(problem_db)
        scenario_model = sm_db.to_scenario_model(problem)

        strategic_symbols_set = {sym for syms in scenario_model.anticipation_stop.values() for sym in syms}
        if not strategic_symbols_set:
            raise JinaScenarioError(
                f"Problem {problem_id} ({problem_db.name!r})'s scenario model declares no "
                "shared first-stage (anticipation_stop) variables — JINA multi-scenario needs "
                "at least one."
            )
        strategic_symbols = [v.symbol for v in problem.variables if v.symbol in strategic_symbols_set]

        settings = _resolve_settings(problem_db)

        combined, symbol_maps = build_combined_scenario_problem(scenario_model)
        obj_symbols = [o.symbol for o in problem.objectives]
        robust_problem, robust_symbol_map = add_worst_case_robust(
            scenario_model, obj_symbols, combined=combined, symbol_maps=symbol_maps
        )

        def solver_factory(p):
            return GurobipySolver(p, options=GUROBI_OPTIONS)

        ideal, nadir = payoff_table_method(robust_problem, solver_factory)
        robust_problem = robust_problem.update_ideal_and_nadir(ideal, nadir)

        robust_syms = list(robust_symbol_map.values())
        aug_weights = {sym: nadir[sym] - ideal[sym] for sym in robust_syms}
        global_ideal_obj = {obj: float(ideal[robust_symbol_map[obj]]) for obj in obj_symbols}
        global_nadir_obj = {obj: float(nadir[robust_symbol_map[obj]]) for obj in obj_symbols}

        all_scenarios = sorted(scenario_model.leaf_scenarios)

        per_leaf_obj: dict[str, dict[str, str]] = symbol_maps.get("objectives", {})
        varying_obj_symbols = [
            o for o in obj_symbols if any(per_leaf_obj.get(o, {}).get(leaf, o) != o for leaf in all_scenarios)
        ]
        shared_obj_symbols = [o for o in obj_symbols if o not in varying_obj_symbols]

        obj_by_symbol = {o.symbol: o for o in problem.objectives}
        obj_meta: dict[str, ObjectiveMeta] = {}
        for sym in obj_symbols:
            o = obj_by_symbol[sym]
            label = f"{o.name} ({o.unit})" if o.unit else o.name
            obj_meta[sym] = ObjectiveMeta(symbol=sym, name=o.name, unit=o.unit, maximize=o.maximize, label=label)

        var_by_symbol = {v.symbol: v for v in problem.variables}
        strategic_meta: dict[str, StrategicVarMeta] = {}
        for sym in strategic_symbols:
            v = var_by_symbol[sym]
            label = settings.strategic_var_labels.get(sym, v.name)
            component = settings.strategic_var_components.get(sym, sym)
            unit = settings.strategic_var_units.get(sym)
            axis_max = float(v.upperbound) if v.upperbound is not None else None
            strategic_meta[sym] = StrategicVarMeta(
                symbol=sym, name=v.name, label=label, component=component, unit=unit, axis_max=axis_max
            )

        scalarizer_defs = [ScalarizerDef(name="balanced", emphasize=None, label="Balanced")]
        scalarizer_defs += [
            ScalarizerDef(name=f"emphasize_{sym}", emphasize=sym, label=f"Emphasize {obj_meta[sym].label}")
            for sym in obj_symbols
        ]

        return JinaScenarioContext(
            problem_id=problem_id,
            scenario_model_id=sm_db.id,
            problem=problem,
            robust_problem=robust_problem,
            combined_problem=combined,
            robust_symbol_map=robust_symbol_map,
            per_leaf_obj=per_leaf_obj,
            ideal=ideal,
            nadir=nadir,
            aug_weights=aug_weights,
            all_scenarios=all_scenarios,
            obj_symbols=obj_symbols,
            obj_meta=obj_meta,
            varying_obj_symbols=varying_obj_symbols,
            shared_obj_symbols=shared_obj_symbols,
            strategic_symbols=strategic_symbols,
            strategic_meta=strategic_meta,
            scalarizer_defs=scalarizer_defs,
            global_ideal_obj=global_ideal_obj,
            global_nadir_obj=global_nadir_obj,
            settings=settings,
        )


# --------------------------------------------------------------------------------------------
# Reference points
# --------------------------------------------------------------------------------------------


def reference_point_from_percent(ctx: JinaScenarioContext, percent: dict[str, float]) -> dict[str, float]:
    out = {}
    for obj, pct in percent.items():
        frac = max(0.0, min(100.0, float(pct))) / 100.0
        out[obj] = ctx.global_nadir_obj[obj] + frac * (ctx.global_ideal_obj[obj] - ctx.global_nadir_obj[obj])
    return out


def reference_point_from_raw(ctx: JinaScenarioContext, values: dict[str, float]) -> dict[str, float]:
    missing = [o for o in ctx.obj_symbols if o not in values]
    if missing:
        raise ValueError(f"Missing objectives: {missing}. Must provide all of {ctx.obj_symbols}")
    return {obj: float(values[obj]) for obj in ctx.obj_symbols}


# --------------------------------------------------------------------------------------------
# Iteration
# --------------------------------------------------------------------------------------------


def _signature(ctx: JinaScenarioContext, strategic_vals: dict[str, float]) -> tuple[int, ...]:
    tol = ctx.settings.design_tolerance
    return tuple(round(float(strategic_vals[s]) / tol) for s in ctx.strategic_symbols)


def _build_shifted_rp(ctx: JinaScenarioContext, g: dict[str, float], emphasize: str | None) -> dict[str, float]:
    """Same generic-ASF shift formula as the pool-matching method: g_i' = ideal_i + (g_i - ideal_i)/w_i."""
    if emphasize is None:
        return dict(g)
    g_shifted = dict(g)
    robust_sym = ctx.robust_symbol_map[emphasize]
    ideal_i = ctx.ideal[robust_sym]
    g_shifted[robust_sym] = ideal_i + (g[robust_sym] - ideal_i) / ctx.settings.emphasis_factor
    return g_shifted


@dataclass
class SolvedDesign:
    scalarizer: str
    robust_vals: dict[str, float]
    strategic_vals: dict[str, float]
    breakdown: list[dict]


def _solve_one(ctx: JinaScenarioContext, g_robust: dict[str, float], sdef: ScalarizerDef, symbol: str) -> SolvedDesign | None:
    """Solve one scalarizer variant against the robust problem. Runs on a worker thread —
    Gurobi releases the GIL during optimization, so all variants can solve concurrently.
    """
    g_used = _build_shifted_rp(ctx, g_robust, sdef.emphasize)
    try:
        scalarized, target = add_asf_partial_diff(
            ctx.robust_problem, symbol, g_used, weights_aug=ctx.aug_weights, rho=1e-3
        )
        result = GurobipySolver(scalarized, options=GUROBI_OPTIONS).solve(target)
    except Exception:  # noqa: BLE001 - mirrors the notebook's own catch-and-skip
        return None
    if not result.success:
        return None

    robust_vals = {obj: float(result.optimal_objectives[ctx.robust_symbol_map[obj]]) for obj in ctx.obj_symbols}
    strategic_vals = {s: float(result.optimal_variables[s]) for s in ctx.strategic_symbols}

    breakdown = []
    for sc in ctx.all_scenarios:
        row = {"scenario": sc}
        for obj in ctx.obj_symbols:
            resolved_sym = ctx.per_leaf_obj.get(obj, {}).get(sc, obj)
            row[obj] = float(result.optimal_objectives[resolved_sym])
        breakdown.append(row)

    return SolvedDesign(scalarizer=sdef.name, robust_vals=robust_vals, strategic_vals=strategic_vals, breakdown=breakdown)


def run_iteration(
    ctx: JinaScenarioContext,
    g_robust: dict[str, float],
    iteration_number: int,
    design_registry: dict[int, dict],
    solution_number_map: dict[int, int],
    max_solutions: int | None = None,
) -> list[dict]:
    """Solve every scalarizer variant (concurrently), dedup by first-stage design signature into
    `design_registry` (mutated in place, never pruned — permanent for the session), and flag
    `repeat` when a design resurfaces in a later iteration (it cannot be excluded, since every
    variant re-solves live each time).

    `max_solutions` only trims how many distinct designs are returned/highlighted *this round* —
    every scalarizer variant still solves live regardless (needed to know which designs exist at
    all), and every discovered design is still added to `design_registry`, so nothing is lost from
    the Strategic Design Explorer or wish list; it's a display cap, not a speed optimization. When
    trimming is needed, designs are kept in scalarizer-priority order (balanced first, then each
    objective's emphasis variant) — the same order `ctx.scalarizer_defs` itself is built in.
    """
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=len(ctx.scalarizer_defs)) as pool:
        futures = {
            pool.submit(_solve_one, ctx, g_robust, sdef, f"ASF_{sdef.name}_it{iteration_number}"): sdef
            for sdef in ctx.scalarizer_defs
        }
        solved_by_variant = {futures[fut].name: fut.result() for fut in futures}

    matches: dict[int, list[str]] = {}
    is_repeat: dict[int, bool] = {}
    next_design_id = max(design_registry.keys(), default=0) + 1

    for sdef in ctx.scalarizer_defs:
        solved = solved_by_variant[sdef.name]
        if solved is None:
            continue

        signature = _signature(ctx, solved.strategic_vals)
        existing_id = next((did for did, e in design_registry.items() if e["signature"] == signature), None)

        if existing_id is None:
            design_id = next_design_id
            next_design_id += 1
            design_registry[design_id] = {
                "signature": signature,
                "first_iteration": iteration_number,
                "scalarizer": solved.scalarizer,
                "robust_vals": solved.robust_vals,
                "strategic_vals": solved.strategic_vals,
                "breakdown": solved.breakdown,
            }
            is_repeat[design_id] = False
        else:
            design_id = existing_id
            is_repeat[design_id] = design_registry[design_id]["first_iteration"] != iteration_number

        if design_id not in solution_number_map:
            solution_number_map[design_id] = max(solution_number_map.values(), default=0) + 1

        matches.setdefault(design_id, []).append(sdef.name)

    if max_solutions is not None and len(matches) > max_solutions:
        matches = dict(list(matches.items())[:max_solutions])

    solutions_this_round = []
    for design_id, scalarizer_names in matches.items():
        entry = design_registry[design_id]
        breakdown = entry["breakdown"]
        worst_case = {}
        best_case = {}
        for obj in ctx.obj_symbols:
            vals = [row[obj] for row in breakdown]
            if ctx.obj_meta[obj].maximize:
                worst_case[obj], best_case[obj] = min(vals), max(vals)
            else:
                worst_case[obj], best_case[obj] = max(vals), min(vals)
        solutions_this_round.append(
            {
                "design_id": design_id,
                "solution_number": solution_number_map[design_id],
                "matched_by": scalarizer_names,
                "repeat": is_repeat.get(design_id, False),
                "breakdown": breakdown,
                "worst_case": worst_case,
                "best_case": best_case,
            }
        )

    return solutions_this_round


# --------------------------------------------------------------------------------------------
# Strategic Design Explorer
# --------------------------------------------------------------------------------------------


def strategic_axis_max(ctx: JinaScenarioContext) -> dict[str, float | None]:
    """Upper bound of each strategic (first-stage) variable, read from the built `Problem`
    itself — `None` for an unbounded variable (legal for a generic problem; the frontend falls
    back to the observed max across discovered designs in that case).
    """
    return {sym: ctx.strategic_meta[sym].axis_max for sym in ctx.strategic_symbols}


def list_strategic_designs(ctx: JinaScenarioContext, design_registry: dict[int, dict], solution_number_map: dict[int, int]) -> list[dict]:
    """One row per unique design discovered this session — strategic variable values, the
    scalarizer that discovered it, and its worst-case robust objectives. Purely a read/reshape
    of the already-solved `design_registry` — no new solving.
    """
    rows = []
    for design_id, entry in sorted(design_registry.items()):
        rows.append(
            {
                "design_id": design_id,
                "solution_number": solution_number_map.get(design_id, design_id),
                "scalarizer": entry.get("scalarizer", "n/a"),
                "first_iteration": entry.get("first_iteration"),
                "strategic_vals": {sym: float(entry["strategic_vals"][sym]) for sym in ctx.strategic_symbols},
                "robust_vals": {obj: float(entry["robust_vals"][obj]) for obj in ctx.obj_symbols},
                "breakdown": entry["breakdown"],
            }
        )
    return rows


# --------------------------------------------------------------------------------------------
# Robustness + antifragility analysis
# --------------------------------------------------------------------------------------------


def compute_wish_list_analysis(
    ctx: JinaScenarioContext,
    design_registry: dict[int, dict],
    wish_list_ids: list[int],
    domain_thresholds: dict[str, float] | None = None,
    af_absolute_floors: dict[str, float] | None = None,
) -> dict:
    """Robustness + antifragility analysis, reusing `compute_robustness_metrics`/
    `compute_antifragility_metrics` (imported, not re-ported) from the pool-matching method —
    they're pool-schema-agnostic. Fed from this method's own session-discovered
    `design_registry` instead of a precomputed CSV pool.

    Known limitation: objectives with `maximize=True` are not yet sign-adjusted here (both
    helper functions assume every given objective is to be minimized) — every objective this
    method has actually been used with so far is a minimize objective. A maximize objective
    would need its columns negated before calling and results un-negated after; left as a
    documented gap rather than shipped unverified.
    """
    domain_thresholds = domain_thresholds if domain_thresholds is not None else (ctx.settings.default_domain_thresholds or {})
    af_absolute_floors = af_absolute_floors if af_absolute_floors is not None else (ctx.settings.default_af_absolute_floors or {})

    wish_design_ids = sorted(set(wish_list_ids))

    rows = []
    for design_id, entry in design_registry.items():
        for row in entry["breakdown"]:
            rows.append(
                {
                    "source_design_scenario": "pool",
                    "reference_id": design_id,
                    "scalarizer": "n/a",
                    "target_operation_scenario": row["scenario"],
                    **{obj: row[obj] for obj in ctx.obj_symbols},
                }
            )
    import pandas as pd

    full_clean = pd.DataFrame(rows)
    if full_clean.empty:
        return {
            "wish_list": wish_design_ids,
            "max_regret": [],
            "domain_criterion": [],
            "antifragility_summary": [],
            "antifragility_deviations": [],
            "af_objectives": [],
            "baseline_scenario": ctx.all_scenarios[0] if ctx.all_scenarios else "",
            "domain_thresholds": domain_thresholds,
            "af_absolute_floors": af_absolute_floors,
        }

    # Domain criterion stays session-pool-only (each wish-listed design's own value against a
    # fixed threshold doesn't benefit from more designs).
    wish_clean = full_clean[full_clean["reference_id"].isin(wish_design_ids)].copy()

    # Max regret and antifragility are normalized *relative to the pool of designs discovered so
    # far* — with only a handful of live-solved designs that normalization is weak. If this
    # problem is configured with a precomputed regret pool (district heating's own
    # pairwise_transfer_matrix_long.csv), blend it in for tighter normalization, namespacing its
    # `reference_id`s under "csv_" so they can never collide with (or be wish-listed as) this
    # session's own integer design ids.
    regret_pool = full_clean
    if ctx.settings.regret_pool_source == "district_heating_csv":
        try:
            pool_ctx = get_pool_context(ctx.problem_id)
            csv_pool_df = load_candidate_pool(pool_ctx).pool_transfer[
                ["source_design_scenario", "reference_id", "scalarizer", "target_operation_scenario", *ctx.obj_symbols]
            ].copy()
            csv_pool_df["reference_id"] = "csv_" + csv_pool_df["reference_id"].astype(str)
            regret_pool = pd.concat([full_clean, csv_pool_df], ignore_index=True)
        except (DistrictHeatingDataError, JinaPoolError):
            pass  # this problem has no pool metadata configured — fall back to session-only pool

    robustness = compute_robustness_metrics(regret_pool, ctx.obj_symbols, thresholds=domain_thresholds)
    max_regret_df = robustness["max_regret"].rename(columns={"reference_id": "design_id"})
    max_regret_df = max_regret_df[max_regret_df["design_id"].isin(wish_design_ids)]

    domain_df = pd.DataFrame()
    if wish_design_ids:
        wish_robustness = compute_robustness_metrics(wish_clean, ctx.obj_symbols, thresholds=domain_thresholds)
        domain_df = wish_robustness["domain_criterion"].rename(columns={"reference_id": "design_id"})

    baseline_scenario = (
        ctx.settings.baseline_scenario
        or next((s for s in ctx.all_scenarios if "baseline" in s.lower()), ctx.all_scenarios[0])
    )
    af_pool = compute_antifragility_metrics(
        regret_pool, ctx.obj_symbols, baseline_scenario=baseline_scenario, absolute_floors=af_absolute_floors
    )
    af_all = af_pool["summary"].rename(columns={"reference_id": "design_id"})
    af_dev_all = af_pool["deviations"].rename(columns={"reference_id": "design_id"})

    af_objectives = [o for o in ctx.varying_obj_symbols if (af_all[f"{o}_U"] > 1e-9).any()]

    af_wish = af_all[af_all["design_id"].isin(wish_design_ids)].copy()
    for o in af_objectives:
        af_wish[f"{o}_AF_pctile"] = af_wish[f"{o}_AF"].apply(lambda v, obj=o: 100.0 * (af_all[f"{obj}_AF"] < v).mean())
    af_dev_wish = af_dev_all[af_dev_all["design_id"].isin(wish_design_ids)].copy()

    def records(df: "pd.DataFrame") -> list[dict]:
        if df.empty:
            return []
        return json.loads(df.to_json(orient="records"))

    return {
        "wish_list": wish_design_ids,
        "max_regret": records(max_regret_df),
        "domain_criterion": records(domain_df),
        "antifragility_summary": records(af_wish),
        "antifragility_deviations": records(af_dev_wish),
        "af_objectives": af_objectives,
        "baseline_scenario": baseline_scenario,
        "domain_thresholds": domain_thresholds,
        "af_absolute_floors": af_absolute_floors,
    }
