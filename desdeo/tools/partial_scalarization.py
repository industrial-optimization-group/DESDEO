"""Scalarization functions that operate on a subset of the problem's objectives."""

from desdeo.problem import (
    Constraint,
    ConstraintTypeEnum,
    Problem,
    ScalarizationFunction,
    Variable,
    VariableTypeEnum,
)
from desdeo.tools.scalarization import Op, ScalarizationError
from desdeo.tools.utils import get_corrected_ideal, get_corrected_nadir


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
    corrected_rp_aug = (
        {
            obj.symbol: reference_point_aug[obj.symbol] * -1 if obj.maximize else reference_point_aug[obj.symbol]
            for obj in active_objectives
        }
        if reference_point_aug is not None
        else None
    )

    alpha = Variable(
        name="alpha",
        symbol="_alpha",
        variable_type=VariableTypeEnum.real,
        lowerbound=None,
        upperbound=None,
        initial_value=1.0,
    )

    aug_obj_list, aug_weights_dict = _resolve_aug_objectives(
        weights_aug, active_objectives, effective_weights, list(problem.objectives)
    )
    aug_expr = _build_aug_expr(aug_obj_list, corrected_rp_aug if weights_aug is None else None, aug_weights_dict)

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


def add_asf_partial_nondiff(
    problem: Problem,
    symbol: str,
    reference_point: dict[str, float],
    weights: dict[str, float] | None = None,
    reference_point_aug: dict[str, float] | None = None,
    weights_aug: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds a non-differentiable partial ASF that scalarizes only the objectives in ``reference_point``.

    This is the non-differentiable counterpart of :func:`add_asf_partial_diff`.  The max
    operator is expressed directly in the objective function rather than being linearised
    with an auxiliary variable and constraints, making the scalarization non-differentiable.

    \begin{align*}
        \min \quad & \underset{i \in I}{\max}
            \left[\frac{f_i(\mathbf{x}) - q_i}{w_i}\right]
            + \rho \sum_{i \in I} \frac{f_i(\mathbf{x})}{w_i}
    \end{align*}

    where $I$ is the index set of objectives whose symbols appear in ``reference_point``,
    $q_i$ are the corresponding aspiration levels, and $w_i$ are the weights.  When
    ``reference_point_aug`` is provided the augmentation numerator becomes
    $f_i(\mathbf{x}) - q_i^{\text{aug}}$.

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
        ScalarizationError: if any key in ``reference_point`` is not a valid objective symbol.
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
    corrected_rp_aug = (
        {
            obj.symbol: reference_point_aug[obj.symbol] * -1 if obj.maximize else reference_point_aug[obj.symbol]
            for obj in active_objectives
        }
        if reference_point_aug is not None
        else None
    )

    # Build the max term over active objectives only.
    max_operands = [
        f"({obj.symbol}_min - {corrected_rp[obj.symbol]}) / ({effective_weights[obj.symbol]})"
        for obj in active_objectives
    ]
    max_term = f"{Op.MAX}({', '.join(max_operands)})"

    aug_obj_list, aug_weights_dict = _resolve_aug_objectives(
        weights_aug, active_objectives, effective_weights, list(problem.objectives)
    )
    aug_expr = _build_aug_expr(aug_obj_list, corrected_rp_aug if weights_aug is None else None, aug_weights_dict)

    sf = f"{max_term} + {rho} * ({aug_expr})"
    scalarization = ScalarizationFunction(
        name="Partial non-differentiable ASF scalarization",
        symbol=symbol,
        func=sf,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=False,
    )
    return problem.add_scalarization(scalarization), symbol


def _make_constraint(name: str, symbol: str, func: str, problem: Problem) -> Constraint:
    return Constraint(
        name=name,
        symbol=symbol,
        func=func,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=problem.is_twice_differentiable,
    )


def _resolve_ideal_nadir(
    problem: Problem,
    ideal: dict[str, float] | None,
    nadir: dict[str, float] | None,
) -> tuple[dict[str, float], dict[str, float]]:
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined and could not be derived from the problem."
        raise ScalarizationError(msg)

    if nadir is not None:
        nadir_point = nadir
    elif problem.get_nadir_point() is not None:
        nadir_point = get_corrected_nadir(problem)
    else:
        msg = "Nadir point not defined and could not be derived from the problem."
        raise ScalarizationError(msg)

    return ideal_point, nadir_point


def _build_aug_expr(
    aug_objectives: list,
    corrected_rp_aug: dict[str, float] | None,
    effective_aug_weights: dict[str, float],
) -> str:
    """Build the augmentation sum expression string.

    Handles an empty objective list (returns "0") and partial coverage of
    ``corrected_rp_aug``: objectives missing from it fall back to the plain
    ``f_i_min / w_i`` form.
    """
    if not aug_objectives:
        return "0"
    terms = []
    for obj in aug_objectives:
        w = effective_aug_weights[obj.symbol]
        if corrected_rp_aug is not None and obj.symbol in corrected_rp_aug:
            terms.append(f"({obj.symbol}_min - {corrected_rp_aug[obj.symbol]}) / ({w})")
        else:
            terms.append(f"{obj.symbol}_min / ({w})")
    return " + ".join(terms)


def _resolve_aug_objectives(
    weights_aug: dict[str, float] | None,
    active_objectives: list,
    default_weights: dict[str, float],
    all_objectives: list,
) -> tuple[list, dict[str, float]]:
    """Return ``(aug_obj_list, aug_weights_dict)`` for the augmentation term.

    When ``weights_aug`` is provided it defines the full augmentation set:
    objectives with a non-zero weight are included (whether active or not),
    objectives with weight 0 are excluded.  When ``weights_aug`` is ``None``
    the default falls back to ``active_objectives`` and ``default_weights``.
    """
    if weights_aug is not None:
        aug_obj_list = [obj for obj in all_objectives if obj.symbol in weights_aug and weights_aug[obj.symbol] != 0]
        return aug_obj_list, weights_aug
    return active_objectives, default_weights


def _classification_constraints(
    obj,
    cls: str,
    level: float | None,
    range_: str,
    current_val: float,
    maximize_flip: str,
    ideal_val: float,
    problem: Problem,
) -> list[Constraint]:
    sym = obj.symbol
    match (cls, level):
        case ("<", _):
            return [
                _make_constraint(
                    f"improvement constraint for {sym}",
                    f"{sym}_lt",
                    f"({sym}_min - {ideal_val}) / ({range_}) - _alpha",
                    problem,
                ),
                _make_constraint(
                    f"stay at least equal constraint for {sym}",
                    f"{sym}_eq",
                    f"{sym}_min - {current_val}{maximize_flip}",
                    problem,
                ),
            ]
        case ("<=", aspiration):
            return [
                _make_constraint(
                    f"improvement until constraint for {sym}",
                    f"{sym}_lte",
                    f"({sym}_min - {aspiration}{maximize_flip}) / ({range_}) - _alpha",
                    problem,
                ),
                _make_constraint(
                    f"stay at least equal constraint for {sym}",
                    f"{sym}_eq",
                    f"{sym}_min - {current_val}{maximize_flip}",
                    problem,
                ),
            ]
        case ("=", _):
            return [
                _make_constraint(
                    f"stay at least equal constraint for {sym}",
                    f"{sym}_eq",
                    f"{sym}_min - {current_val}{maximize_flip}",
                    problem,
                ),
            ]
        case (">=", reservation):
            return [
                _make_constraint(
                    f"worsen until constraint for {sym}",
                    f"{sym}_gte",
                    f"{sym}_min - {reservation}{maximize_flip}",
                    problem,
                ),
            ]
        case ("0", _):
            return []
        case (c, _):
            msg = (
                f"The classification '{c}' for objective '{sym}' is not supported. "
                "Must be one of ['<', '<=', '=', '>=', '0']."
            )
            raise ScalarizationError(msg)


def add_cumulonimbus_diff(
    problem: Problem,
    symbol: str,
    classifications: dict[str, tuple[str, float | None]],
    current_objective_vector: dict[str, float],
    ideal: dict[str, float] | None = None,
    nadir: dict[str, float] | None = None,
    reference_point_aug: dict[str, float] | None = None,
    weights_aug: dict[str, float] | None = None,
    delta: float = 1e-6,
    rho: float = 1e-3,
) -> tuple[Problem, str]:
    r"""Adds a differentiable partial NIMBUS scalarization that only covers classified objectives.

    This is the partial variant of :func:`desdeo.tools.scalarization.add_nimbus_sf_diff`.
    Unlike the full NIMBUS scalarization, ``classifications`` does not need to cover every
    objective in the problem — objectives whose symbols are absent from ``classifications``
    are left unconstrained (treated as free, equivalent to the ``"0"`` class).

    \begin{align*}
        \min \quad & \alpha + \rho \sum_{i \in I} \frac{f_i(\mathbf{x}) - q_i^{\text{aug}}}{w_i^{\text{aug}}} \\
        \text{s.t.} \quad
        & \frac{f_i(\mathbf{x}) - z_i^\star}{z_i^{\text{nad}} - z_i^{\star\star}} - \alpha \leq 0
            & \forall i \in I^< \\
        & \frac{f_i(\mathbf{x}) - \hat{z}_i}{z_i^{\text{nad}} - z_i^{\star\star}} - \alpha \leq 0
            & \forall i \in I^\leq \\
        & f_i(\mathbf{x}) - f_i(\mathbf{x_c}) \leq 0
            & \forall i \in I^< \cup I^\leq \cup I^= \\
        & f_i(\mathbf{x}) - \varepsilon_i \leq 0
            & \forall i \in I^\geq \\
        & \mathbf{x} \in S,
    \end{align*}

    where $I$ is the index set of classified objectives (keys of ``classifications``),
    $z_i^{\star\star} = z_i^\star - \delta$ is the utopian point component,
    $w_i^{\text{aug}}$ are the augmentation weights (defaulting to $z_i^{\text{nad}} - z_i^{\star\star}$),
    $q_i^{\text{aug}}$ is the optional augmentation reference point (omitted when not provided),
    and all other notation follows :func:`desdeo.tools.scalarization.add_nimbus_sf_diff`.

    Args:
        problem: the problem to be scalarized.
        symbol: the symbol given to the added scalarization function.
        classifications: maps objective symbols to ``(class, level)`` tuples.
            Only objectives listed here participate in the scalarization; others are free.
            Valid classes: ``"<"``, ``"<="``, ``"="``, ``">="`` (with a level), ``"0"``.
        current_objective_vector: current objective values needed for ``<``, ``<=``, and ``=`` constraints.
            Must contain entries for every objective classified as ``"<"``, ``"<="``, or ``"="``.
        ideal: ideal point override. If ``None``, derived from ``problem``.
        nadir: nadir point override. If ``None``, derived from ``problem``.
        reference_point_aug: optional reference point for the augmentation term. When provided,
            each augmentation term becomes ``(f_i - q_i^aug) / w_i^aug`` instead of
            ``f_i / w_i^aug``. Must cover every objective present in ``classifications``.
        weights_aug: optional weights for the augmentation term. Replaces the default
            ``nadir - utopian`` weights. Must cover every objective present in ``classifications``.
        delta: small scalar for the utopian offset. Defaults to 1e-6.
        rho: small scalar for the augmentation term. Defaults to 1e-6.

    Returns:
        A tuple of the updated Problem and the symbol of the added scalarization.

    Raises:
        ScalarizationError: if any key in ``classifications`` is not a valid objective symbol.
        ScalarizationError: if an objective classified as ``"<"``, ``"<="``, or ``"="`` is
            missing from ``current_objective_vector``.
        ScalarizationError: if ideal or nadir cannot be determined for an active objective.
        ScalarizationError: if ``reference_point_aug`` or ``weights_aug`` are provided but
            do not cover all objectives present in ``classifications``.
    """
    valid_symbols = {obj.symbol for obj in problem.objectives}
    invalid = set(classifications) - valid_symbols
    if invalid:
        msg = f"classifications contains keys that are not objective symbols: {invalid}."
        raise ScalarizationError(msg)

    active_symbols = set(classifications)
    active_objectives = [obj for obj in problem.objectives if obj.symbol in active_symbols]

    need_current = {sym for sym, (cls, _) in classifications.items() if cls in ("<", "<=", "=")}
    missing_current = need_current - set(current_objective_vector)
    if missing_current:
        msg = f"current_objective_vector is missing entries for objectives: {missing_current}."
        raise ScalarizationError(msg)

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

    ideal_point, nadir_point = _resolve_ideal_nadir(problem, ideal, nadir)

    corrected_rp_aug = (
        {
            obj.symbol: reference_point_aug[obj.symbol] * -1 if obj.maximize else reference_point_aug[obj.symbol]
            for obj in active_objectives
        }
        if reference_point_aug is not None
        else None
    )
    alpha = Variable(
        name="alpha",
        symbol="_alpha",
        variable_type=VariableTypeEnum.real,
        lowerbound=None,
        upperbound=None,
        initial_value=1.0,
    )

    default_aug_weights = {
        obj.symbol: nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta) for obj in active_objectives
    }
    aug_obj_list, aug_weights_dict = _resolve_aug_objectives(
        weights_aug, active_objectives, default_aug_weights, list(problem.objectives)
    )
    aug_expr = _build_aug_expr(aug_obj_list, corrected_rp_aug if weights_aug is None else None, aug_weights_dict)
    scalarization = ScalarizationFunction(
        name="Cumulonimbus scalarization objective function",
        symbol=symbol,
        func=f"_alpha + {rho}*({aug_expr})",
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=problem.is_twice_differentiable,
    )

    constraints = []
    for obj in active_objectives:
        cls, level = classifications[obj.symbol]
        range_ = f"{nadir_point[obj.symbol]} - {ideal_point[obj.symbol] - delta}"
        maximize_flip = " * -1" if obj.maximize else ""
        current_val = current_objective_vector.get(obj.symbol, 0.0)
        constraints.extend(
            _classification_constraints(
                obj, cls, level, range_, current_val, maximize_flip, ideal_point[obj.symbol], problem
            )
        )

    _problem = problem.add_variables([alpha])
    _problem = _problem.add_scalarization(scalarization)
    return _problem.add_constraints(constraints), symbol
