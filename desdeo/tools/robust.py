"""Tools for worst-case robust optimization over scenario-based problems."""

from typing import TYPE_CHECKING

from desdeo.problem.schema import Constraint, ConstraintTypeEnum, Variable, VariableTypeEnum
from desdeo.tools.scenarios import append_aggregated_elem, build_combined_scenario_problem, resolve_elem

if TYPE_CHECKING:
    from desdeo.problem.scenario import ScenarioModel
    from desdeo.problem.schema import Problem


def add_worst_case_robust(
    scenario_model: "ScenarioModel",
    symbols: list[str],
    prefix: str = "robust_",
    combined: "Problem | None" = None,
    symbol_maps: "dict[str, dict[str, dict[str, str]]] | None" = None,
) -> "tuple[Problem, dict[str, str]]":
    """Add worst-case robust aggregations for selected symbols to the combined scenario problem.

    Uses the standard epigraph reformulation with an auxiliary variable ``t`` and
    per-leaf bound constraints, avoiding non-smooth ``Max``/``Min`` expressions that
    most solvers cannot handle.

    The worst-case direction matches the original optimisation direction:

    * **Minimise** objectives / scalarization functions / extra functions — worst case
      is the largest value across scenarios.  Adds constraints ``f_s - t <= 0`` and
      exposes ``t`` as a new **minimise** element (equivalent to ``min max_s f_s``).
    * **Maximise** objectives — worst case is the smallest value across scenarios.
      Adds constraints ``t - f_s <= 0`` and exposes ``t`` as a new **maximise** element
      (equivalent to ``max min_s f_s``).

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

    new_variables = list(combined.variables)
    new_objectives = list(combined.objectives or [])
    new_scal_funcs = list(combined.scalarization_funcs or [])
    new_extra_funcs = list(combined.extra_funcs or [])
    new_constraints = list(combined.constraints or [])
    added_symbols: dict[str, str] = {}

    for sym in symbols:
        info = resolve_elem(sym, symbol_maps, combined, scenario_model)
        robust_sym = f"{prefix}{sym}"
        t_sym = f"_t_{robust_sym}"
        added_symbols[sym] = robust_sym

        is_maximize = info.found_type == "objectives" and info.maximize

        # Epigraph variable t.
        # Minimise objective: t >= f_s for all s  ->  t = max_s f_s  ->  minimise t.
        # Maximise objective: t <= f_s for all s  ->  t = min_s f_s  ->  maximise t.
        new_variables.append(
            Variable(
                name=f"Worst-case robust epigraph variable for {info.elem_name}",
                symbol=t_sym,
                variable_type=VariableTypeEnum.real,
                lowerbound=None,
                upperbound=None,
                initial_value=0.0,
            )
        )

        for leaf, leaf_sym in info.per_leaf.items():
            # Maximise: t - f_s <= 0  ->  t <= f_s.  Minimise: f_s - t <= 0  ->  f_s <= t.
            con_func = ["Add", t_sym, ["Negate", leaf_sym]] if is_maximize else ["Add", leaf_sym, ["Negate", t_sym]]
            new_constraints.append(
                Constraint(
                    name=f"Worst-case robust bound for {info.elem_name} in {leaf}",
                    symbol=f"{leaf}_{robust_sym}_con",
                    func=con_func,
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=info.is_linear,
                    is_convex=info.is_convex,
                    is_twice_differentiable=info.is_twice_diff,
                )
            )

        append_aggregated_elem(
            info.found_type,
            new_objectives,
            new_scal_funcs,
            new_extra_funcs,
            name=f"Worst-case {info.elem_name}",
            description=f"Worst-case robust value of {info.elem_desc}"
            if info.elem_desc
            else f"Worst-case robust value of {info.elem_name}",
            symbol=robust_sym,
            func=t_sym,
            maximize=is_maximize,
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


def add_single_objective_worst_case_regret(
    scenario_model: "ScenarioModel",
    symbols: list[str],
    ideals: "dict[str, dict[str, float]]",
    prefix: str = "regret_wc_",
    combined: "Problem | None" = None,
    symbol_maps: "dict[str, dict[str, dict[str, str]]] | None" = None,
) -> "tuple[Problem, dict[str, str]]":
    """Add worst-case regret aggregations for selected symbols to the combined scenario problem.

    For each symbol, the per-scenario regret is the difference between the objective
    value in that scenario and its ideal (best achievable) value in that scenario:

    * **Minimise** objectives: ``regret_s = f_s - ideal_s``  (ideal is the minimum).
    * **Maximise** objectives: ``regret_s = ideal_s - f_s``  (ideal is the maximum).

    The worst-case regret across all scenarios is then expressed via the standard
    epigraph reformulation: minimise ``t`` subject to ``regret_s - t <= 0`` for
    every leaf scenario ``s``.  The resulting element is always a **minimise**
    objective (or extra function / scalarization function matching the original type)
    regardless of the original optimisation direction.

    Args:
        scenario_model: the ScenarioModel to expand.
        symbols: original symbols whose worst-case regret should be added.
        ideals: mapping ``{symbol -> {leaf -> ideal_value}}`` giving the ideal
            (best achievable) value of each symbol in each leaf scenario.  Every
            leaf returned by ``scenario_model.leaf_scenarios`` must have an entry
            for each symbol.
        prefix: prefix prepended to each original symbol to form the new symbol.
            Defaults to ``'regret_wc_'``.
        combined: pre-built combined Problem.  If provided together with
            ``symbol_maps``, ``build_combined_scenario_problem`` is not called.
            Must match ``scenario_model``.
        symbol_maps: pre-built symbol maps from ``build_combined_scenario_problem``.
            Must be provided together with ``combined``; ignored otherwise.

    Returns:
        A tuple of the combined Problem with worst-case regret elements appended,
        and a dict mapping each original symbol to its regret symbol.

    Raises:
        ValueError: if a requested symbol is not found in the combined problem.
        ValueError: if ``ideals`` is missing a leaf entry for any requested symbol.
    """
    if combined is None or symbol_maps is None:
        combined, symbol_maps = build_combined_scenario_problem(scenario_model)

    new_variables = list(combined.variables)
    new_objectives = list(combined.objectives or [])
    new_scal_funcs = list(combined.scalarization_funcs or [])
    new_extra_funcs = list(combined.extra_funcs or [])
    new_constraints = list(combined.constraints or [])
    added_symbols: dict[str, str] = {}

    for sym in symbols:
        info = resolve_elem(sym, symbol_maps, combined, scenario_model)
        regret_sym = f"{prefix}{sym}"
        t_sym = f"_t_{regret_sym}"
        added_symbols[sym] = regret_sym

        sym_ideals = ideals.get(sym, {})
        missing_leaves = set(info.per_leaf) - set(sym_ideals)
        if missing_leaves:
            raise ValueError(f"ideals is missing entries for symbol '{sym}' in leaves: {missing_leaves}")

        new_variables.append(
            Variable(
                name=f"Worst-case regret epigraph variable for {info.elem_name}",
                symbol=t_sym,
                variable_type=VariableTypeEnum.real,
                lowerbound=None,
                upperbound=None,
                initial_value=0.0,
            )
        )

        for leaf, leaf_sym in info.per_leaf.items():
            ideal_val = sym_ideals[leaf]
            # Minimise: regret_s = f_s - ideal_s  ->  f_s - ideal_s - t <= 0
            # Maximise: regret_s = ideal_s - f_s  ->  ideal_s - f_s - t <= 0
            if info.maximize:
                con_func = ["Add", ideal_val, ["Negate", leaf_sym], ["Negate", t_sym]]
            else:
                con_func = ["Add", leaf_sym, -ideal_val, ["Negate", t_sym]]
            new_constraints.append(
                Constraint(
                    name=f"Worst-case regret bound for {info.elem_name} in {leaf}",
                    symbol=f"{leaf}_{regret_sym}_con",
                    func=con_func,
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=info.is_linear,
                    is_convex=info.is_convex,
                    is_twice_differentiable=info.is_twice_diff,
                )
            )

        append_aggregated_elem(
            info.found_type,
            new_objectives,
            new_scal_funcs,
            new_extra_funcs,
            name=f"Worst-case regret {info.elem_name}",
            description=f"Worst-case regret of {info.elem_desc}"
            if info.elem_desc
            else f"Worst-case regret of {info.elem_name}",
            symbol=regret_sym,
            func=t_sym,
            maximize=False,
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
        info = resolve_elem(sym, symbol_maps, combined, scenario_model)
        terms = [["Multiply", weights[leaf], info.per_leaf[leaf]] for leaf in leaf_scenarios]
        weighted_sym = f"{prefix}{sym}"
        added_symbols[sym] = weighted_sym

        append_aggregated_elem(
            info.found_type,
            new_objectives,
            new_scal_funcs,
            new_extra_funcs,
            name=f"Weighted {info.elem_name}",
            description=f"Weighted scenario value of {info.elem_desc}"
            if info.elem_desc
            else f"Weighted scenario value of {info.elem_name}",
            symbol=weighted_sym,
            func=terms[0] if len(terms) == 1 else ["Add", *terms],
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
