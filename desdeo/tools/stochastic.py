"""Tools for solving scenario-based optimization problems."""

from typing import TYPE_CHECKING

from desdeo.problem.schema import (
    Constraint,
    ConstraintTypeEnum,
    Variable,
    VariableTypeEnum,
)
from desdeo.tools.scalarization import add_asf_diff, add_asf_nondiff
from desdeo.tools.scenarios import append_aggregated_elem, build_combined_scenario_problem, resolve_elem

if TYPE_CHECKING:
    from desdeo.problem.scenario import ScenarioModel
    from desdeo.problem.schema import Problem


def add_expected_asf(
    scenario_model: "ScenarioModel",
    symbol: str,
    reference_point: dict[str, float],
    ideal: dict[str, float] | None = None,
    nadir: dict[str, float] | None = None,
    rho: float = 1e-6,
    delta: float = 1e-6,
) -> "tuple[Problem, str]":
    """Build a combined scenario problem with an expected value of ASF scalarization.

    This is here mostly as a convenience for testing, but it can also be used as a template
    for users who want to build their own scenario problems expected-value scalarizations.

    Args:
        scenario_model: the ScenarioModel to expand and scalarize.
        symbol: symbol for the scalarization function added to the problem.
        reference_point: maps objective symbols to reference point values.
        ideal: maps objective symbols to ideal values. If None, the problem's
            ideal is used.
        nadir: maps objective symbols to nadir values. If None, the problem's
            nadir is used.
        rho: augmentation term weight for the ASF.
        delta: small perturbation for the differentiable ASF variant.

    Returns:
        A tuple of the combined Problem and the scalarization function symbol.
    """
    base_problem = scenario_model.base_problem
    if base_problem.is_twice_differentiable or base_problem.is_linear:
        scal_problem, scal = add_asf_diff(
            problem=base_problem,
            symbol=symbol,
            reference_point=reference_point,
            ideal=ideal,
            nadir=nadir,
            rho=rho,
            delta=delta,
        )
    else:
        scal_problem, scal = add_asf_nondiff(
            problem=base_problem,
            symbol=symbol,
            reference_point=reference_point,
            ideal=ideal,
            nadir=nadir,
            rho=rho,
            delta=delta,
        )

    modified_model = scenario_model.with_base_problem(problem=scal_problem, validate=True)
    combined, symbol_maps = build_combined_scenario_problem(modified_model)
    combined, added = add_expected_value(modified_model, [scal], combined=combined, symbol_maps=symbol_maps)

    return combined, added[scal]


def add_expected_value(
    scenario_model: "ScenarioModel",
    symbols: list[str],
    prefix: str = "E_",
    combined: "Problem | None" = None,
    symbol_maps: "dict[str, dict[str, dict[str, str]]] | None" = None,
) -> "tuple[Problem, dict[str, str]]":
    """Add expected-value aggregations for selected symbols to the combined scenario problem.

    For each symbol the expected value is a probability-weighted sum of the per-leaf
    copies of that symbol in the combined problem.  The new element type matches the
    original: objectives stay objectives, scalarization functions stay scalarization
    functions, and everything else (extra functions, constraints, …) becomes an extra
    function.

    Args:
        scenario_model: the ScenarioModel to expand.
        symbols: original symbols whose expected values should be added.
        prefix: prefix prepended to each original symbol to form the new symbol.
            Defaults to ``'E_'``.
        combined: pre-built combined Problem. If provided together with
            ``symbol_maps``, ``build_combined_scenario_problem`` is not called.
            Must match ``scenario_model``.
        symbol_maps: pre-built symbol maps from ``build_combined_scenario_problem``.
            Must be provided together with ``combined``; ignored otherwise.

    Returns:
        A tuple of the combined Problem with the expected-value elements appended,
        and a dict mapping each original symbol to its new expected-value symbol.

    Raises:
        ValueError: if a requested symbol is not found in the combined problem.
    """
    if combined is None or symbol_maps is None:
        combined, symbol_maps = build_combined_scenario_problem(scenario_model)
    weights = scenario_model.leaf_scenarios

    new_objectives = list(combined.objectives or [])
    new_scal_funcs = list(combined.scalarization_funcs or [])
    new_extra_funcs = list(combined.extra_funcs or [])
    added_symbols: dict[str, str] = {}

    # Variables and constants are direct values; everything else is a computed
    # expression whose func must be inlined rather than referenced by symbol.
    _func_bearing = {"objectives", "extra_funcs", "scalarization_funcs", "constraints"}

    for sym in symbols:
        info = resolve_elem(sym, symbol_maps, combined, scenario_model)
        expected_sym = f"{prefix}{sym}"
        added_symbols[sym] = expected_sym

        if info.found_type in _func_bearing:
            terms = [
                [
                    "Multiply",
                    weights[leaf],
                    next((e.func for e in info.elem_list if e.symbol == info.per_leaf[leaf]), info.per_leaf[leaf]),
                ]
                for leaf in weights
            ]
        else:
            terms = [["Multiply", weights[leaf], info.per_leaf[leaf]] for leaf in weights]
        expected_expr = terms[0] if len(terms) == 1 else ["Add", *terms]

        append_aggregated_elem(
            info.found_type,
            new_objectives,
            new_scal_funcs,
            new_extra_funcs,
            name=f"Expected {info.elem_name}",
            description=f"Expected value of {info.elem_desc}"
            if info.elem_desc
            else f"Expected value of {info.elem_name}",
            symbol=expected_sym,
            func=expected_expr,
            maximize=info.maximize,
            is_linear=info.is_linear,
            is_convex=info.is_convex,
            is_twice_differentiable=info.is_twice_diff,
        )

    return combined.model_copy(
        update={
            "objectives": new_objectives or None,
            "scalarization_funcs": new_scal_funcs or None,
            "extra_funcs": new_extra_funcs or None,
        }
    ), added_symbols


def add_conditional_value_at_risk(
    scenario_model: "ScenarioModel",
    symbols: list[str],
    alpha: float,
    var_prefix: str = "VAR_",
    cvar_prefix: str = "CVAR_",
    combined: "Problem | None" = None,
    symbol_maps: "dict[str, dict[str, dict[str, str]]] | None" = None,
) -> "tuple[Problem, dict[str, str]]":
    """Add CVaR aggregations using the Rockafellar-Uryasev LP formulation.

    For each symbol in ``symbols``, introduces:

    - ``{var_prefix}{sym}``: VaR threshold variable η (shared across scenarios).
    - ``{leaf}_{var_prefix}{sym}``: per-leaf auxiliary z_s ≥ 0 such that
      z_s >= sym_s - eta.
    - ``{leaf}_{var_prefix}{sym}_con``: per-leaf LTE constraint sym_s - eta - z_s <= 0.
    - ``{cvar_prefix}{sym}``: CVaR = eta + 1/(1-alpha) * sum_s p_s * z_s.

    The CVaR element preserves the type of the original element (objective stays
    objective, scalarization function stays scalarization function, anything else
    becomes an extra function).

    Args:
        scenario_model: the ScenarioModel used to build or match ``combined``.
        symbols: original symbols whose CVaR should be added.
        alpha: confidence level, 0 < alpha < 1 (e.g., 0.95 for 95% CVaR).
        var_prefix: prefix for the VaR threshold and auxiliary variables.
            Defaults to ``'VAR_'``.
        cvar_prefix: prefix for the resulting CVaR element. Defaults to ``'CVAR_'``.
        combined: pre-built combined Problem. If provided together with
            ``symbol_maps``, ``build_combined_scenario_problem`` is not called.
        symbol_maps: pre-built symbol maps; required together with ``combined``.

    Returns:
        A tuple of the updated combined Problem and a dict mapping each original
        symbol to its CVaR symbol.

    Raises:
        ValueError: if a requested symbol is not found in the combined problem.
    """
    if combined is None or symbol_maps is None:
        combined, symbol_maps = build_combined_scenario_problem(scenario_model)
    weights = scenario_model.leaf_scenarios
    scale = 1.0 / (1.0 - alpha)

    new_variables = list(combined.variables)
    new_objectives = list(combined.objectives or [])
    new_scal_funcs = list(combined.scalarization_funcs or [])
    new_extra_funcs = list(combined.extra_funcs or [])
    new_constraints = list(combined.constraints or [])
    added_symbols: dict[str, str] = {}

    for sym in symbols:
        info = resolve_elem(sym, symbol_maps, combined, scenario_model)
        var_sym = f"{var_prefix}{sym}"
        cvar_sym = f"{cvar_prefix}{sym}"
        added_symbols[sym] = cvar_sym

        # VaR threshold η — shared across all scenarios.
        new_variables.append(
            Variable(
                name=f"VaR threshold for {info.elem_name}",
                symbol=var_sym,
                variable_type=VariableTypeEnum.real,
                lowerbound=None,
                upperbound=None,
                initial_value=0.0,
            )
        )

        # Per-leaf auxiliary variables z_s and their constraints.
        leaf_z_syms: dict[str, str] = {}
        for leaf, leaf_sym in info.per_leaf.items():
            z_sym = f"{leaf}_{var_sym}"
            leaf_z_syms[leaf] = z_sym

            new_variables.append(
                Variable(
                    name=f"CVaR auxiliary for {info.elem_name} in {leaf}",
                    symbol=z_sym,
                    variable_type=VariableTypeEnum.real,
                    lowerbound=0.0,
                    upperbound=None,
                    initial_value=0.0,
                )
            )

            # z_s >= sym_s - eta  ->  sym_s - eta - z_s <= 0
            # Use the func expression of the per-leaf element rather than its symbol.
            leaf_func = next((e.func for e in info.elem_list if e.symbol == leaf_sym), leaf_sym)
            new_constraints.append(
                Constraint(
                    name=f"CVaR constraint for {info.elem_name} in {leaf}",
                    symbol=f"{z_sym}_con",
                    func=["Add", leaf_func, ["Negate", var_sym], ["Negate", z_sym]],
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=info.is_linear,
                    is_convex=info.is_convex,
                    is_twice_differentiable=info.is_twice_diff,
                )
            )

        # CVaR = η + scale · Σ_s p_s · z_s
        weighted_z = [["Multiply", weights[leaf], leaf_z_syms[leaf]] for leaf in weights]
        sum_z = weighted_z[0] if len(weighted_z) == 1 else ["Add", *weighted_z]

        append_aggregated_elem(
            info.found_type,
            new_objectives,
            new_scal_funcs,
            new_extra_funcs,
            name=f"CVaR of {info.elem_name}",
            description=f"CVaR of {info.elem_desc}" if info.elem_desc else f"CVaR of {info.elem_name}",
            symbol=cvar_sym,
            func=["Add", var_sym, ["Multiply", scale, sum_z]],
            maximize=info.maximize,
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
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
