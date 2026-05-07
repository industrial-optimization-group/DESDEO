"""Scalarization functions that operate on a subset of the problem's objectives."""

from desdeo.problem import (
    Constraint,
    ConstraintTypeEnum,
    Problem,
    ScalarizationFunction,
    Variable,
    VariableTypeEnum,
)
from desdeo.tools.scalarization import ScalarizationError


def add_asf_partial_diff(
    problem: Problem,
    symbol: str,
    reference_point: dict[str, float],
    weights: dict[str, float] | None = None,
    reference_point_aug: dict[str, float] | None = None,
    weights_aug: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds a differentiable generic ASF that scalarizes only the objectives in ``reference_point``.

    This is the partial version of :func:`desdeo.tools.scalarization.add_asf_generic_diff`.
    The subset of objectives to scalarize is determined by the keys of ``reference_point``;
    objectives not present in ``reference_point`` are left out of both the max-term constraints
    and the augmentation sum.

    \begin{align*}
        \min \quad & \alpha + \rho \sum_{i \in I} \frac{f_i(\mathbf{x})}{w_i} \\
        \text{s.t.} \quad & \frac{f_i(\mathbf{x}) - q_i}{w_i} - \alpha \leq 0, \quad i \in I,\\
        & \mathbf{x} \in S,
    \end{align*}

    where $I$ is the index set of objectives whose symbols appear in ``reference_point``,
    $q_i$ are the corresponding aspiration levels, and $w_i$ are the weights.

    When ``weights`` is ``None`` the weights default to ``nadir_i - ideal_i`` (in the
    minimization-corrected space) for each active objective.  In that case every active
    objective must have both ``ideal`` and ``nadir`` defined on its ``Objective`` instance,
    otherwise a :class:`ScalarizationError` is raised.

    Args:
        problem: the problem the scalarization is added to.
        symbol: the symbol given to the added scalarization function.
        reference_point: maps objective symbols to aspiration levels.  Only objectives
            whose symbols appear here are included in the scalarization.
        weights: maps the same objective symbols to positive weight values.  If ``None``,
            defaults to ``nadir - ideal`` for each active objective.
        reference_point_aug: optional separate reference point for the augmentation term.
            Must cover the same subset as ``reference_point`` when provided.
        weights_aug: optional separate weights for the augmentation term.
            Must cover the same subset as ``reference_point`` when provided.
        rho: small scalar multiplier for the augmentation sum. Defaults to 1e-6.

    Returns:
        A tuple of the updated Problem and the symbol of the added scalarization.

    Raises:
        ScalarizationError: if any key in ``reference_point`` is not a valid objective
            symbol in the problem.
        ScalarizationError: if ``weights`` is provided but does not cover all active objectives.
        ScalarizationError: if ``weights`` is ``None`` and any active objective is missing
            an ``ideal`` or ``nadir`` value.
        ScalarizationError: if ``reference_point_aug`` or ``weights_aug`` are provided but
            do not cover the same subset as ``reference_point``.
    """
    valid_symbols = {obj.symbol for obj in problem.objectives}

    invalid = set(reference_point) - valid_symbols
    if invalid:
        msg = f"reference_point contains keys that are not objective symbols: {invalid}."
        raise ScalarizationError(msg)

    active_symbols = set(reference_point)
    active_objectives = [obj for obj in problem.objectives if obj.symbol in active_symbols]

    if weights is not None:
        missing_weights = active_symbols - set(weights)
        if missing_weights:
            msg = f"weights is missing values for objectives: {missing_weights}."
            raise ScalarizationError(msg)
        effective_weights = weights
    else:
        missing_ideal = [obj.symbol for obj in active_objectives if obj.ideal is None]
        missing_nadir = [obj.symbol for obj in active_objectives if obj.nadir is None]
        if missing_ideal:
            msg = f"weights not provided and ideal is missing for objectives: {missing_ideal}."
            raise ScalarizationError(msg)
        if missing_nadir:
            msg = f"weights not provided and nadir is missing for objectives: {missing_nadir}."
            raise ScalarizationError(msg)
        # Compute corrected nadir - corrected ideal in the minimization space.
        effective_weights = {obj.symbol: abs(obj.nadir - obj.ideal) for obj in active_objectives}

    if reference_point_aug is not None:
        missing_aug = active_symbols - set(reference_point_aug)
        if missing_aug:
            msg = f"reference_point_aug is missing values for objectives: {missing_aug}."
            raise ScalarizationError(msg)

    if weights_aug is not None:
        missing_waug = active_symbols - set(weights_aug)
        if missing_waug:
            msg = f"weights_aug is missing values for objectives: {missing_waug}."
            raise ScalarizationError(msg)

    # Flip reference point values for maximized objectives.
    corrected_rp = {
        obj.symbol: reference_point[obj.symbol] * -1 if obj.maximize else reference_point[obj.symbol]
        for obj in active_objectives
    }
    if reference_point_aug is not None:
        corrected_rp_aug = {
            obj.symbol: reference_point_aug[obj.symbol] * -1 if obj.maximize else reference_point_aug[obj.symbol]
            for obj in active_objectives
        }

    alpha = Variable(
        name="alpha",
        symbol="_alpha",
        variable_type=VariableTypeEnum.real,
        lowerbound=-float("Inf"),
        upperbound=float("Inf"),
        initial_value=1.0,
    )

    aug_weights = weights_aug if weights_aug is not None else effective_weights

    if reference_point_aug is None:
        aug_expr = " + ".join([f"({obj.symbol}_min / {aug_weights[obj.symbol]})" for obj in active_objectives])
    else:
        aug_expr = " + ".join(
            [
                f"(({obj.symbol}_min - {corrected_rp_aug[obj.symbol]}) / {aug_weights[obj.symbol]})"
                for obj in active_objectives
            ]
        )

    target_expr = f"_alpha + {rho}*({aug_expr})"
    scalarization = ScalarizationFunction(
        name="Partial generic ASF scalarization",
        symbol=symbol,
        func=target_expr,
        is_convex=problem.is_convex,
        is_linear=problem.is_linear,
        is_twice_differentiable=problem.is_twice_differentiable,
    )

    constraints = []
    for obj in active_objectives:
        expr = f"({obj.symbol}_min - {corrected_rp[obj.symbol]}) / {effective_weights[obj.symbol]} - _alpha"
        constraints.append(
            Constraint(
                name=f"Constraint for {obj.symbol}",
                symbol=f"{obj.symbol}_con",
                func=expr,
                cons_type=ConstraintTypeEnum.LTE,
                is_linear=obj.is_linear,
                is_convex=obj.is_convex,
                is_twice_differentiable=obj.is_twice_differentiable,
            )
        )

    _problem = problem.add_variables([alpha])
    _problem = _problem.add_scalarization(scalarization)
    return _problem.add_constraints(constraints), symbol
