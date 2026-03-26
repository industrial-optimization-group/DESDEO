"""Utilities for working with Lagrange multipliers in explainable multiobjective optimization."""

import re
from collections import defaultdict


def filter_lagrange_multipliers(  # noqa: C901
    lagrange_multipliers: dict[str, float],
    objective_symbols: list[str] | None = None,
) -> dict[str, float]:
    """Filter raw Lagrange multipliers to keep one representative per objective.

    Solver results may contain multiple multiplier entries per objective
    (e.g., from equality and inequality constraints). This function groups
    them and selects a preferred one (non-equality constraint preferred).

    Args:
        lagrange_multipliers: Raw multiplier dict from SolverResults.
        objective_symbols: If provided, use these to group multipliers by
            objective symbol. Otherwise, group by ``f_{index}`` pattern.

    Returns:
        A dict mapping each objective key to its filtered multiplier value.
        Missing objectives are assigned 0.0.
    """
    grouped: dict[str, list[tuple[str, float]]] = defaultdict(list)

    for key, value in lagrange_multipliers.items():
        if objective_symbols is None:
            match = re.search(r"f_(\d+)", key)
            if match:
                f_i = match.group(1)
                grouped[f_i].append((key, value))
        else:
            for symbol in objective_symbols:
                if symbol in key:
                    grouped[symbol].append((key, value))
                    break

    filtered: dict[str, float] = {}
    for obj_key, entries in grouped.items():
        # Prefer non-"eq" constraints
        preferred = next((entry for entry in entries if not entry[0].endswith("eq")), None)
        if preferred is None and entries:
            preferred = entries[0]

        if preferred:
            # Use the symbol as key if available
            key = obj_key if (objective_symbols is not None and obj_key in objective_symbols) else preferred[0]
            filtered[key] = preferred[1]

    # Ensure every objective has an entry (default 0.0)
    if objective_symbols is not None:
        for symbol in objective_symbols:
            if symbol not in filtered:
                filtered[symbol] = 0.0
    else:
        max_index = -1
        for key in filtered:
            match = re.search(r"f_(\d+)", key)
            if match:
                max_index = max(max_index, int(match.group(1)))
        for i in range(max_index + 1):
            key = f"f_{i}"
            if key not in filtered:
                filtered[key] = 0.0

    return filtered


def filter_constraint_values(
    constraint_values: dict[str, float],
    objective_symbols: list[str] | None = None,
) -> dict[str, float]:
    """Filter constraint values to keep one representative per objective.

    Same grouping logic as :func:`filter_lagrange_multipliers` but applied
    to constraint values. Used to determine which constraints are active.

    Args:
        constraint_values: Raw constraint value dict from SolverResults.
        objective_symbols: Optional list of objective symbols for grouping.

    Returns:
        A dict mapping each objective key to its filtered constraint value.
    """
    grouped: dict[str, list[tuple[str, float]]] = defaultdict(list)

    for key, value in constraint_values.items():
        if objective_symbols is None:
            match = re.search(r"f_(\d+)", key)
            if match:
                f_i = match.group(1)
                grouped[f_i].append((key, value))
        else:
            for symbol in objective_symbols:
                if symbol in key:
                    grouped[symbol].append((key, value))
                    break

    filtered: dict[str, float] = {}
    for obj_key, entries in grouped.items():
        preferred = next((entry for entry in entries if not entry[0].endswith("eq")), None)
        if preferred is None and entries:
            preferred = entries[0]

        if preferred:
            key = obj_key if (objective_symbols is not None and obj_key in objective_symbols) else preferred[0]
            filtered[key] = preferred[1]

    return filtered


def compute_tradeoffs(
    filtered_multipliers: dict[str, float] | None,
) -> dict[str, dict[str, float]] | None:
    """Compute a tradeoff matrix from filtered Lagrange multipliers.

    Tradeoffs represent marginal rates of substitution between objectives.
    For objectives *i* and *j*: ``tradeoff[i][j] = -lambda_j / lambda_i``.

    Args:
        filtered_multipliers: Dict mapping objective keys to their multiplier
            values. Typically the output of :func:`filter_lagrange_multipliers`.

    Returns:
        A nested dict where ``result[i][j]`` is the tradeoff of improving
        objective *i* on objective *j*. Diagonal entries are 1.0.
        Returns ``None`` if input is ``None`` or empty.
    """
    if not filtered_multipliers:
        return None

    objectives = list(filtered_multipliers.keys())
    tradeoffs: dict[str, dict[str, float]] = {}

    for obj_i in objectives:
        tradeoffs[obj_i] = {}
        lambda_i = filtered_multipliers[obj_i]

        if lambda_i == 0:
            for obj_j in objectives:
                tradeoffs[obj_i][obj_j] = 0.0 if obj_i != obj_j else 1.0
            continue

        for obj_j in objectives:
            if obj_i == obj_j:
                tradeoffs[obj_i][obj_j] = 1.0
            else:
                lambda_j = filtered_multipliers[obj_j]
                tradeoffs[obj_i][obj_j] = -lambda_j / lambda_i

    return tradeoffs


def determine_active_objectives(
    lagrange_multipliers: list[dict[str, float] | None],
    constraint_values: list[dict[str, float] | None] | None = None,
    objective_symbols: list[str] | None = None,
    threshold: float = 1e-5,
) -> list[list[str]]:
    """Determine which objectives are active (binding) for each solution.

    An objective is considered active if its corresponding constraint is
    binding (constraint value >= 0) or, when constraint values are not
    available, if its multiplier magnitude exceeds a threshold.

    Args:
        lagrange_multipliers: List of filtered multiplier dicts, one per solution.
        constraint_values: Optional list of filtered constraint value dicts.
        objective_symbols: Optional list of known objective symbols.
        threshold: Multiplier magnitude threshold for the fallback heuristic.

    Returns:
        A list of lists, where each inner list contains the symbols of the
        active objectives for the corresponding solution.
    """
    active_objectives: list[list[str]] = []

    if constraint_values and objective_symbols:
        for constraint_dict in constraint_values:
            if constraint_dict is None:
                active_objectives.append([])
                continue
            active = [obj for obj, value in constraint_dict.items() if obj in objective_symbols and value >= 0]
            active_objectives.append(active)
    elif objective_symbols:
        for multiplier_dict in lagrange_multipliers:
            if multiplier_dict is None:
                active_objectives.append([])
                continue
            active = [obj for obj in objective_symbols if abs(multiplier_dict.get(obj, 0.0)) > threshold]
            active_objectives.append(active)
    else:
        for multiplier_dict in lagrange_multipliers:
            if multiplier_dict is None:
                active_objectives.append([])
                continue
            active = [obj for obj, value in multiplier_dict.items() if abs(value) > threshold]
            active_objectives.append(active)

    return active_objectives
