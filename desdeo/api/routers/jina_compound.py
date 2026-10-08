"""Generic compound-disruption stress test for the JINA multi-scenario method.

Re-evaluates candidate designs under combinations of disruptions a problem defines, via a
per-problem plug-in hook. Combining two scenarios' overrides generically isn't derivable from
`ScenarioModel` alone: if two scenarios both override the same underlying constants (as disruption
scenarios typically do), a symbol-level merge can only pick one side's value, not "both applied at
once" — that needs a "perturbation over a shared baseline" notion `ScenarioModel` doesn't have. So
this stays a hook: a problem's `JinaMultiScenarioMetaData.compound_scenario_hook` names a
"module.path:function" string that, given the problem's `JinaScenarioContext`, returns a
`CompoundScenarioSet`. A problem with no hook configured simply doesn't support this stress test —
see `district_heating_compound.py` for the one existing implementation.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import pandas as pd

from desdeo.api.routers.district_heating_robust_data import GUROBI_OPTIONS, JinaScenarioContext, JinaScenarioError
from desdeo.problem.schema import Problem
from desdeo.tools import GurobipySolver
from desdeo.tools.design_fixing import asf_at_reference_point, asf_weights_from_ideal_nadir, fix_variables


@dataclass
class CompoundScenarioSet:
    """N named deterministic problems to stress-test candidate designs against.

    The strategic variables are NOT yet fixed — that happens per design at solve time.

    That happens per design at solve time) to stress-test candidate designs against.
    """

    names: list[str]
    problems: dict[str, Problem]
    description: str | None = None
    pair_components: dict[str, tuple[str, str]] | None = None
    """For a combo set built by pairing two "reference" scenarios (e.g. two single disruptions),
    maps each combo name to the pair of reference-scenario names it was built from — lets
    `compute_superadditivity` know which two rows of a separate reference `CompoundScenarioSet` to
    subtract. `None` for a scenario set that isn't pair-structured (or a reference set itself,
    which doesn't need this)."""


def resolve_hook(spec: str) -> Callable[[JinaScenarioContext], CompoundScenarioSet]:
    """Resolve a 'module.path:function' string to the actual function."""
    module_path, _, func_name = spec.partition(":")
    if not module_path or not func_name:
        raise JinaScenarioError(f"Malformed compound_scenario_hook {spec!r}, expected 'module.path:function'.")
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise JinaScenarioError(f"Could not import compound-scenario hook module {module_path!r}: {e}") from e
    try:
        return getattr(module, func_name)
    except AttributeError as e:
        raise JinaScenarioError(f"Module {module_path!r} has no function {func_name!r}.") from e


def _solve_combo_one(
    problem_fixed: Problem,
    obj_symbols: list[str],
    combo_name: str,
    design_id: int,
    reference_point: dict[str, float],
    weights: dict[str, float],
    label: str,
) -> dict:
    def solver_factory(p):
        return GurobipySolver(p, options=GUROBI_OPTIONS)

    obj_vals, status = asf_at_reference_point(
        problem_fixed, solver_factory, obj_symbols, reference_point, weights, label=label
    )
    return {"design_id": design_id, "combined_scenario": combo_name, "status": status, **obj_vals}


def run_compound_analysis(
    ctx: JinaScenarioContext,
    scenario_set: CompoundScenarioSet,
    design_registry: dict[int, dict],
    candidate_ids: list[int],
    reference_point: dict[str, float],
) -> list[dict]:
    """Re-evaluate every candidate design under every combined scenario, with one ASF solve each.

    For each candidate design and each combined scenario, the design's strategic variables are fixed and ONE ASF is
    solved against `reference_point` — so each row is the objective vector of a single achievable recourse decision,
    and the DM steers the re-evaluation the same way they steered the search that produced the designs.

    This replaces a payoff-table re-evaluation (one independent solve per objective), which
    returned each pair's ideal point: four values from four different recourse decisions, a row no
    operating plan achieves. It is also one solve per pair instead of `len(obj_symbols)`.

    Normalization is `|nadir - ideal|` from the problem's *global* worst-case ideal/nadir, shared
    by every pair, so rows stay comparable across designs and scenarios — the whole point of
    plotting them together.

    The combos for one design solve concurrently (Gurobi releases the GIL), same pattern as
    `run_iteration`.
    """
    weights = asf_weights_from_ideal_nadir(ctx.global_ideal_obj, ctx.global_nadir_obj, ctx.obj_symbols)
    rows: list[dict] = []
    for design_id in candidate_ids:
        fixed_design = {sym: design_registry[design_id]["strategic_vals"][sym] for sym in ctx.strategic_symbols}
        with ThreadPoolExecutor(max_workers=max(len(scenario_set.names), 1)) as pool:
            futures = []
            for combo_name in scenario_set.names:
                label = f"d{design_id}_{combo_name}"
                problem_fixed = fix_variables(scenario_set.problems[combo_name], fixed_design, label)
                futures.append(
                    pool.submit(
                        _solve_combo_one,
                        problem_fixed,
                        ctx.obj_symbols,
                        combo_name,
                        design_id,
                        reference_point,
                        weights,
                        label,
                    )
                )
            rows.extend(fut.result() for fut in futures)
    return rows


def summarize_compound_results(
    ctx: JinaScenarioContext,
    rows: list[dict],
    candidate_ids: list[int],
    design_registry: dict[int, dict],
    solution_number_map: dict[int, int],
) -> list[dict]:
    """Worst compound-disruption case vs. single-disruption worst case (`robust_vals`), per candidate and objective.

    A large gap means compound disruptions expose real additional risk that single-disruption robustness testing
    misses.
    """
    df = pd.DataFrame(rows)
    summary_rows = []
    for design_id in candidate_ids:
        ok_rows = df[(df["design_id"] == design_id) & (df["status"] == "ok")] if not df.empty else df
        row = {"design_id": design_id, "solution_number": solution_number_map.get(design_id, design_id)}
        for obj in ctx.obj_symbols:
            single_val = design_registry[design_id]["robust_vals"][obj]
            row[f"{obj}_single_robust"] = single_val
            if ok_rows.empty:
                row[f"{obj}_combo_worst"] = None
                row[f"{obj}_worst_combo"] = None
                row[f"{obj}_gap"] = None
            else:
                maximize = ctx.obj_meta[obj].maximize
                idx = ok_rows[obj].idxmin() if maximize else ok_rows[obj].idxmax()
                combo_worst = float(ok_rows.loc[idx, obj])
                row[f"{obj}_combo_worst"] = combo_worst
                row[f"{obj}_worst_combo"] = str(ok_rows.loc[idx, "combined_scenario"])
                row[f"{obj}_gap"] = (single_val - combo_worst) if maximize else (combo_worst - single_val)
        summary_rows.append(row)
    return summary_rows


def compute_superadditivity(
    obj_symbols: list[str],
    combo_rows: list[dict],
    reference_rows: list[dict],
    pair_components: dict[str, tuple[str, str]],
) -> None:
    """Add each (design, combo) row's super-additivity, in place.

    Mutates `combo_rows` in place, adding `{obj}_superadd` to every (design, combo) row whose
    baseline/A-alone/B-alone reference values are all feasible:

        super_add = combined - (baseline + (A_alone - baseline) + (B_alone - baseline))
                  = combined + baseline - A_alone - B_alone

    Positive = super-additive (the pair is worse than the sum of its two single-disruption
    effects — the interaction a compound-disruption test exists to catch). Negative =
    sub-additive (the disruptions overlap/saturate). Requires a `reference_rows` entry named
    "baseline" plus one for each name `pair_components` refers to, per design.
    """
    ref_lookup = {(r["design_id"], r["combined_scenario"]): r for r in reference_rows if r.get("status") == "ok"}
    for row in combo_rows:
        if row.get("status") != "ok":
            continue
        combo_name = row["combined_scenario"]
        components = pair_components.get(combo_name)
        if components is None:
            continue
        a_name, b_name = components
        design_id = row["design_id"]
        base = ref_lookup.get((design_id, "baseline"))
        ref_a = ref_lookup.get((design_id, a_name))
        ref_b = ref_lookup.get((design_id, b_name))
        if base is None or ref_a is None or ref_b is None:
            continue
        for obj in obj_symbols:
            row[f"{obj}_superadd"] = row[obj] + base[obj] - ref_a[obj] - ref_b[obj]
