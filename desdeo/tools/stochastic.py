"""Tools for solving scenario-based optimization problems."""

from typing import TYPE_CHECKING

from desdeo.problem.schema import ExtraFunction, Objective, ScalarizationFunction
from desdeo.tools.scalarization import add_asf_diff, add_asf_nondiff
from desdeo.tools.scenarios import build_combined_scenario_problem

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

    modified_model = scenario_model.with_base_problem(problem=scal_problem)
    combined, symbol_maps = build_combined_scenario_problem(modified_model)
    combined, added = add_expected_value(
        modified_model, [scal], combined=combined, symbol_maps=symbol_maps
    )

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

        terms = [["Multiply", weights[leaf], per_leaf[leaf]] for leaf in weights]
        expected_expr = terms[0] if len(terms) == 1 else ["Add", *terms]
        expected_sym = f"{prefix}{sym}"
        added_symbols[sym] = expected_sym

        # Look up a representative per-leaf element to copy differentiability flags.
        # A weighted sum inherits differentiability/linearity/convexity from its terms.
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

        if found_type == "objectives":
            new_objectives.append(
                Objective(
                    name=f"Expected value of {sym}",
                    symbol=expected_sym,
                    func=expected_expr,
                    maximize=ref_elem.maximize if ref_elem is not None else False,
                    is_linear=is_linear,
                    is_convex=is_convex,
                    is_twice_differentiable=is_twice_diff,
                )
            )
        elif found_type == "scalarization_funcs":
            new_scal_funcs.append(
                ScalarizationFunction(
                    name=f"Expected value of {sym}",
                    symbol=expected_sym,
                    func=expected_expr,
                    is_linear=is_linear,
                    is_convex=is_convex,
                    is_twice_differentiable=is_twice_diff,
                )
            )
        else:
            new_extra_funcs.append(
                ExtraFunction(
                    name=f"Expected value of {sym}",
                    symbol=expected_sym,
                    func=expected_expr,
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
