"""Tools for worst-case robust optimization over scenario-based problems."""

from typing import TYPE_CHECKING

from desdeo.problem.schema import (
    Constraint,
    ConstraintTypeEnum,
    ExtraFunction,
    Objective,
    ScalarizationFunction,
    Variable,
    VariableTypeEnum,
)
from desdeo.tools.scenarios import build_combined_scenario_problem

if TYPE_CHECKING:
    from desdeo.problem.scenario import ScenarioModel
    from desdeo.problem.schema import Problem


def add_min_max_robust(
    scenario_model: "ScenarioModel",
    symbols: list[str],
    prefix: str = "robust_",
    combined: "Problem | None" = None,
    symbol_maps: "dict[str, dict[str, dict[str, str]]] | None" = None,
) -> "tuple[Problem, dict[str, str]]":
    """Add min-max robust aggregations for selected symbols to the combined scenario problem.

    Uses the standard epigraph reformulation: introduces an auxiliary variable ``t`` and
    per-leaf upper-bound constraints ``f_s - t <= 0``, then exposes ``t`` as the robust
    element to minimize. This is equivalent to minimizing ``max_s f_s`` but avoids
    non-smooth ``Max`` expressions that most solvers cannot handle.

    For objectives the per-leaf ``_min`` expressions (negated for maximization objectives)
    are used in the constraints. Scalarization functions are always minimization, so their
    per-leaf expressions are inlined directly.

    The new element type matches the original: objectives stay objectives, scalarization
    functions stay scalarization functions, and everything else becomes an extra function.
    The epigraph variable is named ``_t_{prefix}{sym}`` and the returned element is
    ``{prefix}{sym}``.

    Args:
        scenario_model: the ScenarioModel to expand.
        symbols: original symbols whose worst-case values should be added.
        prefix: prefix prepended to each original symbol to form the new symbol.
            Defaults to ``'robust_'``.
        combined: pre-built combined Problem. If provided together with
            ``symbol_maps``, ``build_combined_scenario_problem`` is not called.
            Must match ``scenario_model``.
        symbol_maps: pre-built symbol maps from ``build_combined_scenario_problem``.
            Must be provided together with ``combined``; ignored otherwise.

    Returns:
        A tuple of the combined Problem with robust elements appended, and a dict
        mapping each original symbol to its robust symbol.

    Raises:
        ValueError: if a requested symbol is not found in the combined problem.
    """
    if combined is None or symbol_maps is None:
        combined, symbol_maps = build_combined_scenario_problem(scenario_model)
    weights = scenario_model.leaf_scenarios

    new_variables = list(combined.variables)
    new_objectives = list(combined.objectives or [])
    new_scal_funcs = list(combined.scalarization_funcs or [])
    new_extra_funcs = list(combined.extra_funcs or [])
    new_constraints = list(combined.constraints or [])
    added_symbols: dict[str, str] = {}

    for sym in symbols:
        found_type: str | None = None
        per_leaf: dict[str, str] | None = None
        for elem_type, smap in symbol_maps.items():
            if sym in smap:
                found_type = elem_type
                per_leaf = smap[sym]
                break

        if per_leaf is None:
            raise ValueError(f"Symbol '{sym}' not found in the combined problem.")

        first_leaf_sym = per_leaf[next(iter(weights))]
        elem_lists = {
            "objectives": combined.objectives,
            "scalarization_funcs": combined.scalarization_funcs,
            "extra_funcs": combined.extra_funcs,
            "constraints": combined.constraints,
        }
        ref_elem = next(
            (e for e in (elem_lists.get(found_type) or []) if e.symbol == first_leaf_sym),
            None,
        )
        is_linear = ref_elem.is_linear if ref_elem is not None else False
        is_convex = ref_elem.is_convex if ref_elem is not None else False
        is_twice_diff = ref_elem.is_twice_differentiable if ref_elem is not None else False

        robust_sym = f"{prefix}{sym}"
        t_sym = f"_t_{robust_sym}"
        added_symbols[sym] = robust_sym

        # Epigraph variable t: minimizing t subject to f_s <= t gives min max_s f_s.
        new_variables.append(
            Variable(
                name=f"Min-max robust epigraph variable for {sym}",
                symbol=t_sym,
                variable_type=VariableTypeEnum.real,
                lowerbound=-float("Inf"),
                upperbound=float("Inf"),
                initial_value=0.0,
            )
        )

        # Per-leaf upper-bound constraints: f_s <= t  ->  f_s - t <= 0
        # For objectives, use _min versions (already negated for maximization objectives).
        # For scalarization functions, inline the expression: Pyomo adds constraints before
        # scalarizations, so referencing a scalarization symbol causes an AttributeError.
        for leaf, leaf_sym in per_leaf.items():
            if found_type == "objectives":
                con_func = ["Add", f"{leaf_sym}_min", ["Negate", t_sym]]
            elif found_type == "scalarization_funcs":
                leaf_elem = next(
                    (e for e in (combined.scalarization_funcs or []) if e.symbol == leaf_sym), None
                )
                leaf_func = leaf_elem.func if leaf_elem is not None else leaf_sym
                con_func = ["Add", leaf_func, ["Negate", t_sym]]
            else:
                con_func = ["Add", leaf_sym, ["Negate", t_sym]]

            new_constraints.append(
                Constraint(
                    name=f"Min-max robust upper bound for {sym} in {leaf}",
                    symbol=f"{leaf}_{robust_sym}_con",
                    func=con_func,
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=is_linear,
                    is_convex=is_convex,
                    is_twice_differentiable=is_twice_diff,
                )
            )

        if found_type == "objectives":
            new_objectives.append(
                Objective(
                    name=f"Min-max robust value of {sym}",
                    symbol=robust_sym,
                    func=t_sym,
                    maximize=False,
                    is_linear=True,
                    is_convex=True,
                    is_twice_differentiable=True,
                )
            )
        elif found_type == "scalarization_funcs":
            new_scal_funcs.append(
                ScalarizationFunction(
                    name=f"Min-max robust value of {sym}",
                    symbol=robust_sym,
                    func=t_sym,
                    is_linear=True,
                    is_convex=True,
                    is_twice_differentiable=True,
                )
            )
        else:
            new_extra_funcs.append(
                ExtraFunction(
                    name=f"Min-max robust value of {sym}",
                    symbol=robust_sym,
                    func=t_sym,
                    is_linear=True,
                    is_convex=True,
                    is_twice_differentiable=True,
                )
            )

    return combined.model_copy(
        update={
            "variables": new_variables,
            "objectives": new_objectives or None,
            "scalarization_funcs": new_scal_funcs or None,
            "extra_funcs": new_extra_funcs or None,
            "constraints": new_constraints or None,
        }
    ), added_symbols


def add_weighted_scenarios(
    scenario_model: "ScenarioModel",
    symbols: list[str],
    weights: dict[str, float],
    prefix: str = "weighted_",
    combined: "Problem | None" = None,
    symbol_maps: "dict[str, dict[str, dict[str, str]]] | None" = None,
) -> "tuple[Problem, dict[str, str]]":
    """Add user-weighted aggregations for selected symbols to the combined scenario problem.

    Identical to ``add_expected_value`` in ``desdeo.tools.stochastic``, except that the
    per-leaf weights come from the caller rather than from the scenario probabilities in
    ``scenario_model``.  This lets you express, e.g., pessimistic weightings that put
    more mass on bad scenarios than their true probabilities warrant.

    The new element type matches the original: objectives stay objectives, scalarization
    functions stay scalarization functions, and everything else becomes an extra function.

    Args:
        scenario_model: the ScenarioModel to expand.
        symbols: original symbols whose weighted sums should be added.
        weights: mapping from leaf scenario name to its weight.  Must contain a key
            for every leaf in ``scenario_model.leaf_scenarios``.
        prefix: prefix prepended to each original symbol to form the new symbol.
            Defaults to ``'weighted_'``.
        combined: pre-built combined Problem. If provided together with
            ``symbol_maps``, ``build_combined_scenario_problem`` is not called.
            Must match ``scenario_model``.
        symbol_maps: pre-built symbol maps from ``build_combined_scenario_problem``.
            Must be provided together with ``combined``; ignored otherwise.

    Returns:
        A tuple of the combined Problem with the weighted elements appended, and a dict
        mapping each original symbol to its new weighted symbol.

    Raises:
        ValueError: if a requested symbol is not found in the combined problem.
        ValueError: if ``weights`` is missing a key for any leaf scenario.
    """
    if combined is None or symbol_maps is None:
        combined, symbol_maps = build_combined_scenario_problem(scenario_model)
    leaf_scenarios = scenario_model.leaf_scenarios

    missing = set(leaf_scenarios) - set(weights)
    if missing:
        raise ValueError(f"weights is missing keys for leaf scenarios: {missing}")

    new_objectives = list(combined.objectives or [])
    new_scal_funcs = list(combined.scalarization_funcs or [])
    new_extra_funcs = list(combined.extra_funcs or [])
    added_symbols: dict[str, str] = {}

    for sym in symbols:
        found_type: str | None = None
        per_leaf: dict[str, str] | None = None
        for elem_type, smap in symbol_maps.items():
            if sym in smap:
                found_type = elem_type
                per_leaf = smap[sym]
                break

        if per_leaf is None:
            raise ValueError(f"Symbol '{sym}' not found in the combined problem.")

        terms = [["Multiply", weights[leaf], per_leaf[leaf]] for leaf in leaf_scenarios]
        weighted_expr = terms[0] if len(terms) == 1 else ["Add", *terms]
        weighted_sym = f"{prefix}{sym}"
        added_symbols[sym] = weighted_sym

        first_leaf_sym = per_leaf[next(iter(leaf_scenarios))]
        elem_lists = {
            "objectives": combined.objectives,
            "scalarization_funcs": combined.scalarization_funcs,
            "extra_funcs": combined.extra_funcs,
            "constraints": combined.constraints,
        }
        ref_elem = next(
            (e for e in (elem_lists.get(found_type) or []) if e.symbol == first_leaf_sym),
            None,
        )
        is_linear = ref_elem.is_linear if ref_elem is not None else False
        is_convex = ref_elem.is_convex if ref_elem is not None else False
        is_twice_diff = ref_elem.is_twice_differentiable if ref_elem is not None else False

        if found_type == "objectives":
            new_objectives.append(
                Objective(
                    name=f"Weighted scenario value of {sym}",
                    symbol=weighted_sym,
                    func=weighted_expr,
                    maximize=ref_elem.maximize if ref_elem is not None else False,
                    is_linear=is_linear,
                    is_convex=is_convex,
                    is_twice_differentiable=is_twice_diff,
                )
            )
        elif found_type == "scalarization_funcs":
            new_scal_funcs.append(
                ScalarizationFunction(
                    name=f"Weighted scenario value of {sym}",
                    symbol=weighted_sym,
                    func=weighted_expr,
                    is_linear=is_linear,
                    is_convex=is_convex,
                    is_twice_differentiable=is_twice_diff,
                )
            )
        else:
            new_extra_funcs.append(
                ExtraFunction(
                    name=f"Weighted scenario value of {sym}",
                    symbol=weighted_sym,
                    func=weighted_expr,
                    is_linear=is_linear,
                    is_convex=is_convex,
                    is_twice_differentiable=is_twice_diff,
                )
            )

    return combined.model_copy(
        update={
            "objectives": new_objectives or None,
            "scalarization_funcs": new_scal_funcs or None,
            "extra_funcs": new_extra_funcs or None,
        }
    ), added_symbols
