"""rpm_evolutionary.py

Reference Point Method (RPM) - evolutionary variant.

"""

import numpy as np

from desdeo.problem.schema import Problem
from desdeo.emo.options.algorithms import rvea_options, nsga3_options
from desdeo.emo.options.templates import emo_constructor, ReferencePointOptions

ALGORITHM_OPTION_BUILDERS = {
    "RVEA": rvea_options,
    "NSGA-III": nsga3_options,
}


def _perturb_reference_points(
    problem: Problem, reference_point: dict, scaling_factor: float = 0.1
) -> list[dict]:
    """Generate k+1 perturbed reference points (k = number of objectives).

    This replicates the perturbation scheme used by the classic RPM: one
    sub-problem uses the original, unperturbed reference point; the remaining
    k sub-problems each perturb a single objective's aspiration level to
    encourage a spread of solutions around the reference point.

    Args:
        problem (Problem): The optimization problem, used to read objective
            symbols and the ideal/nadir points needed to scale the
            perturbation.
        reference_point (dict): Mapping objective symbol -> aspiration value.
        scaling_factor (float): Fraction of the ideal-nadir span used to
            perturb each objective. Defaults to 0.1.

    Returns:
        list[dict]: k+1 reference points, the first one being the original
        (unperturbed) reference point.
    """
    symbols = [obj.symbol for obj in problem.objectives]
    ideal = problem.get_ideal_point()
    nadir = problem.get_nadir_point()

    points = [dict(reference_point)]
    for symbol in symbols:
        perturbed = dict(reference_point)
        span = abs(nadir[symbol] - ideal[symbol])
        perturbed[symbol] = reference_point[symbol] + scaling_factor * span
        points.append(perturbed)
    return points


def rpm_solve_solutions_evolutionary(
    problem: Problem,
    reference_point: dict,
    method: str = "RVEA",
    max_generations: int = 200,
    seed: int = 0,
) -> list[dict]:
    """Evolutionary version of rpm_solve_solutions.

    Instead of scalarizing the problem with an achievement scalarizing
    function and solving it with a mathematical-programming solver
    (e.g. PyomoIpoptSolver), each of the k+1 reference-point sub-problems is
    solved using an evolutionary algorithm (RVEA or NSGA-III) guided by the
    reference point as preference information, via emo_constructor.

    Args:
        problem (Problem): The optimization problem to solve.
        reference_point (dict): Mapping objective symbol -> aspiration value.
        method (str): "RVEA" or "NSGA-III". Defaults to "RVEA".
        max_generations (int): Number of generations to run each
            sub-problem for. Defaults to 200.
        seed (int): Random seed, kept fixed across sub-problems for
            reproducibility. Defaults to 0.

    Returns:
        list[dict]: One result dict per sub-problem, each containing the
        perturbed reference point used and the resulting Pareto-optimal
        objective vector(s) found by the evolutionary run.

    Raises:
        ValueError: If `method` is not one of the supported evolutionary
            algorithms.
    """
    if method not in ALGORITHM_OPTION_BUILDERS:
        raise ValueError(
            f"Unsupported evolutionary method: {method}. "
            f"Use one of {list(ALGORITHM_OPTION_BUILDERS)}."
        )

    perturbed_points = _perturb_reference_points(problem, reference_point)
    options_builder = ALGORITHM_OPTION_BUILDERS[method]

    results = []
    for rp in perturbed_points:
        options = options_builder()
        options.template.seed = seed
        options.template.termination.max_generations = max_generations
        options.preference = ReferencePointOptions(preference=rp)

        run_fn, extras = emo_constructor(options, problem)
        result = run_fn()

        results.append({
            "reference_point_used": rp,
            "optimal_outputs": result.optimal_outputs,
        })

    return results