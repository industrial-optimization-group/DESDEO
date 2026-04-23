"""Tools for solving scenario-based optimization problems."""

from typing import TYPE_CHECKING

from desdeo.problem.schema import ScalarizationFunction
from desdeo.tools.scalarization import add_asf_diff, add_asf_nondiff
from desdeo.tools.scenarios import build_combined_scenario_problem

if TYPE_CHECKING:
    from desdeo.problem.scenario import ScenarioModel
    from desdeo.problem.schema import Problem


def expected_asf(
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

    combined = build_combined_scenario_problem(scenario_model.with_base_problem(problem=scal_problem))

    weights = scenario_model.leaf_scenarios

    terms = [["Multiply", weights[leaf], f"{scal}_{leaf}"] for leaf in weights]
    expected_expr = terms[0] if len(terms) == 1 else ["Add", *terms]

    expected_symbol = f"E_{scal}"
    expected_func = ScalarizationFunction(
        name=f"Expected value of {scal}",
        symbol=expected_symbol,
        func=expected_expr,
    )

    existing_scal = list(combined.scalarization_funcs or [])
    existing_scal.append(expected_func)
    combined = combined.model_copy(update={"scalarization_funcs": existing_scal})

    return combined, expected_symbol
