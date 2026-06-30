"""Functions related to the CUMULUS method.

References:
    TBD
"""

from enum import Enum

import numpy as np

from desdeo.mcdm.reference_point_method import rpm_intermediate_solutions
from desdeo.problem import (
    ConstraintTypeEnum,
    Problem,
    ScenarioModel,
    add_soft_constraint,
)
from desdeo.problem.schema import Constraint
from desdeo.tools import (
    BaseSolver,
    SolverOptions,
    SolverResults,
    add_asf_diff,
    add_asf_nondiff,
    add_asf_partial_diff,
    add_asf_partial_nondiff,
    add_cumulonimbus_diff,
    build_scenario_symbol_maps,
    guess_best_solver,
)


class CumulusError(Exception):
    """Raised when an error with a CUMULUS method is encountered."""


class CumulusScalarization(Enum):
    """Scalarization functions compatible with the CUMULUS method.

    All variants operate on a partial reference point — they only scalarize
    the objectives whose symbols appear in the reference point supplied to
    `solve_sub_problems`.  Objectives absent from the reference point
    are left unconstrained.
    """

    CUMULONIMBUS = "cumulonimbus"
    """Partial NIMBUS scalarization (`add_cumulonimbus_diff`).

    Derives classifications from the reference point and current objective
    values, then builds NIMBUS-style improvement/reservation constraints only
    for the classified objectives.  Requires ideal and nadir to be defined for
    every objective present in the reference point.
    """

    ASF_PARTIAL = "asf_partial"
    """Partial ASF (`add_asf_partial_diff` or `add_asf_partial_nondiff`).

    Minimizes an achievement scalarizing function over the subset of objectives
    in the reference point.  No classification step is performed.  The
    differentiable variant is used unless the problem is non-differentiable
    *and* has no constraints, in which case the non-differentiable variant is
    used automatically.
    """


def solve_intermediate_solutions(
    problem: Problem,
    solution_1: dict[str, float],
    solution_2: dict[str, float],
    num_desired: int,
    scalarization_options: dict | None = None,
    solver: BaseSolver | None = None,
    solver_options: SolverOptions | None = None,
) -> list[SolverResults]:
    """Generates a desired number of intermediate solutions between two given solutions.

    Interpolates between ``solution_1`` and ``solution_2`` in objective space and projects
    each interpolated reference point onto the Pareto front via an ASF solve.  The returned
    list contains ``num_desired`` solutions strictly between the two endpoints.

    Args:
        problem (Problem): the problem being solved.
        solution_1 (dict[str, float]): objective vector of the first endpoint.
        solution_2 (dict[str, float]): objective vector of the second endpoint.
        num_desired (int): number of intermediate solutions to generate. Must be at least ``1``.
        scalarization_options (dict | None, optional): extra kwargs forwarded to the ASF builder.
        solver (BaseSolver | None, optional): solver class to use. Defaults to the best
            compatible solver inferred from ``problem``.
        solver_options (SolverOptions | None, optional): options passed to ``solver``.

    Returns:
        list[SolverResults]: intermediate solutions projected onto the Pareto front.
    """
    return rpm_intermediate_solutions(
        problem,
        solution_1,
        solution_2,
        num_desired,
        scalarization_options=scalarization_options,
        solver=solver,
        solver_options=solver_options,
    )


def infer_classifications(
    problem: Problem, current_objectives: dict[str, float], reference_point: dict[str, float]
) -> dict[str, tuple[str, float | None]]:
    r"""Infers CUMULUS classifications for the objectives present in ``reference_point``.

    Only the objectives whose symbols appear as keys in ``reference_point`` are
    classified.  Objectives absent from ``reference_point`` are left out of the
    returned dict and are treated as free by the scalarization functions.

    The following classifications are inferred for each active objective:

    - $I^{<}$: values that should improve, the reference point value of an objective
        function is equal to its ideal value;
    - $I^{\leq}$: values that should improve until a given aspiration level, the reference point
        value of an objective function is better than the current value;
    - $I^{=}$: values that should stay as they are, the reference point value of an objective
        function is equal to the current value;
    - $I^{\geq}$: values that can be impaired until some reservation level, the reference point
        value of an objective function is worse than the current value; and
    - $I^{\diamond}$: values that are allowed to change freely, the reference point value of
        and objective function is equal to its nadir value.

    Raises:
        CumulusError: any key in ``reference_point`` is not a valid objective symbol.
        CumulusError: any active objective is missing an ideal or nadir value.
        CumulusError: ``current_objectives`` is missing an entry for one or more active objectives.

    Args:
        problem (Problem): the problem the current objectives and the reference point
            are related to.
        current_objectives (dict[str, float]): objective values for the current solution.
            Must contain entries for every objective present in ``reference_point``.
        reference_point (dict[str, float]): partial or full objective dict with reference
            point values.  Only objectives whose symbols appear here are classified.

    Returns:
        dict[str, tuple[str, float | None]]: a dict whose keys are the symbols of the
            active objectives and whose values are ``(classification, level)`` tuples.
            The level is ``None`` unless the classification is ``"<="`` (aspiration) or
            ``">="`` (reservation).
    """
    valid_symbols = {obj.symbol for obj in problem.objectives}
    invalid = set(reference_point) - valid_symbols
    if invalid:
        msg = f"reference_point contains keys that are not objective symbols: {invalid}."
        raise CumulusError(msg)

    active_objectives = [obj for obj in problem.objectives if obj.symbol in reference_point]

    missing_ideal = [obj.symbol for obj in active_objectives if obj.ideal is None]
    missing_nadir = [obj.symbol for obj in active_objectives if obj.nadir is None]
    if missing_ideal or missing_nadir:
        msg = f"Active objectives are missing ideal values: {missing_ideal}, nadir values: {missing_nadir}."
        raise CumulusError(msg)

    missing_current = [obj.symbol for obj in active_objectives if obj.symbol not in current_objectives]
    if missing_current:
        msg = f"current_objectives is missing entries for active objectives: {missing_current}."
        raise CumulusError(msg)

    classifications = {}

    for obj in active_objectives:
        rp_val = reference_point[obj.symbol]

        # For minimized objectives the ideal/nadir are in the same space as rp_val.
        # Guard against an aspiration better than ideal (would cause solver infeasibility).
        if not obj.maximize and rp_val < obj.ideal:
            classifications |= {obj.symbol: ("<", None)}
            continue

        if np.isclose(rp_val, obj.nadir):
            # the objective is free to change
            classification = {obj.symbol: ("0", None)}
        elif np.isclose(rp_val, obj.ideal):
            # the objective should improve
            classification = {obj.symbol: ("<", None)}
        elif np.isclose(rp_val, current_objectives[obj.symbol]):
            # the objective should stay as it is
            classification = {obj.symbol: ("=", None)}
        elif not obj.maximize and rp_val < current_objectives[obj.symbol]:
            # minimizing objective, reference value smaller: aspiration level
            classification = {obj.symbol: ("<=", rp_val)}
        elif not obj.maximize and rp_val > current_objectives[obj.symbol]:
            # minimizing objective, reference value greater: reservation level
            classification = {obj.symbol: (">=", rp_val)}
        elif obj.maximize and rp_val < current_objectives[obj.symbol]:
            # maximizing objective, reference value smaller: reservation level
            classification = {obj.symbol: (">=", rp_val)}
        elif obj.maximize and rp_val > current_objectives[obj.symbol]:
            # maximizing objective, reference value greater: aspiration level
            classification = {obj.symbol: ("<=", rp_val)}
        else:
            msg = f"Warning: CUMULUS could not figure out the classification for objective {obj.symbol}."
            raise CumulusError(msg)

        classifications |= classification

    return classifications


def _scenario_aug_weights(
    problem: Problem,
    reference_point: dict[str, float],
    symbol_maps: "dict[str, dict[str, dict[str, str]]]",
) -> dict[str, float]:
    """Compute ``weights_aug`` that restricts augmentation to per-scenario objectives.

    When the combined problem contains both per-scenario objectives (e.g. ``s0_f_1``,
    ``s1_f_1``) and aggregation objectives (e.g. ``E_f_1``), the default augmentation
    would include whichever objectives appear in ``reference_point`` — usually the
    aggregation ones.  This is undesirable: the augmentation should pull on the
    per-scenario realizations so the solver is guided towards good outcomes across all
    scenarios, not just the aggregate.

    This function returns a ``weights_aug`` dict where:

    - every objective in ``reference_point`` is initialised to weight ``0``;
    - every per-scenario objective that has both ``ideal`` and ``nadir`` defined receives
      weight ``nadir - ideal`` (positive for minimize, negative for maximize), overwriting
      the initial 0 if the objective also appears in ``reference_point``;
    - per-scenario objectives missing ``ideal`` or ``nadir`` are omitted (no augmentation
      contribution, avoiding division-by-zero).

    Args:
        problem: the combined scenario problem being solved.
        reference_point: the partial reference point passed to the scalarization.
        symbol_maps: symbol maps from `build_scenario_symbol_maps`.

    Returns:
        dict[str, float]: augmentation weights keyed by objective symbol.
    """
    per_scenario_syms: set[str] = {
        combined_sym for leaf_map in symbol_maps.get("objectives", {}).values() for combined_sym in leaf_map.values()
    }
    obj_by_sym = {obj.symbol: obj for obj in problem.objectives}
    weights_aug: dict[str, float] = dict.fromkeys(reference_point, 0.0)
    for sym in per_scenario_syms:
        obj = obj_by_sym.get(sym)
        if obj is not None and obj.ideal is not None and obj.nadir is not None:
            weights_aug[sym] = obj.nadir - obj.ideal
    return weights_aug


def _apply_scalarization(
    problem: Problem,
    sf: "CumulusScalarization",
    scalarization_options: dict | None,
    current_objectives: dict[str, float],
    reference_point: dict[str, float],
) -> tuple[Problem, str]:
    """Apply one CUMULUS scalarization to *problem* and return the augmented problem and target symbol."""
    match sf:
        case CumulusScalarization.CUMULONIMBUS:
            classifications = infer_classifications(problem, current_objectives, reference_point)
            return add_cumulonimbus_diff(
                problem, "cumulonimbus_sf", classifications, current_objectives, **(scalarization_options or {})
            )
        case CumulusScalarization.ASF_PARTIAL:
            use_nondiff = not problem.is_twice_differentiable and not problem.constraints
            if use_nondiff:
                return add_asf_partial_nondiff(
                    problem, "asf_partial_sf", reference_point, **(scalarization_options or {})
                )
            return add_asf_partial_diff(problem, "asf_partial_sf", reference_point, **(scalarization_options or {}))
        case _:
            msg = f"Unsupported scalarization function: {sf}."
            raise CumulusError(msg)


def _solve_with_constraints(
    problem: Problem,
    scalarizations: list["CumulusScalarization"],
    hard_constraints: list[Constraint] | None,
    soft_constraints: list[Constraint] | None,
    solve_one,
    init_solver,
    solver_options,
) -> "dict[CumulusScalarization, SolverResults | None]":
    """Solve all scalarizations with optional soft-constraint relaxation.

    Builds the base problem with hard and soft constraints attached, solves every
    scalarization, and returns immediately if at least one succeeded.  When every
    sub-problem is infeasible, relaxes the soft constraints via `add_soft_constraint`,
    locks in the minimum total violation as a budget constraint, and re-solves.
    """
    base_problem = problem
    if hard_constraints:
        base_problem = base_problem.add_constraints(hard_constraints)
    if soft_constraints:
        base_problem = base_problem.add_constraints(soft_constraints)

    solutions: dict[CumulusScalarization, SolverResults | None] = {
        sf: solve_one(base_problem, sf) for sf in scalarizations
    }

    if any(r is not None for r in solutions.values()) or not soft_constraints:
        return solutions

    relaxed_problem, violation_symbol, optimal_violation = _minimize_soft_constraint_violations(
        problem, hard_constraints, soft_constraints, init_solver, solver_options
    )

    relaxed_problem = relaxed_problem.add_constraints(
        [
            Constraint(
                name="Soft constraint violation budget",
                symbol="_violation_budget",
                cons_type=ConstraintTypeEnum.LTE,
                func=["Subtract", f"{violation_symbol}_min", optimal_violation],
            )
        ]
    )

    return {sf: solve_one(relaxed_problem, sf) for sf in scalarizations}


def _minimize_soft_constraint_violations(
    problem: Problem,
    hard_constraints: list[Constraint] | None,
    soft_constraints: list[Constraint],
    init_solver,
    solver_options,
) -> tuple[Problem, str, float]:
    """Builds a relaxed problem and minimizes its total soft-constraint violation.

    Slackens each soft constraint via `add_soft_constraint`, which accumulates all
    violations into a single objective, then solves for the minimum total violation
    subject to the hard constraints.

    Args:
        problem: the base problem (no constraints already attached).
        hard_constraints: constraints that must always hold.
        soft_constraints: constraints that may be relaxed.
        init_solver: solver class or factory.
        solver_options: options forwarded to the solver (or ``None``).

    Raises:
        CumulusError: no optimal solution could be found for the violation-minimization
            sub-problem, e.g. because the hard constraints alone are infeasible.

    Returns:
        A 3-tuple ``(relaxed_problem, violation_symbol, optimal_violation)`` where
        *relaxed_problem* has the soft constraints slackened and a violation objective
        added, *violation_symbol* is that objective's symbol, and *optimal_violation*
        is the minimized total violation value.
    """
    relaxed_problem = problem
    if hard_constraints:
        relaxed_problem = relaxed_problem.add_constraints(hard_constraints)

    violation_symbol = "_soft_constraint_violation"
    for sc in soft_constraints:
        relaxed_problem, violation_symbol = add_soft_constraint(relaxed_problem, sc, symbol=violation_symbol)

    viol_inst = init_solver(relaxed_problem, solver_options) if solver_options else init_solver(relaxed_problem)
    viol_result = viol_inst.solve(violation_symbol)
    if viol_result is None or not viol_result.success:
        msg = (
            "Could not find an optimal solution while minimizing soft constraint violations. "
            "The hard constraints may be infeasible on their own."
        )
        raise CumulusError(msg)
    optimal_violation: float = viol_result.optimal_objectives[violation_symbol]

    return relaxed_problem, violation_symbol, optimal_violation


def _fix_worst_case_epigraphs(
    result: SolverResults,
    problem: Problem,
    symbol_maps: "dict[str, dict[str, dict[str, str]]]",
) -> SolverResults:
    """Tighten worst-case epigraph variables to the true max/min of leaf values.

    Solvers have no incentive to minimise ``t`` when it backs an extra function rather
    than the optimisation target; this replaces each such ``t`` with the actual worst
    case implied by the per-leaf bound constraints (`add_worst_case_robust`,
    `add_single_objective_worst_case_regret`).  The per-leaf bound is recovered from
    `constraint_values` rather than the raw leaf objective/extra/scalarization value, so
    this also covers regret-style epigraphs whose bound is offset by a per-leaf ideal
    value baked into the constraint rather than present anywhere in the solved leaf
    values.
    """
    _epigraph_name_prefixes = (
        "Worst-case robust epigraph variable for ",
        "Worst-case regret epigraph variable for ",
    )

    all_base_syms = {s for m in symbol_maps.values() for s in m}
    obj_by_sym = {obj.symbol: obj for obj in problem.objectives}
    new_vars = dict(result.optimal_variables)
    new_objs = dict(result.optimal_objectives)
    new_extra = dict(result.extra_func_values or {})
    new_scal = dict(result.scalarization_values or {})
    constraint_values = result.constraint_values or {}

    for var in problem.variables:
        t_sym = var.symbol
        if not t_sym.startswith("_t_") or not var.name.startswith(_epigraph_name_prefixes):
            continue
        agg_sym = t_sym[len("_t_") :]
        candidates = [s for s in all_base_syms if agg_sym.endswith(s)]
        if not candidates:
            continue
        original_sym = max(candidates, key=len)
        leaf_map = next((m[original_sym] for m in symbol_maps.values() if original_sym in m), None)
        if leaf_map is None or t_sym not in new_vars:
            continue

        t_val = float(new_vars[t_sym])
        obj = obj_by_sym.get(agg_sym)
        is_maximize_t = bool(obj and obj.maximize)

        # LTE constraints are normalised to `func <= 0`.  The per-leaf bound constraint
        # is either `g_s - t <= 0` (minimise-t formulation) or `t - g_s <= 0`
        # (maximise-t formulation), so `g_s` can be recovered from the constraint value.
        bound_vals = []
        for leaf in leaf_map:
            con_sym = f"{leaf}_{agg_sym}_con"
            if con_sym not in constraint_values:
                continue
            cv = float(constraint_values[con_sym])
            bound_vals.append(t_val - cv if is_maximize_t else cv + t_val)
        if not bound_vals:
            continue
        true_worst = min(bound_vals) if is_maximize_t else max(bound_vals)
        new_vars[t_sym] = true_worst
        for d in (new_objs, new_extra, new_scal):
            if agg_sym in d:
                d[agg_sym] = true_worst
                break

    return result.model_copy(
        update={
            "optimal_variables": new_vars,
            "optimal_objectives": new_objs,
            "extra_func_values": new_extra or None,
            "scalarization_values": new_scal or None,
        }
    )


def solve_sub_problems(
    problem: Problem,
    current_objectives: dict[str, float],
    reference_point: dict[str, float],
    scalarizations: list[CumulusScalarization],
    scalarization_options: dict | None = None,
    solver: BaseSolver | None = None,
    solver_options: SolverOptions | None = None,
    hard_constraints: list[Constraint] | None = None,
    soft_constraints: list[Constraint] | None = None,
    scenario_model: ScenarioModel | None = None,
) -> dict[CumulusScalarization, SolverResults | None]:
    r"""Solves one sub-problem per requested scalarization using a partial reference point.

    Unlike the NIMBUS method, CUMULUS does not require the reference point to cover all
    objectives.  Only objectives present in ``reference_point`` are actively scalarized;
    the remaining objectives are left unconstrained.

    Each entry in ``scalarizations`` triggers one solver run:

    - `CumulusScalarization.CUMULONIMBUS`: derives classifications from
      ``reference_point`` and ``current_objectives``, then solves a partial NIMBUS
      scalarization.  Requires ideal and nadir to be defined for every active objective.
    - `CumulusScalarization.ASF_PARTIAL`: solves a partial ASF directly from
      ``reference_point``.  Automatically selects the differentiable variant unless
      the problem is non-differentiable and has no constraints.

    When ``hard_constraints`` and/or ``soft_constraints`` are supplied, the function first
    attempts to solve with all constraints enforced.  If every sub-problem is infeasible,
    the soft constraints are relaxed via slack variables, the minimum total violation is
    computed, that value is locked in as an additional constraint, and all sub-problems are
    re-solved on the relaxed formulation.

    Raises:
        CumulusError: ``scalarizations`` is empty.
        CumulusError: ``reference_point`` contains keys that are not objective symbols.
        CumulusError: `CumulusScalarization.CUMULONIMBUS` is requested but an active
            objective is missing an ideal or nadir value, or ``current_objectives`` does not
            cover all active objectives.

    Args:
        problem (Problem): the problem being solved.
        current_objectives (dict[str, float]): current objective values.  Only entries for
            objectives present in ``reference_point`` are required (and only when
            `CumulusScalarization.CUMULONIMBUS` is included in ``scalarizations``).
        reference_point (dict[str, float]): partial objective dict with reference point
            values.  Only the objectives listed here participate in the scalarizations.
        scalarizations (list[CumulusScalarization]): ordered list of scalarizations to solve.
            One entry is returned per unique scalarization type.
        scalarization_options (dict | None, optional): optional kwargs forwarded to every
            scalarization function.  Defaults to None.
        solver (BaseSolver | None, optional): solver class to use.  If not given, an
            appropriate solver is determined automatically.  Defaults to None.
        solver_options (SolverOptions | None, optional): options passed to the solver.
            Ignored when ``solver`` is ``None``.  Defaults to None.
        hard_constraints (list[Constraint] | None, optional): constraints that must always
            hold.  Never relaxed.  Defaults to None.
        soft_constraints (list[Constraint] | None, optional): constraints that are attempted
            first as hard constraints but may be relaxed if the problem is infeasible.
            Defaults to None.
        scenario_model (ScenarioModel | None, optional): when provided, the augmentation
            weights are automatically set so that only the per-scenario versions of the
            original objectives contribute to the augmentation term.  Aggregation/uncertainty
            objectives present in ``reference_point`` receive weight 0.  Always overrides
            any ``"weights_aug"`` already present in ``scalarization_options``.
            Defaults to None.

    Returns:
        dict[CumulusScalarization, SolverResults | None]: maps each scalarization type to
            its result.  A value of ``None`` means the sub-problem was infeasible even after
            any applicable relaxation; a `SolverResults` instance means the solver
            returned a result (check `success` for whether it is
            optimal).
    """
    if not scalarizations:
        msg = "scalarizations must contain at least one CumulusScalarization value."
        raise CumulusError(msg)

    valid_symbols = {obj.symbol for obj in problem.objectives}
    invalid = set(reference_point) - valid_symbols
    if invalid:
        msg = f"reference_point contains keys that are not objective symbols: {invalid}."
        raise CumulusError(msg)

    init_solver = solver if solver is not None else guess_best_solver(problem)
    _solver_options = solver_options if solver_options is not None else None

    effective_scalarization_options = dict(scalarization_options or {})
    _symbol_maps = None
    if scenario_model is not None:
        _symbol_maps = build_scenario_symbol_maps(problem, scenario_model)
        effective_scalarization_options["weights_aug"] = _scenario_aug_weights(problem, reference_point, _symbol_maps)
        effective_scalarization_options.setdefault("rho", 1e-2)

    def _solve(base: Problem, sf: CumulusScalarization) -> SolverResults | None:
        p, target = _apply_scalarization(base, sf, effective_scalarization_options, current_objectives, reference_point)
        inst = init_solver(p, _solver_options) if _solver_options else init_solver(p)
        result = inst.solve(target)
        return result if result.success else None

    if hard_constraints or soft_constraints:
        results = _solve_with_constraints(
            problem, scalarizations, hard_constraints, soft_constraints, _solve, init_solver, _solver_options
        )
    else:
        results = {sf: _solve(problem, sf) for sf in scalarizations}

    if _symbol_maps is not None:
        results = {
            sf: _fix_worst_case_epigraphs(r, problem, _symbol_maps) if r is not None else None
            for sf, r in results.items()
        }
    return results


def generate_starting_point(
    problem: Problem,
    reference_point: dict[str, float] | None = None,
    scalarization_options: dict | None = None,
    solver: BaseSolver | None = None,
    solver_options: SolverOptions | None = None,
) -> SolverResults:
    r"""Generates a starting point for the CUMULUS method.

    Using the given reference point and achievement scalarizing function, finds one pareto
    optimal solution that can be used as a starting point for the CUMULUS method.
    If no reference point is given, ideal is used as the reference point.

    Instead of using this function, the user can provide a starting point.

    Raises:
        CumulusError: the given problem has an undefined ideal or nadir point, or both.

    Args:
        problem (Problem): the problem being solved.
        reference_point (dict[str, float]|None): an objective dictionary with a reference point.
            If not given, ideal will be used as reference point.
        scalarization_options (dict | None, optional): optional kwargs passed to the scalarization function.
            Defaults to None.
        solver (BaseSolver | None, optional): solver used to solve the problem.
            If not given, an appropriate solver will be automatically determined based on the features of `problem`.
            Defaults to None.
        solver_options (SolverOptions | None, optional): optional options passed
            to the `solver`. Ignored if `solver` is `None`.
            Defaults to None.

    Returns:
        SolverResults: the starting point solution.
    """
    ideal = problem.get_ideal_point()
    nadir = problem.get_nadir_point()
    if None in ideal or None in nadir:
        msg = "The given problem must have both an ideal and nadir point defined."
        raise CumulusError(msg)

    if reference_point is None:
        reference_point = {}
    for obj in problem.objectives:
        if obj.symbol not in reference_point:
            reference_point[obj.symbol] = ideal[obj.symbol]

    init_solver = solver if solver is not None else guess_best_solver(problem)
    _solver_options = solver_options if solver_options is not None else None

    # solve ASF
    add_asf = add_asf_diff if problem.is_twice_differentiable else add_asf_nondiff

    problem_w_asf, asf_target = add_asf(problem, "asf", reference_point, **(scalarization_options or {}))

    asf_solver = init_solver(problem_w_asf, _solver_options) if _solver_options else init_solver(problem_w_asf)

    return asf_solver.solve(asf_target)
