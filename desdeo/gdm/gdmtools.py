"""This module contains tools for group decision making such as manipulating set of preferences."""

from desdeo.problem import Problem


# Below two are tools for GDM, have needed them in both projects
def dict_of_rps_to_list_of_rps(reference_points: dict[str, dict[str, float]]) -> list[dict[str, float]]:
    """Convert a dict of preferences keyed by decision maker into an ordered list of preferences."""
    return list(reference_points.values())


def list_of_rps_to_dict_of_rps(reference_points: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    """Convert an ordered list of preferences into a dict keyed by decision maker (``DM1``, ``DM2``, ...)."""
    return {f"DM{i + 1}": rp for i, rp in enumerate(reference_points)}


def agg_aspbounds(po_list: list[dict[str, float]], problem: Problem) -> tuple[dict[str, float], dict[str, float]]:
    """Aggregate a set of preferences into shared aspiration levels and bounds.

    For each objective, the aggregated aspiration level is the most optimistic
    value across the given preferences (the maximum for objectives to be
    maximized, the minimum for objectives to be minimized), while the aggregated
    bound is the least optimistic value.

    Args:
        po_list (list[dict[str, float]]): a list of preferences, where each
            preference maps objective symbols to values.
        problem (Problem): the problem the preferences relate to. Used to
            determine the objective symbols and whether each is maximized.

    Returns:
        tuple[dict[str, float], dict[str, float]]: the aggregated aspiration
            levels and the aggregated bounds, each mapping objective symbols to
            values.
    """
    agg_aspirations = {}
    agg_bounds = {}

    for obj in problem.objectives:
        if obj.maximize:
            agg_aspirations.update({obj.symbol: max(s[obj.symbol] for s in po_list)})
            agg_bounds.update({obj.symbol: min(s[obj.symbol] for s in po_list)})
        else:
            agg_aspirations.update({obj.symbol: min(s[obj.symbol] for s in po_list)})
            agg_bounds.update({obj.symbol: max(s[obj.symbol] for s in po_list)})

    return agg_aspirations, agg_bounds


def scale_delta(problem: Problem, d: float) -> dict[str, float]:
    """Scale a step size into a per-objective delta based on the objective ranges.

    For each objective, the delta has magnitude equal to the fraction `d` of the
    objective's range, i.e. the distance between the ideal and nadir points.

    Args:
        problem (Problem): the problem whose ideal and nadir points define the
            objective ranges.
        d (float): the fraction of each objective's range to use as the delta.

    Returns:
        dict[str, float]: a mapping from objective symbols to the scaled delta.
    """
    delta = {}
    ideal = problem.get_ideal_point()
    nadir = problem.get_nadir_point()

    for obj in problem.objectives:
        if obj.maximize:
            delta.update({obj.symbol: d * (ideal[obj.symbol] - nadir[obj.symbol])})
        else:
            delta.update({obj.symbol: d * (nadir[obj.symbol] - ideal[obj.symbol])})
    return delta
