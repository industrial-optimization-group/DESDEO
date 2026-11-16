"""JINA: interactive reference-point method for finding designs of scenario-based problems.

The decision maker gives a reference point over *targets*: aggregated objectives (worst case,
expected value or CVaR over the leaf scenarios) or per-leaf objective values.  The combined scenario
problem is scalarised with a partial ASF for a balanced variant and one variant per emphasised
objective, and the first-stage (design) variables of each solution form a design.  Designs found
earlier can be scored against a new reference point with numpy alone.

All public functions take and return values in the objectives' original direction.
"""

import math
import warnings
from collections.abc import Callable, Hashable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Literal, get_args

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from desdeo.problem import Constraint, ConstraintTypeEnum, Problem, ScalarizationFunction
from desdeo.problem.scenario import ScenarioModel
from desdeo.tools.generics import BaseSolver
from desdeo.tools.partial_scalarization import add_asf_partial_diff
from desdeo.tools.robust import add_worst_case_robust
from desdeo.tools.scenario_designs import design_from_values, outcomes_from_combined
from desdeo.tools.scenarios import build_combined_scenario_problem, build_scenario_problem
from desdeo.tools.stochastic import add_conditional_value_at_risk, add_expected_value

View = Literal["aggregated", "per_scenario"]
Measure = Literal["worst_case", "expected_value", "cvar"]
DesignId = Hashable

_BINDING_TOL = 1e-5
_PARETO_TOL = 1e-6


class Target(BaseModel):
    """One scalarised quantity of a JINA problem."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(description="Objective symbol of the target in the built problem.")
    objective: str = Field(description="The original objective symbol.")
    leaf: str | None = Field(description="The leaf of a per-leaf target; None for a target over all leaves.")
    leaves: tuple[str, ...] = Field(description="The leaves whose values the target depends on.")
    maximize: bool = Field(description="Whether the target is maximised.")


@dataclass(frozen=True)
class JinaProblem:
    """A combined scenario problem with the objectives the targets refer to."""

    problem: Problem
    symbol_maps: dict[str, dict[str, dict[str, str]]]
    targets: list[Target]
    view: View
    measure: Measure
    probabilities: dict[str, float]
    cvar_alpha: float


class VariantResult(BaseModel):
    """Result of solving one scalarised variant of a JINA problem."""

    name: str = Field(description="'balanced' or 'emphasis_<objective>'.")
    success: bool = Field(description="Whether the variant was solved successfully.")
    message: str = Field(description="Solver message, or the error raised.")
    effective_reference_point: dict[str, float] = Field(description="The reference point used, by target.")
    target_values: dict[str, float] = Field(
        default={}, description="Target values of the solution, aggregated from its per-leaf objective values."
    )
    leaf_objectives: dict[str, dict[str, float]] = Field(
        default={}, description="Objective values of the solution by leaf and original objective symbol."
    )
    design: dict[str, float | list] = Field(default={}, description="Design variable values of the solution.")
    alpha: float | None = Field(default=None, description="Optimal value of the ASF auxiliary variable.")
    binding: list[str] = Field(
        default=[], description="Targets whose ASF term equals alpha, or else the targets with the largest term."
    )


def build_jina_problem(
    model: ScenarioModel, view: View, measure: Measure = "worst_case", *, cvar_alpha: float = 0.9
) -> JinaProblem:
    """Build the combined scenario problem of a model and its targets.

    In the ``"per_scenario"`` view each objective of each leaf is a target.  In the ``"aggregated"``
    view each objective present in every leaf is aggregated over the leaves with ``measure``, and
    objectives present in only some leaves stay per-leaf targets.  An objective that is identical in
    every leaf is a single target over all leaves in both views.  Targets are ordered by objective
    (base-problem objectives first) and then by leaf.

    Args:
        model: the scenario model.
        view: ``"aggregated"`` or ``"per_scenario"``.
        measure: the aggregation used in the aggregated view: ``"worst_case"``, ``"expected_value"``
            (probability-weighted) or ``"cvar"``.
        cvar_alpha: the CVaR confidence level.

    Returns:
        The JINA problem.

    Raises:
        ValueError: if ``view`` or ``measure`` is unknown.
    """
    if view not in get_args(View):
        raise ValueError(f"Unknown view '{view}'.")
    if measure not in get_args(Measure):
        raise ValueError(f"Unknown measure '{measure}'.")
    combined, symbol_maps = build_combined_scenario_problem(model)
    leaves = tuple(model.leaf_scenarios)
    maximize = {obj.symbol: obj.maximize for obj in combined.objectives}
    obj_maps = symbol_maps["objectives"]
    base_order = [obj.symbol for obj in model.base_problem.objectives if obj.symbol in obj_maps]
    order = base_order + [sym for sym in obj_maps if sym not in base_order]

    targets: list[Target] = []
    aggregate: list[str] = []
    for sym in order:
        per_leaf = obj_maps[sym]
        if all(new_sym == sym for new_sym in per_leaf.values()):
            targets.append(Target(symbol=sym, objective=sym, leaf=None, leaves=leaves, maximize=maximize[sym]))
        elif view == "aggregated" and len(per_leaf) == len(leaves):
            aggregate.append(sym)
            targets.append(Target(symbol=sym, objective=sym, leaf=None, leaves=leaves, maximize=False))
        else:
            targets += [
                Target(symbol=new_sym, objective=sym, leaf=leaf, leaves=(leaf,), maximize=maximize[new_sym])
                for leaf, new_sym in per_leaf.items()
            ]

    if aggregate:
        if measure == "worst_case":
            combined, added = add_worst_case_robust(model, aggregate, combined=combined, symbol_maps=symbol_maps)
        elif measure == "expected_value":
            combined, added = add_expected_value(model, aggregate, combined=combined, symbol_maps=symbol_maps)
        else:
            combined, added = add_conditional_value_at_risk(
                model, aggregate, alpha=cvar_alpha, combined=combined, symbol_maps=symbol_maps
            )
        maximize = {obj.symbol: obj.maximize for obj in combined.objectives}
        targets = [
            t.model_copy(update={"symbol": added[t.symbol], "maximize": maximize[added[t.symbol]]})
            if t.symbol in added
            else t
            for t in targets
        ]

    return JinaProblem(
        problem=combined,
        symbol_maps=symbol_maps,
        targets=targets,
        view=view,
        measure=measure,
        probabilities=dict(model.leaf_scenarios),
        cvar_alpha=cvar_alpha,
    )


def target_values(jp: JinaProblem, leaf_objectives: dict[str, dict[str, float]]) -> dict[str, float]:
    """Compute the target values of a JINA problem from per-leaf objective values.

    Uses `aggregate_outcomes` with the measure, leaf probabilities and CVaR level of ``jp``.

    Args:
        jp: the JINA problem.
        leaf_objectives: objective values by leaf and original objective symbol, e.g., of an
            evaluated or imported design.

    Returns:
        The target values by target symbol; targets missing a leaf value are omitted.
    """
    return aggregate_outcomes(
        jp.targets, leaf_objectives, jp.measure, probabilities=jp.probabilities, cvar_alpha=jp.cvar_alpha
    )


def _pareto_row(
    problem: Problem,
    sym: str,
    symbols: list[str],
    *,
    stage_1: dict[str, float],
    best: float,
    solver: type[BaseSolver],
    solver_options: Any,
) -> dict[str, float] | None:
    """Minimise the other objectives with ``sym`` kept at its optimum; return the optimal objectives or None.

    ``best`` is the optimum of ``sym`` in the minimisation space, and each other objective is
    scaled by ``max(1, |its stage-1 value|)``.
    """
    maximize = {obj.symbol: obj.maximize for obj in problem.objectives}
    term = {other: f"(-1 * {other})" if maximize[other] else other for other in symbols}
    bound = best + _PARETO_TOL * max(1.0, abs(best))
    others = " + ".join(f"{term[other]} / {max(1.0, abs(stage_1[other]))}" for other in symbols if other != sym)
    flags = {
        "is_linear": problem.is_linear,
        "is_convex": problem.is_convex,
        "is_twice_differentiable": problem.is_twice_differentiable,
    }
    row_problem = problem.add_constraints(
        [
            Constraint(
                name=f"Optimum of {sym}",
                symbol="_payoff_bound",
                func=f"{term[sym]} - {bound}",
                cons_type=ConstraintTypeEnum.LTE,
                **flags,
            )
        ]
    ).add_scalarization(ScalarizationFunction(name="Other objectives", symbol="_payoff_others", func=others, **flags))
    try:
        results = solver(row_problem, solver_options).solve("_payoff_others")
    except Exception:
        return None
    return results.optimal_objectives if results.success else None


def _payoff(
    problem: Problem,
    symbols: list[str],
    solver: type[BaseSolver],
    solver_options: Any,
    *,
    where: str,
    values: Callable[[dict[str, float]], dict[str, float]] = dict,
    pareto_rows: bool = True,
) -> dict[str, tuple[float, float]]:
    """Return ``(ideal, nadir)`` of the given objectives from a payoff table of the problem.

    Row ``i`` first minimises objective ``i``, which gives its ideal.  With ``pareto_rows``, the
    other objectives are then minimised (scaled, in the minimisation space) with objective ``i``
    kept at its optimum, so that the row is Pareto optimal; if that fails, the first-stage row is
    used with a warning.  ``values`` maps the optimal objective values of a solve to the values
    of ``symbols``.
    """
    maximize = {obj.symbol: obj.maximize for obj in problem.objectives}
    instance = None
    ideals: dict[str, float] = {}
    rows: dict[str, dict[str, float]] = {}
    for sym in symbols:
        try:
            instance = instance or solver(problem, solver_options)
            results = instance.solve(f"{sym}_min")
        except Exception as e:
            raise RuntimeError(f"Optimising '{sym}' in {where} raised {type(e).__name__}: {e}") from e
        if not results.success:
            raise RuntimeError(f"Optimising '{sym}' in {where} failed: {results.message}")
        rows[sym] = values(results.optimal_objectives)
        ideals[sym] = rows[sym][sym]
        if pareto_rows and len(symbols) > 1:
            best = (-1.0 if maximize[sym] else 1.0) * float(results.optimal_objectives[sym])
            row = _pareto_row(
                problem, sym, symbols, stage_1=rows[sym], best=best, solver=solver, solver_options=solver_options
            )
            if row is None:
                warnings.warn(
                    f"Minimising the other objectives at the optimum of '{sym}' in {where} failed; "
                    "using the first-stage payoff row.",
                    stacklevel=3,
                )
            else:
                rows[sym] = values(row)
    worst = {sym: min if maximize[sym] else max for sym in symbols}
    return {sym: (float(ideals[sym]), float(worst[sym](row[sym] for row in rows.values()))) for sym in symbols}


def target_ranges(
    jp: JinaProblem,
    model: ScenarioModel,
    solver: type[BaseSolver],
    *,
    solver_options: Any = None,
    pareto_rows: bool = True,
) -> dict[str, tuple[float, float]]:
    """Estimate the ideal and nadir of every target with payoff tables.

    A per-leaf target gets the ideal and nadir of its objective from the payoff table over all
    objectives of its leaf's scenario problem.  Targets over all leaves get them from a payoff table
    over all targets on the JINA problem, with values aggregated from the per-leaf objective values
    of each payoff solution.  Each row first optimises its target, which gives the ideal; with
    ``pareto_rows`` it then optimises the other targets with that target kept at its optimum, so
    that slack or free recourse cannot inflate the nadir.

    Args:
        jp: the JINA problem.
        model: the scenario model the JINA problem was built from.
        solver: the solver class.
        solver_options: options passed to the solver.
        pareto_rows: whether to make each payoff row Pareto optimal with a second solve.

    Returns:
        ``(ideal, nadir)`` by target symbol.

    Raises:
        RuntimeError: if a payoff table solve fails; the message names the leaf or problem and target.
    """
    ranges: dict[str, tuple[float, float]] = {}
    for leaf in dict.fromkeys(t.leaf for t in jp.targets if t.leaf is not None):
        leaf_problem = build_scenario_problem(model, leaf)
        payoff = _payoff(
            leaf_problem,
            [obj.symbol for obj in leaf_problem.objectives],
            solver,
            solver_options,
            where=f"leaf '{leaf}'",
            pareto_rows=pareto_rows,
        )
        ranges |= {t.symbol: payoff[t.objective] for t in jp.targets if t.leaf == leaf}
    if any(t.leaf is None for t in jp.targets):
        payoff = _payoff(
            jp.problem,
            [t.symbol for t in jp.targets],
            solver,
            solver_options,
            where="the combined problem",
            values=lambda objective_values: target_values(jp, outcomes_from_combined(objective_values, jp.symbol_maps)),
            pareto_rows=pareto_rows,
        )
        ranges |= {t.symbol: payoff[t.symbol] for t in jp.targets if t.leaf is None}
    return {t.symbol: ranges[t.symbol] for t in jp.targets}


def shift_reference_point(
    reference_point: dict[str, float],
    targets: list[Target],
    ranges: dict[str, tuple[float, float]],
    emphasize: str | None,
    factor: float,
) -> dict[str, float]:
    """Move the reference point of every target of one objective toward its ideal.

    Each target ``t`` of the objective gets ``ideal_t + (q_t - ideal_t) / factor``.

    Args:
        reference_point: aspiration levels by target symbol.
        targets: the targets.
        ranges: ``(ideal, nadir)`` by target symbol.
        emphasize: the original objective symbol to emphasise, or None for no shift.
        factor: how many times closer to the ideal the shifted aspiration levels are.

    Returns:
        The shifted reference point, a new dict.

    Raises:
        ValueError: if an emphasised target in the reference point has no range.
    """
    shifted = dict(reference_point)
    for t in targets:
        if t.objective != emphasize or t.symbol not in shifted:
            continue
        if ranges.get(t.symbol) is None:
            raise ValueError(f"No range for target '{t.symbol}'.")
        ideal = ranges[t.symbol][0]
        shifted[t.symbol] = ideal + (shifted[t.symbol] - ideal) / factor
    return shifted


def _weights(
    reference_point: dict[str, float], ranges: dict[str, tuple[float, float]] | None, *, warn: bool = True
) -> dict[str, float]:
    """Return the ASF weights ``|nadir - ideal|`` of the reference point targets with a nonzero range.

    Targets with a zero estimated range are left out with a warning.  Raises ValueError if a target
    has no range or no target is left.
    """
    ranges = ranges or {}
    if missing := [sym for sym in reference_point if ranges.get(sym) is None]:
        raise ValueError(f"No range for targets {missing}.")
    spans = {sym: abs(ranges[sym][1] - ranges[sym][0]) for sym in reference_point}
    degenerate = [sym for sym, span in spans.items() if not span]
    if len(degenerate) == len(spans):
        raise ValueError(f"No target in the reference point has a nonzero range: {degenerate}.")
    if degenerate and warn:
        warnings.warn(f"Targets {degenerate} have no nonzero range; leaving them out.", stacklevel=3)
    return {sym: span for sym, span in spans.items() if span}


def _solve_variant(
    jp: JinaProblem,
    name: str,
    reference_point: dict[str, float],
    weights: dict[str, float],
    *,
    solver: type[BaseSolver],
    design_variables: list[str],
    rho: float,
    solver_options: Any,
) -> VariantResult:
    """Solve one variant; errors are returned as an unsuccessful result."""
    try:
        symbol = f"_jina_{name}"
        problem, _ = add_asf_partial_diff(
            jp.problem, symbol, reference_point, weights=weights, weights_aug=weights, rho=rho
        )
        results = solver(problem, solver_options).solve(symbol)
        if not results.success:
            return VariantResult(
                name=name, success=False, message=results.message, effective_reference_point=reference_point
            )

        maximize = {t.symbol: t.maximize for t in jp.targets}
        leaf_objectives = outcomes_from_combined(results.optimal_objectives, jp.symbol_maps)
        values = target_values(jp, leaf_objectives)
        alpha = float(results.optimal_variables["_alpha"])
        scaled = {
            sym: (-1.0 if maximize[sym] else 1.0) * (values[sym] - q) / weights[sym]
            for sym, q in reference_point.items()
        }
        tol = _BINDING_TOL * max(1.0, abs(alpha))
        binding = [sym for sym, term in scaled.items() if abs(term - alpha) < tol]
        if not binding:
            largest = max(scaled.values())
            binding = [sym for sym, term in scaled.items() if largest - term < tol]
        return VariantResult(
            name=name,
            success=True,
            message=results.message,
            effective_reference_point=reference_point,
            target_values=values,
            leaf_objectives=leaf_objectives,
            design=design_from_values(results.optimal_variables, design_variables),
            alpha=alpha,
            binding=binding,
        )
    except Exception as e:
        return VariantResult(
            name=name,
            success=False,
            message=f"{type(e).__name__}: {e}",
            effective_reference_point=reference_point,
        )


def solve_variants(
    jp: JinaProblem,
    reference_point: dict[str, float],
    ranges: dict[str, tuple[float, float]],
    solver: type[BaseSolver],
    *,
    design_variables: list[str],
    emphasis_factor: float = 3.0,
    rho: float = 1e-3,
    solver_options: Any = None,
    max_workers: int = 1,
) -> list[VariantResult]:
    """Solve the balanced variant and one emphasis variant per objective.

    Each variant minimises ``add_asf_partial_diff`` over the targets in the reference point, with
    weights ``|nadir - ideal|`` for both the max term and the augmentation term.  A target with a
    zero estimated range is left out of the scalarisation with a warning; it is
    still reported in the target values.  The emphasis variant
    ``"emphasis_<objective>"`` uses `shift_reference_point` with ``emphasis_factor``.  The variants
    are solved in ``max_workers`` threads; parallel runs need a thread-safe solver, and with Gurobi
    a ``Threads`` limit in ``solver_options``.

    Args:
        jp: the JINA problem.
        reference_point: aspiration levels by target symbol; only these targets are scalarised.
        ranges: ``(ideal, nadir)`` by target symbol.
        solver: the solver class.
        design_variables: the design variable symbols.
        emphasis_factor: the shift factor of the emphasis variants.
        rho: the augmentation coefficient.
        solver_options: options passed to the solver.
        max_workers: the number of threads.

    Returns:
        The results, balanced first and then by objective.  A variant that fails or raises has
        ``success=False``.

    Raises:
        ValueError: if a target in the reference point has no range, no target has a nonzero range,
            or a design variable is not a variable of the JINA problem.
    """
    if missing := [sym for sym in reference_point if ranges.get(sym) is None]:
        raise ValueError(f"No range for targets {missing}.")
    if unknown := sorted(set(design_variables) - {var.symbol for var in jp.problem.variables}):
        raise ValueError(f"Design variables {unknown} are not variables of the JINA problem.")
    weights = _weights(reference_point, ranges)
    active = {sym: reference_point[sym] for sym in weights}
    objectives = dict.fromkeys(t.objective for t in jp.targets if t.symbol in active)
    variants = {"balanced": active} | {
        f"emphasis_{obj}": shift_reference_point(active, jp.targets, ranges, obj, emphasis_factor) for obj in objectives
    }
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(
                _solve_variant,
                jp,
                name,
                rp,
                weights,
                solver=solver,
                design_variables=design_variables,
                rho=rho,
                solver_options=solver_options,
            )
            for name, rp in variants.items()
        ]
        return [future.result() for future in futures]


def leaf_reference_points(
    targets: list[Target], effective_reference_point: dict[str, float]
) -> dict[str, dict[str, float]]:
    """Split a target-keyed reference point into reference points per leaf.

    A target over all leaves gives its value to its objective in every leaf; a per-leaf target only
    in its leaf.  The result can be passed to `evaluate_design` as ``leaf_reference_points``.

    Args:
        targets: the targets.
        effective_reference_point: aspiration levels by target symbol.

    Returns:
        ``{leaf: {objective: aspiration level}}``.
    """
    return _per_leaf(targets, effective_reference_point)


def leaf_ranges(
    targets: list[Target], ranges: dict[str, tuple[float, float]]
) -> dict[str, dict[str, tuple[float, float]]]:
    """Split target ranges into ranges per leaf, as `leaf_reference_points` does.

    The result can be passed to `evaluate_design` as ``leaf_ranges``.

    Args:
        targets: the targets.
        ranges: ``(ideal, nadir)`` by target symbol.

    Returns:
        ``{leaf: {objective: (ideal, nadir)}}``.
    """
    return _per_leaf(targets, ranges)


def objective_ranges(targets: list[Target], ranges: dict[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
    """Combine target ranges into one range per objective.

    The ideal is the best of the objective's target ideals and the nadir the worst of their nadirs, in
    the objective's original direction.  The result can be passed to `evaluate_design` as ``ranges``.

    Args:
        targets: the targets.
        ranges: ``(ideal, nadir)`` by target symbol; targets missing from it or mapped to None are skipped.

    Returns:
        ``{objective: (ideal, nadir)}``.
    """
    combined: dict[str, tuple[float, float]] = {}
    for t in targets:
        if ranges.get(t.symbol) is None:
            continue
        ideal, nadir = ranges[t.symbol]
        if t.objective in combined:
            best, worst = (max, min) if t.maximize else (min, max)
            ideal = best(ideal, combined[t.objective][0])
            nadir = worst(nadir, combined[t.objective][1])
        combined[t.objective] = (ideal, nadir)
    return combined


def _per_leaf(targets: list[Target], values: dict) -> dict[str, dict]:
    """Give each target's value to its objective in every leaf the target covers."""
    per_leaf: dict[str, dict] = {}
    for t in targets:
        if t.symbol in values:
            for leaf in t.leaves:
                per_leaf.setdefault(leaf, {})[t.objective] = values[t.symbol]
    return per_leaf


def aggregate_outcomes(
    targets: list[Target],
    leaf_objectives: dict[str, dict[str, float]],
    measure: Measure,
    *,
    probabilities: dict[str, float] | None = None,
    cvar_alpha: float = 0.9,
) -> dict[str, float]:
    """Compute target values from per-leaf objective values.

    A per-leaf target takes the value of its leaf.  A target over all leaves aggregates them with
    ``measure`` as `build_jina_problem` does: the worst case in the objective's direction, the
    probability-weighted sum, or the CVaR ``min_eta eta + 1 / (1 - alpha) * sum_s p_s * max(v_s - eta, 0)``.
    For a maximised target, the CVaR is that of the negated values, negated back, i.e., the mean of
    the lowest ``1 - alpha`` tail.

    Args:
        targets: the targets.
        leaf_objectives: objective values by leaf and original objective symbol, e.g., the objectives
            of the `LeafOutcome` of each leaf.
        measure: ``"worst_case"``, ``"expected_value"`` or ``"cvar"``.
        probabilities: the leaf probabilities, e.g., ``ScenarioModel.leaf_scenarios``.  Defaults to
            equal probabilities over each target's leaves.
        cvar_alpha: the CVaR confidence level.

    Returns:
        The target values by target symbol.  A target with a leaf missing from ``leaf_objectives``,
        or lacking its objective, is omitted.

    Raises:
        ValueError: if ``measure`` is unknown.
    """
    if measure not in ("worst_case", "expected_value", "cvar"):
        raise ValueError(f"Unknown measure '{measure}'.")

    values: dict[str, float] = {}
    for t in targets:
        if any(t.objective not in leaf_objectives.get(leaf, {}) for leaf in t.leaves):
            continue
        v = np.array([leaf_objectives[leaf][t.objective] for leaf in t.leaves], dtype=float)
        if t.leaf is not None:
            values[t.symbol] = float(v[0])
            continue
        p = np.array([probabilities[leaf] for leaf in t.leaves]) if probabilities else np.full(len(v), 1 / len(v))
        if measure == "worst_case":
            values[t.symbol] = float(v.min() if t.maximize else v.max())
        elif measure == "expected_value":
            values[t.symbol] = float(p @ v)
        else:
            sign = -1.0 if t.maximize else 1.0
            v = sign * v
            # Piecewise linear and convex in eta, so the minimum is at one of the values.
            cvar = min(eta + (p @ np.maximum(v - eta, 0.0)) / (1 - cvar_alpha) for eta in v)
            values[t.symbol] = sign * float(cvar)
    return values


def score_designs(
    target_values: dict[DesignId, dict[str, float]],
    reference_point: dict[str, float],
    ranges: dict[str, tuple[float, float]],
    targets: list[Target],
    method: Literal["asf", "guess", "stom"],
    *,
    rho: float = 1e-3,
    delta: float = 1e-6,
    emphasize: str | None = None,
    factor: float = 3.0,
    warn: bool = True,
) -> dict[DesignId, float]:
    """Score designs by their target values against a reference point; lower is better.

    Only the targets in the reference point with a nonzero range are scored; targets with a zero
    estimated range are left out with a warning.  In the minimisation space (maximised
    targets negated), with aspiration levels ``q``, ideal ``z*`` and nadir ``z_nad`` from ``ranges``:

    * ``"asf"``: ``max_i (f_i - q_i) / w_i + rho * sum_i f_i / w_i`` with ``w_i = |nadir_i - ideal_i|``,
      the value `solve_variants` minimises.
    * ``"guess"``: ``max_{i not free} (f_i - z_nad_i) / (z_nad_i - q_i) + rho * sum_i f_i / d_i``,
      where ``i`` is free when ``q_i >= z_nad_i``, ``d_i = z_nad_i - z*_i`` if free and
      ``z_nad_i - q_i`` otherwise (as `add_guess_sf_diff`).  The max term is 0 when all are free, and
      denominators are at least ``delta``.
    * ``"stom"``: ``max_i (f_i - z*_i + delta) / (q_i - z*_i + delta) + rho * sum_i f_i / (q_i - z*_i + delta)``
      (as `add_stom_sf_diff`), with ``q_i`` clipped to at least ``z*_i + delta``.

    Args:
        target_values: target values by design id.
        reference_point: aspiration levels by target symbol.
        ranges: ``(ideal, nadir)`` by target symbol.
        targets: the targets.
        method: ``"asf"``, ``"guess"`` or ``"stom"``.
        rho: the augmentation coefficient.
        delta: the utopian offset of ``"stom"`` and smallest denominator of ``"guess"``.
        emphasize: an original objective symbol whose targets' aspiration levels are first shifted
            with `shift_reference_point`, or None.
        factor: the shift factor.
        warn: whether to warn about targets left out for lacking a nonzero range.

    Returns:
        The score by design id; +inf for a design missing a scored target value.

    Raises:
        ValueError: if ``method`` is unknown, a target in the reference point has no range, or none
            has a nonzero range.
    """
    if method not in ("asf", "guess", "stom"):
        raise ValueError(f"Unknown method '{method}'.")
    weights = _weights(reference_point, ranges, warn=warn)
    symbols = list(weights)
    q = shift_reference_point({sym: reference_point[sym] for sym in symbols}, targets, ranges, emphasize, factor)

    maximize = {t.symbol: t.maximize for t in targets}
    sign = np.array([-1.0 if maximize[sym] else 1.0 for sym in symbols])
    q_min = sign * np.array([q[sym] for sym in symbols])
    if method == "asf":
        w = np.array([weights[sym] for sym in symbols])
    else:
        ideal = sign * np.array([ranges[sym][0] for sym in symbols])
        nadir = sign * np.array([ranges[sym][1] for sym in symbols])
        if method == "stom":
            q_min = np.maximum(q_min, ideal + delta)

    scores: dict[DesignId, float] = {}
    for design_id, values in target_values.items():
        f = sign * np.array([values.get(sym, np.nan) for sym in symbols], dtype=float)
        if np.isnan(f).any():
            scores[design_id] = math.inf
        elif method == "asf":
            scores[design_id] = float(np.max((f - q_min) / w) + rho * np.sum(f / w))
        elif method == "guess":
            free = np.isclose(q_min, nadir) | (q_min > nadir)
            d = np.maximum(np.where(free, nadir - ideal, nadir - q_min), delta)
            max_term = np.max((f - nadir)[~free] / d[~free]) if not free.all() else 0.0
            scores[design_id] = float(max_term + rho * np.sum(f / d))
        else:
            d = q_min - ideal + delta
            scores[design_id] = float(np.max((f - ideal + delta) / d) + rho * np.sum(f / d))
    return scores


def match_pool(
    target_values: dict[DesignId, dict[str, float]],
    reference_point: dict[str, float],
    ranges: dict[str, tuple[float, float]],
    targets: list[Target],
    *,
    exclude: set | frozenset = frozenset(),
    scorers: list[str] | None = None,
    rho: float = 1e-3,
    factor: float = 3.0,
) -> dict[DesignId, list[str]]:
    """Pick the best design of a pool for each scorer.

    The scorers are ``"asf"``, ``"asf_emphasis_<objective>"`` (the ASF at the reference point shifted
    toward that objective's ideal), ``"guess"`` and ``"stom"``; see `score_designs`.  Each picks the
    design with the lowest finite score that is not in ``exclude``, the first one on ties.

    Args:
        target_values: target values by design id.
        reference_point: aspiration levels by target symbol.
        ranges: ``(ideal, nadir)`` by target symbol.
        targets: the targets.
        exclude: design ids that may not be picked.
        scorers: the scorers to use.  Defaults to ``"asf"``, one emphasis scorer per objective with a
            scored target in the reference point, ``"guess"`` and ``"stom"``.
        rho: the augmentation coefficient.
        factor: the shift factor of the emphasis scorers.

    Returns:
        The names of the scorers that picked each picked design, in scorer order.

    Raises:
        ValueError: if a scorer name is unknown, a target in the reference point has no range, or none
            has a nonzero range.
    """
    weights = _weights(reference_point, ranges)
    objectives = dict.fromkeys(t.objective for t in targets if t.symbol in weights)
    known = ["asf", *(f"asf_emphasis_{obj}" for obj in objectives), "guess", "stom"]
    scorers = known if scorers is None else scorers
    if unknown := [name for name in scorers if name not in known]:
        raise ValueError(f"Unknown scorers {unknown}.")

    picks: dict[DesignId, list[str]] = {}
    for name in scorers:
        emphasize = name.removeprefix("asf_emphasis_") if name.startswith("asf_emphasis_") else None
        method = "asf" if emphasize is not None else name
        scores = score_designs(
            target_values,
            reference_point,
            ranges,
            targets,
            method,
            rho=rho,
            emphasize=emphasize,
            factor=factor,
            warn=False,
        )
        candidates = [(score, i, did) for i, (did, score) in enumerate(scores.items()) if did not in exclude]
        best = min((c for c in candidates if math.isfinite(c[0])), default=None)
        if best is not None:
            picks.setdefault(best[2], []).append(name)
    return picks
