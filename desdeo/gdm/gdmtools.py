""" This module contains tools for group decision making such as manipulating set of preferences. """

from desdeo.problem import Problem

# Below two are tools for GDM, have needed them in both projects
def dict_of_rps_to_list_of_rps(reference_points: dict[str, dict[str, float]]) -> list[dict[str, float]]:
    """
    Convert dict containing the DM key to an ordered list.
    """
    return list(reference_points.values())

def list_of_rps_to_dict_of_rps(reference_points: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    """
    Convert the ordered list to a dict contain the DM keys. TODO: Later maybe get these keys from somewhere.
    """
    return {f"DM{i+1}": rp for i, rp in enumerate(reference_points)}

# TODO:(@jpajasmaa) document
def agg_aspbounds(po_list: list[dict[str, float]], problem: Problem):
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


# TODO:(@jpajasmaa) comments
def scale_delta(problem: Problem, d: float):
    delta = {}
    ideal = problem.get_ideal_point()
    nadir = problem.get_nadir_point()

    for obj in problem.objectives:
        if obj.maximize:
            delta.update({obj.symbol: d*(ideal[obj.symbol] - nadir[obj.symbol])})
        else:
            delta.update({obj.symbol: d*(nadir[obj.symbol] - ideal[obj.symbol])})
    return delta
