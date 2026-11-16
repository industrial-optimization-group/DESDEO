"""Tools for finding and evaluating designs of scenario-based problems.

A design is a set of values for the first-stage (here-and-now) variables of a
`ScenarioModel`.  A design is evaluated by fixing it and solving, in each leaf
scenario, a recourse problem that minimises a partial achievement scalarizing
function over the objectives present in that leaf.
"""

import warnings
from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from desdeo.problem import Problem, ScalarizationFunction, TensorVariable, Variable, VariableTypeEnum
from desdeo.problem.scenario import ScenarioModel
from desdeo.tools.generics import BaseSolver
from desdeo.tools.partial_scalarization import add_asf_partial_diff
from desdeo.tools.scenarios import _build_parent_map, _path_from_root, _rename_symbols, build_combined_scenario_problem

_BOUND_TOL = 1e-6


class LeafOutcome(BaseModel):
    """Result of evaluating a design in one leaf scenario."""

    status: bool = Field(description="Whether the recourse problem was solved successfully.")
    message: str = Field(description="Solver message.")
    objectives: dict[str, float] = Field(
        default={}, description="Objective values in the leaf, in their original direction."
    )
    variables: dict[str, float | list] = Field(default={}, description="Variable values in the leaf.")


def root_variables(model: ScenarioModel) -> list[str]:
    """Return the variables shared by all scenarios (anticipation_stop["ROOT"]) in base-problem order.

    Args:
        model: the scenario model.

    Returns:
        The root variable symbols.
    """
    root = model.anticipation_stop.get("ROOT", [])
    ordered = [var.symbol for var in model.base_problem.variables if var.symbol in root]
    return ordered + [sym for sym in root if sym not in ordered]


def default_design_variables(model: ScenarioModel) -> list[str]:
    """Return all root variables (anticipation_stop["ROOT"]), in the same order as `root_variables`.

    Args:
        model: the scenario model.

    Returns:
        The default design variable symbols.

    Raises:
        ValueError: if the model has no root variables.
    """
    root = root_variables(model)
    if not root:
        raise ValueError("The scenario model has no variables in anticipation_stop['ROOT'].")
    return root


def _bounds(var: Variable | TensorVariable) -> tuple[np.ndarray, np.ndarray]:
    """Return the lower and upper bounds of a variable as float arrays, with nan for missing bounds."""
    if isinstance(var, TensorVariable):
        return (
            np.array(var.get_lowerbound_values(), dtype=float),
            np.array(var.get_upperbound_values(), dtype=float),
        )
    return (
        np.array(var.lowerbound if var.lowerbound is not None else np.nan, dtype=float),
        np.array(var.upperbound if var.upperbound is not None else np.nan, dtype=float),
    )


def _fixed_variable(var: Variable | TensorVariable, value: float | list) -> Variable | TensorVariable:
    """Return a copy of a variable with both bounds and the initial value set to ``value``."""
    integral = var.variable_type in (VariableTypeEnum.integer, VariableTypeEnum.binary)
    lower, upper = _bounds(var)

    array = np.array(value, dtype=float)
    if array.shape != lower.shape:
        raise ValueError(f"Value for '{var.symbol}' has shape {array.shape}, expected {lower.shape}.")
    if integral:
        array = np.rint(array)
    # nan bounds compare False, so missing bounds never trigger.
    if np.any(array < lower - _BOUND_TOL * np.maximum(1, np.abs(lower))) or np.any(
        array > upper + _BOUND_TOL * np.maximum(1, np.abs(upper))
    ):
        raise ValueError(f"Value for '{var.symbol}' is outside its bounds.")

    fixed = (array.astype(int) if integral else array).tolist()
    if isinstance(var, TensorVariable):
        update = {"lowerbounds": fixed, "upperbounds": fixed, "initial_values": fixed}
    else:
        update = {"lowerbound": fixed, "upperbound": fixed, "initial_value": fixed}
    return type(var).model_validate(var.model_dump() | update)


def fix_variables(problem: Problem, values: dict[str, float | list]) -> Problem:
    """Return a copy of the problem with the given variables fixed to the given values.

    Args:
        problem: the problem whose variables are fixed.
        values: maps variable symbols to values; nested lists for tensor variables.

    Returns:
        A copy of the problem where each named variable has equal lower and upper bounds.

    Raises:
        KeyError: if a symbol is not a variable of the problem.
        ValueError: if a value is outside the variable's bounds or has the wrong shape.
    """
    unknown = set(values) - {var.symbol for var in problem.variables}
    if unknown:
        raise KeyError(f"Not variables of the problem: {sorted(unknown)}.")
    variables = [_fixed_variable(var, values[var.symbol]) if var.symbol in values else var for var in problem.variables]
    return problem.model_copy(update={"variables": variables})


def same_design(
    a: dict[str, float | list],
    b: dict[str, float | list],
    variables: dict[str, Variable | TensorVariable],
    rtol: float = 1e-4,
    atol: float = 1e-6,
) -> bool:
    """Check whether two designs are equal within tolerance.

    Integer and binary values must match exactly after rounding.  Real values match when
    ``|a - b| <= max(rtol * (ub - lb), atol)``; when a bound is missing, the tolerance is ``atol``.

    Args:
        a: the first design.
        b: the second design.
        variables: the design variables by symbol.
        rtol: tolerance relative to the variable's range.
        atol: absolute tolerance.

    Returns:
        True if the designs match.
    """
    if set(a) != set(b):
        return False
    for sym, value in a.items():
        var = variables[sym]
        x = np.array(value, dtype=float)
        y = np.array(b[sym], dtype=float)
        if x.shape != y.shape:
            return False
        if var.variable_type in (VariableTypeEnum.integer, VariableTypeEnum.binary):
            if not np.array_equal(np.rint(x), np.rint(y)):
                return False
            continue
        lower, upper = _bounds(var)
        tol = np.where(np.isnan(upper - lower), atol, np.maximum(rtol * (upper - lower), atol))
        if np.any(np.abs(x - y) > tol):
            return False
    return True


def find_design(
    registry: Sequence[dict[str, float | list]],
    design: dict[str, float | list],
    variables: dict[str, Variable | TensorVariable],
    rtol: float = 1e-4,
    atol: float = 1e-6,
) -> int | None:
    """Return the index of the first design in ``registry`` matching ``design``, or None.

    Args:
        registry: the known designs.
        design: the design to look for.
        variables: the design variables by symbol.
        rtol: tolerance relative to the variable's range, see `same_design`.
        atol: absolute tolerance, see `same_design`.

    Returns:
        The index of the matching design, or None if no design matches.
    """
    return next(
        (i for i, known in enumerate(registry) if same_design(known, design, variables, rtol=rtol, atol=atol)),
        None,
    )


def design_from_values(variable_values: dict[str, float | list], design_variables: list[str]) -> dict:
    """Pick the design variable values from a solution.

    Works with the optimal variables of a leaf problem and of a combined scenario problem,
    where root variables keep their original symbols.

    Args:
        variable_values: variable values by symbol, e.g., `SolverResults.optimal_variables`.
        design_variables: the design variable symbols.

    Returns:
        The design.
    """
    return {sym: variable_values[sym] for sym in design_variables}


def outcomes_from_combined(
    objective_values: dict[str, float], symbol_maps: dict[str, dict[str, dict[str, str]]]
) -> dict[str, dict[str, float]]:
    """Split the objective values of a combined scenario problem per leaf.

    Args:
        objective_values: objective values of the combined problem by combined symbol.
        symbol_maps: the symbol maps returned by `build_combined_scenario_problem`.

    Returns:
        A dict ``{leaf: {objective: value}}`` with the original objective symbols.
    """
    outcomes: dict[str, dict[str, float]] = {}
    for sym, per_leaf in symbol_maps["objectives"].items():
        for leaf, new_sym in per_leaf.items():
            outcomes.setdefault(leaf, {})[sym] = float(objective_values[new_sym])
    return outcomes


def independent_leaf_groups(model: ScenarioModel, fixed: Iterable[str]) -> list[list[str]]:
    """Group the leaf scenarios that must be solved together once ``fixed`` variables are fixed.

    All leaves under a node share the variables in that node's anticipation_stop.  Leaves
    are coupled when they share a variable that is not fixed.

    Args:
        model: the scenario model.
        fixed: the symbols of the fixed variables.

    Returns:
        The groups of coupled leaves, ordered as in `ScenarioModel.leaf_scenarios`.
    """
    fixed = set(fixed)
    leaves = list(model.leaf_scenarios)
    parent_map = _build_parent_map(model.scenario_tree)
    root_of = {leaf: leaf for leaf in leaves}

    def find(leaf: str) -> str:
        while root_of[leaf] != leaf:
            root_of[leaf] = root_of[root_of[leaf]]
            leaf = root_of[leaf]
        return leaf

    for node, symbols in model.anticipation_stop.items():
        if set(symbols) <= fixed:
            continue
        under = [leaf for leaf in leaves if node in _path_from_root(leaf, parent_map)]
        for leaf in under[1:]:
            root_of[find(leaf)] = find(under[0])

    groups: dict[str, list[str]] = {}
    for leaf in leaves:
        groups.setdefault(find(leaf), []).append(leaf)
    return list(groups.values())


def to_min_space(values: dict[str, float], maximize: dict[str, bool]) -> dict[str, float]:
    """Negate the values of maximised objectives.

    Args:
        values: objective values by symbol.
        maximize: maps objective symbols to whether they are maximised.

    Returns:
        The values in the minimisation space.
    """
    return {sym: -value if maximize.get(sym, False) else value for sym, value in values.items()}


def from_min_space(values: dict[str, float], maximize: dict[str, bool]) -> dict[str, float]:
    """Return values in the minimisation space to the original direction of the objectives.

    Args:
        values: objective values by symbol, in the minimisation space.
        maximize: maps objective symbols to whether they are maximised.

    Returns:
        The values in the original direction.
    """
    return to_min_space(values, maximize)


def _asf_terms(
    leaf_problem: Problem,
    reference_point: dict[str, float],
    ranges: dict[str, tuple[float, float]] | None,
) -> tuple[dict[str, float], dict[str, float]]:
    """Return the reference point and weights of a leaf's partial ASF, keyed by original symbol.

    The weights are the ranges ``|nadir - ideal|``.  If any objective in the reference point lacks a
    nonzero range, all weights are 1 and a warning is emitted.
    """
    ranges = ranges or {}
    rp: dict[str, float] = {}
    spans: dict[str, float] = {}
    for obj in leaf_problem.objectives:
        if obj.symbol not in reference_point:
            continue
        rp[obj.symbol] = reference_point[obj.symbol]
        ideal, nadir = ranges.get(obj.symbol, (obj.ideal, obj.nadir))
        spans[obj.symbol] = abs(nadir - ideal) if ideal is not None and nadir is not None else 0.0
    if all(spans.values()):
        return rp, spans
    missing = sorted(sym for sym, span in spans.items() if not span)
    warnings.warn(f"No usable range for objectives {missing}; using unit ASF weights for all objectives.", stacklevel=3)
    return rp, dict.fromkeys(rp, 1.0)


def _add_summed_asf(
    problem: Problem, terms: dict[str, tuple[dict[str, float], dict[str, float]]], symbol: str
) -> Problem:
    """Add the variables and constraints of one partial ASF per term and a scalarization minimising their sum.

    Each term ``key: (reference_point, weights)`` gets its own alpha variable ``_alpha_{key}``
    and constraints prefixed with ``_asf_{key}_``.
    """
    funcs = []
    for key, (rp, weights) in terms.items():
        with_asf, asf_symbol = add_asf_partial_diff(problem, f"_asf_{key}", rp, weights)
        renames = {"_alpha": f"_alpha_{key}"}
        alpha = next(var for var in with_asf.variables if var.symbol == "_alpha")
        alpha = alpha.model_copy(update={"symbol": f"_alpha_{key}", "name": f"alpha ({key})"})
        old_constraints = {con.symbol for con in problem.constraints or []}
        constraints = [
            con.model_copy(update={"symbol": f"_asf_{key}_{con.symbol}", "func": _rename_symbols(con.func, renames)})
            for con in with_asf.constraints
            if con.symbol not in old_constraints
        ]
        asf = next(scal for scal in with_asf.scalarization_funcs if scal.symbol == asf_symbol)
        funcs.append(_rename_symbols(asf.func, renames))
        problem = problem.add_variables([alpha]).add_constraints(constraints)

    return problem.add_scalarization(
        ScalarizationFunction(
            name="Sum of partial ASFs",
            symbol=symbol,
            func=funcs[0] if len(funcs) == 1 else ["Add", *funcs],
            is_linear=problem.is_linear,
            is_convex=problem.is_convex,
            is_twice_differentiable=problem.is_twice_differentiable,
        )
    )


def _group_model(model: ScenarioModel, group: list[str]) -> ScenarioModel:
    """Return the model restricted to the subtree spanning the leaves in ``group``."""
    parent_map = _build_parent_map(model.scenario_tree)
    keep = {node for leaf in group for node in _path_from_root(leaf, parent_map)}
    tree = {node: [c for c in children if c in keep] for node, children in model.scenario_tree.items() if node in keep}
    # Only declared fields are copied, so cached properties such as leaf_scenarios are recomputed.
    fields = {name: getattr(model, name) for name in type(model).model_fields}
    return ScenarioModel.model_construct(
        **fields
        | {
            "scenario_tree": tree,
            "scenario_probabilities": {node: p for node, p in model.scenario_probabilities.items() if node in keep},
            "anticipation_stop": {node: syms for node, syms in model.anticipation_stop.items() if node in keep},
        }
    )


def _solve(problem: Problem, target: str, solver: type[BaseSolver], solver_options: Any):
    """Solve the problem; return the results, or None and a message if solving raised.

    Errors raised while constructing the solver propagate.
    """
    instance = solver(problem, solver_options)
    try:
        return instance.solve(target), ""
    except Exception as e:
        return None, f"Solver raised {type(e).__name__}: {e}"


def evaluate_design(
    model: ScenarioModel,
    design: dict[str, float | list],
    solver: type[BaseSolver],
    reference_point: dict[str, float],
    *,
    ranges: dict[str, tuple[float, float]] | None = None,
    leaves: list[str] | None = None,
    solver_options: Any = None,
    leaf_reference_points: dict[str, dict[str, float]] | None = None,
    leaf_ranges: dict[str, dict[str, tuple[float, float]]] | None = None,
) -> dict[str, LeafOutcome]:
    """Evaluate a design in the leaf scenarios of a scenario model.

    The design variables are fixed, and the remaining (recourse) variables of each leaf are
    chosen by minimising a partial ASF over the objectives of that leaf found in
    ``reference_point``.  Leaves coupled through unfixed shared variables (see
    `independent_leaf_groups`) are solved together in one combined problem whose target
    is the sum of their partial ASFs.

    Args:
        model: the scenario model.
        design: maps design variable symbols to values.
        solver: the solver class used for the recourse problems.
        reference_point: aspiration levels by original objective symbol, in the
            objectives' original direction. Objectives missing from it are not scalarized.
        ranges: optional ``(ideal, nadir)`` per objective used for the ASF weights.  Defaults
            to the objective's ideal and nadir in the leaf.  If any objective of a leaf in the
            reference point has no nonzero range, that leaf uses unit weights for all objectives
            and a warning is emitted.
        leaves: the leaves to evaluate. Defaults to all leaves.  Leaves coupled with these
            are solved together with them but not returned.
        solver_options: options passed to the solver.
        leaf_reference_points: optional reference points by leaf; a leaf found here uses its own
            reference point instead of ``reference_point``, other leaves use ``reference_point``.
        leaf_ranges: optional ranges by leaf and original objective symbol; they override ``ranges``
            for the objectives they cover in that leaf.

    Returns:
        The outcome of each evaluated leaf.

    Raises:
        ValueError: if ``leaves`` has names that are not leaves of the model, a design variable is
            not a variable of an evaluated leaf, or an evaluated leaf has no objective in
            ``reference_point``.
    """
    leaves = list(model.leaf_scenarios) if leaves is None else leaves
    unknown = sorted(set(leaves) - set(model.leaf_scenarios))
    if unknown:
        raise ValueError(f"Not leaves of the model: {unknown}.")
    leaf_reference_points = leaf_reference_points or {}
    leaf_ranges = leaf_ranges or {}
    target = "_design_asf"
    outcomes: dict[str, LeafOutcome] = {}

    groups = [group for group in independent_leaf_groups(model, design.keys()) if set(group) & set(leaves)]
    leaf_problems = {leaf: model.get_scenario_problem(leaf) for group in groups for leaf in group}
    for leaf, leaf_problem in leaf_problems.items():
        absent = sorted(set(design) - {var.symbol for var in leaf_problem.variables})
        if absent:
            raise ValueError(f"Design variables {absent} are not variables of leaf '{leaf}'.")
    leaf_terms = {
        leaf: _asf_terms(
            leaf_problem,
            leaf_reference_points.get(leaf, reference_point),
            {**(ranges or {}), **leaf_ranges.get(leaf, {})},
        )
        for leaf, leaf_problem in leaf_problems.items()
    }
    empty = [leaf for leaf, (rp, _) in leaf_terms.items() if not rp]
    if empty:
        raise ValueError(f"The reference point has no objectives of leaves {empty}.")

    for group in groups:
        if len(group) == 1:
            problem = leaf_problems[group[0]]
            symbol_maps = {
                "variables": {var.symbol: {group[0]: var.symbol} for var in problem.variables},
                "objectives": {obj.symbol: {group[0]: obj.symbol} for obj in problem.objectives},
            }
        else:
            problem, symbol_maps = build_combined_scenario_problem(_group_model(model, group))
        var_maps, obj_maps = symbol_maps["variables"], symbol_maps["objectives"]
        fixed = {var_maps[sym][leaf]: value for sym, value in design.items() for leaf in group}
        terms = {
            leaf: (
                {obj_maps[sym][leaf]: value for sym, value in rp.items()},
                {obj_maps[sym][leaf]: weight for sym, weight in weights.items()},
            )
            for leaf, (rp, weights) in leaf_terms.items()
            if leaf in group
        }
        problem = _add_summed_asf(fix_variables(problem, fixed), terms, target)

        results, error = _solve(problem, target, solver, solver_options)
        evaluated = [leaf for leaf in group if leaf in leaves]
        if results is None or not results.success:
            message = error if results is None else results.message
            outcomes |= {leaf: LeafOutcome(status=False, message=message) for leaf in evaluated}
            continue
        objectives = outcomes_from_combined(results.optimal_objectives, symbol_maps)
        for leaf in evaluated:
            outcomes[leaf] = LeafOutcome(
                status=True,
                message=results.message,
                objectives=objectives[leaf],
                variables={
                    sym: results.optimal_variables[per_leaf[leaf]]
                    for sym, per_leaf in var_maps.items()
                    if leaf in per_leaf
                },
            )

    return outcomes
