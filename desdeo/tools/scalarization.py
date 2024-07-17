"""Defines various functions for scalarizing multiobjective optimization problems.

Note that when scalarization functions are defined, they must add the post-fix
'_min' to any symbol representing objective functions so that the maximization
or minimization of the corresponding objective functions may be correctly
accounted for when computing scalarization function values.
"""

import numpy as np

from desdeo.problem import (
    Constraint,
    ConstraintTypeEnum,
    Problem,
    ScalarizationFunction,
    Variable,
    VariableTypeEnum,
)
from desdeo.tools.utils import (
    get_corrected_ideal_and_nadir,
    get_corrected_reference_point,
)


class ScalarizationError(Exception):
    """Raised when issues with creating or adding scalarization functions are encountered."""


class Op:
    """Defines the supported operators in the MathJSON format."""

    # TODO: move this to problem/schema.py, make it use this, and import it here from there
    # Basic arithmetic operators
    NEGATE = "Negate"
    ADD = "Add"
    SUB = "Subtract"
    MUL = "Multiply"
    DIV = "Divide"

    # Exponentation and logarithms
    EXP = "Exp"
    LN = "Ln"
    LB = "Lb"
    LG = "Lg"
    LOP = "LogOnePlus"
    SQRT = "Sqrt"
    SQUARE = "Square"
    POW = "Power"

    # Rounding operators
    ABS = "Abs"
    CEIL = "Ceil"
    FLOOR = "Floor"

    # Trigonometric operations
    ARCCOS = "Arccos"
    ARCCOSH = "Arccosh"
    ARCSIN = "Arcsin"
    ARCSINH = "Arcsinh"
    ARCTAN = "Arctan"
    ARCTANH = "Arctanh"
    COS = "Cos"
    COSH = "Cosh"
    SIN = "Sin"
    SINH = "Sinh"
    TAN = "Tan"
    TANH = "Tanh"

    # Comparison operators
    EQUAL = "Equal"
    GREATER = "Greater"
    GREATER_EQUAL = "GreaterEqual"
    LESS = "Less"
    LESS_EQUAL = "LessEqual"
    NOT_EQUAL = "NotEqual"

    # Other operators
    MAX = "Max"
    RATIONAL = "Rational"


def objective_dict_has_all_symbols(problem: Problem, obj_dict: dict[str, float]) -> bool:
    """Check that a dict has all the objective function symbols of a problem as its keys.

    Args:
        problem (Problem): the problem with the objective symbols.
        obj_dict (dict[str, float]): a dict that should have a key for each objective symbol.

    Returns:
        bool: whether all the symbols are present or not.
    """
    return all(obj.symbol in obj_dict for obj in problem.objectives)


def add_asf_nondiff(
    problem: Problem,
    symbol: str,
    reference_point: dict[str, float],
    reference_in_aug=False,
    delta: float = 0.000001,
    rho: float = 0.000001,
) -> tuple[Problem, str]:
    r"""Add the achievement scalarizing function for a problem with the reference point.

    This is the non-differentiable variant of the achievement scalarizing function, which
    means the resulting scalarization function is non-differentiable.
    Requires that the ideal and nadir point have been defined for the problem.

    The scalarization is defined as follows:

    \begin{equation}
        \mathcal{S}_\text{ASF}(F(\mathbf{x}); \mathbf{q}, \mathbf{z}^\star, \mathbf{z}^\text{nad}) =
        \underset{i=1,\ldots,k}{\text{max}}
        \left[
        \frac{f_i(\mathbf{x}) - q_i}{z^\text{nad}_i - (z_i^\star - \delta)}
        \right]
        + \rho\sum_{i=1}^{k} \frac{f_i(\mathbf{x})}{z_i^\text{nad} - (z_i^\star - \delta)},
    \end{equation}

    where $\mathbf{q} = [q_1,\dots,q_k]$ is a reference point, $\mathbf{z^\star} = [z_1^\star,\dots,z_k^\star]$
    is the ideal point, $\mathbf{z}^\text{nad} = [z_1^\text{nad},\dots,z_k^\text{nad}]$ is the nadir point, $k$
    is the number of objective functions, and $\delta$ and $\rho$ are small scalar values. The summation term
    in the scalarization is known as the _augmentation term_. If the reference point is chosen to
    be used in the augmentation term (`reference_in_aug=True`), then
    the reference point components are subtracted from the objective function values in the nominator
    of the augmentation term. That is:

    \begin{equation}
        \mathcal{S}_\text{ASF}(F(\mathbf{x}); \mathbf{q}, \mathbf{z}^\star, \mathbf{z}^\text{nad}) =
        \underset{i=1,\ldots,k}{\text{max}}
        \left[
        \frac{f_i(\mathbf{x}) - q_i}{z^\text{nad}_i - (z_i^\star - \delta)}
        \right]
        + \rho\sum_{i=1}^{k} \frac{f_i(\mathbf{x}) - q_i}{z_i^\text{nad} - (z_i^\star - \delta)}.
    \end{equation}

    Args:
        problem (Problem): the problem to which the scalarization function should be added.
        symbol (str): the symbol to reference the added scalarization function.
        reference_point (dict[str, float]): a reference point as an objective dict.
        reference_in_aug (bool): whether the reference point should be used in
            the augmentation term as well. Defaults to False.
        delta (float, optional): the scalar value used to define the utopian point (ideal - delta).
            Defaults to 0.000001.
        rho (float, optional): the weight factor used in the augmentation term. Defaults to 0.000001.

    Raises:
        ScalarizationError: there are missing elements in the reference point, or if any of the ideal or nadir
            point values are undefined (None).

    Returns:
        tuple[Problem, str]: A tuple containing a copy of the problem with the scalarization function added,
            and the symbol of the added scalarization function.
    """
    # check that the reference point has all the objective components
    if not objective_dict_has_all_symbols(problem, reference_point):
        msg = f"The given reference point {reference_point} does not have a component defined for all the objectives."
        raise ScalarizationError(msg)

    # check if minimizing or maximizing and adjust ideal and nadir values correspondingly
    ideal_point, nadir_point = get_corrected_ideal_and_nadir(problem)

    if any(value is None for value in ideal_point.values()) or any(value is None for value in nadir_point.values()):
        msg = f"There are undefined values in either the ideal ({ideal_point}) or the nadir point ({nadir_point})."
        raise ScalarizationError(msg)

    # Build the max term
    max_operands = [
        (
            f"({obj.symbol}_min - {reference_point[obj.symbol]}{" * -1" if obj.maximize else ''}) "
            f"/ ({nadir_point[obj.symbol]} - ({ideal_point[obj.symbol]} - {delta}))"
        )
        for obj in problem.objectives
    ]
    max_term = f"{Op.MAX}({', '.join(max_operands)})"

    # Build the augmentation term
    if not reference_in_aug:
        aug_operands = [
            f"{obj.symbol}_min / ({nadir_point[obj.symbol]} - ({ideal_point[obj.symbol]} - {delta}))"
            for obj in problem.objectives
        ]
    else:
        aug_operands = [
            (
                f"({obj.symbol}_min - {reference_point[obj.symbol]}{" * -1" if obj.maximize else 1}) "
                f"/ ({nadir_point[obj.symbol]} - ({ideal_point[obj.symbol]} - {delta}))"
            )
            for obj in problem.objectives
        ]

    aug_term = " + ".join(aug_operands)

    asf_function = f"{max_term} + {rho} * ({aug_term})"

    # Add the function to the problem
    scalarization_function = ScalarizationFunction(
        name="Achievement scalarizing function",
        symbol=symbol,
        func=asf_function,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=False,
    )
    return problem.add_scalarization(scalarization_function), symbol


def add_asf_generic_diff(
    problem: Problem,
    symbol: str,
    reference_point: dict[str, float],
    weights: dict[str, float],
    reference_point_aug: dict[str, float] | None = None,
    weights_aug: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds the differentiable variant of the generic achievement scalarizing function.

    \begin{align*}
        \min \quad & \alpha + \rho \sum_{i=1}^k \frac{f_i(\mathbf{x})}{w_i} \\
        \text{s.t.} \quad & \frac{f_i(\mathbf{x}) - q_i}{w_i} - \alpha \leq 0,\\
        & \mathbf{x} \in S,
    \end{align*}

    where $f_i$ are objective functions, $q_i$ is a component of the reference point,
    and $w_i$ are components of the weight vector (which are assumed to be positive),
    $\rho$ and $\delta$ are small scalar values, $S$ is the feasible solution
    space of the original problem, and $\alpha$ is an auxiliary variable.
    The summation term in the scalarization is known as the _augmentation term_.
    If a reference point is chosen to be used in the augmentation term, e.g., a separate
    reference point for the augmentation term is given (`reference_point_aug`), then
    the reference point components are subtracted from the objective function values
    in the nominator of the augmentation term. That is:

    \begin{align*}
        \min \quad & \alpha + \rho \sum_{i=1}^k \frac{f_i(\mathbf{x}) - q_i}{w_i} \\
        \text{s.t.} \quad & \frac{f_i(\mathbf{x}) - q_i}{w_i} - \alpha \leq 0,\\
        & \mathbf{x} \in S,
    \end{align*}

    References:
        Wierzbicki, A. P. (1982). A mathematical basis for satisficing decision
            making. Mathematical modelling, 3(5), 391-405.

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_point (dict[str, float]): a dict with keys corresponding to objective
            function symbols and values to reference point components, i.e.,
            aspiration levels.
        weights (dict[str, float]): the weights to be used in the scalarization function. Must be positive.
        reference_point_aug (dict[str, float], optional): a dict with keys corresponding to objective
            function symbols and values to reference point components for the augmentation term, i.e.,
            aspiration levels. Defeults to None.
        weights_aug (dict[str, float], optional): the weights to be used in the scalarization function's
            augmentation term. Must be positive. Defaults to None.
        rho (float, optional): a small scalar value to scale the sum in the objective
            function of the scalarization. Defaults to 1e-6.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """
    # check reference point
    if not objective_dict_has_all_symbols(problem, reference_point):
        msg = f"The give reference point {reference_point} is missing a value for one or more objectives."
        raise ScalarizationError(msg)

    # check augmentation term reference point
    if reference_point_aug is not None and not objective_dict_has_all_symbols(problem, reference_point_aug):
        msg = f"The given reference point for the augmentation term {reference_point_aug} does not have a component defined for all the objectives."
        raise ScalarizationError(msg)

    # check the weight vector
    if not objective_dict_has_all_symbols(problem, weights):
        msg = f"The given weight vector {weights} is missing a value for one or more objectives."
        raise ScalarizationError(msg)

    # check the weight vector for the augmentation term
    if weights_aug is not None and not objective_dict_has_all_symbols(problem, weights_aug):
        msg = f"The given weight vector {weights_aug} is missing a value for one or more objectives."
        raise ScalarizationError(msg)

    ideal_point, nadir_point = get_corrected_ideal_and_nadir(problem)
    corrected_rp = get_corrected_reference_point(problem, reference_point)
    if reference_point_aug is not None:
        corrected_rp_aug = get_corrected_reference_point(problem, reference_point_aug)

    # define the auxiliary variable
    alpha = Variable(name="alpha", symbol="_alpha", variable_type=VariableTypeEnum.real, lowerbound=-float("Inf"), upperbound=float("Inf"), initial_value=1.0)

    # define the augmentation term
    if reference_point_aug is None and weights_aug is None:
        # no reference point in augmentation term
        # same weights for both terms
        aug_expr = " + ".join([f"({obj.symbol}_min / {weights[obj.symbol]})" for obj in problem.objectives])
    elif reference_point_aug is None and weights_aug is not None:
        # different weights provided for augmentation term
        aug_expr = " + ".join([f"({obj.symbol}_min / {weights_aug[obj.symbol]})" for obj in problem.objectives])
    elif reference_point_aug is not None and weights_aug is None:
        # reference point in augmentation term
        aug_expr = " + ".join(
            [f"(({obj.symbol}_min - {corrected_rp_aug[obj.symbol]}) / {weights[obj.symbol]})" for obj in problem.objectives]
        )
    else:
        aug_expr = " + ".join(
            [f"(({obj.symbol}_min - {corrected_rp_aug[obj.symbol]}) / {weights_aug[obj.symbol]})" for obj in problem.objectives]
        )

    target_expr = f"_alpha + {rho}*" + f"({aug_expr})"
    scalarization = ScalarizationFunction(
        name="Generic ASF scalarization objective function",
        symbol=symbol,
        func=target_expr,
        is_convex=problem.is_convex,
        is_linear=problem.is_linear,
        is_twice_differentiable=problem.is_twice_differentiable,
    )

    constraints = []

    for obj in problem.objectives:
        expr = f"({obj.symbol}_min - {corrected_rp[obj.symbol]}) / {weights[obj.symbol]} - _alpha"

        # since we are subtracting a constant value, the linearity, convexity,
        # and differentiability of the objective function, and hence the
        # constraint, should not change.
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


def add_asf_generic_nondiff(
    problem: Problem,
    symbol: str,
    reference_point: dict[str, float],
    weights: dict[str, float],
    reference_point_aug: dict[str, float] | None = None,
    weights_aug: dict[str, float] | None = None,
    rho: float = 0.000001,
) -> tuple[Problem, str]:
    r"""Adds the generic achievement scalarizing function to a problem with the given reference point, and weights.

    This is the non-differentiable variant of the generic achievement scalarizing function, which
    means the resulting scalarization function is non-differentiable. Compared to `add_asf_nondiff`, this
    variant is useful, when the problem being scalarized does not have a defined ideal or nadir point,
    or both. The weights should be non-zero to avoid zero division.

    The scalarization is defined as follows:

    \begin{equation}
        \mathcal{S}_\text{ASF}(F(\mathbf{x}); \mathbf{q}, \mathbf{w}) =
        \underset{i=1,\ldots,k}{\text{max}}
        \left[
        \frac{f_i(\mathbf{x}) - q_i}{w_i}
        \right]
        + \rho\sum_{i=1}^{k} \frac{f_i(\mathbf{x})}{w_i},
    \end{equation}

    where $\mathbf{q} = [q_1,\dots,q_k]$ is a reference point, $\mathbf{w} =
    [w_1,\dots,w_k]$ are weights, $k$ is the number of objective functions, and
    $\delta$ and $\rho$ are small scalar values. The summation term in the
    scalarization is known as the _augmentation term_. If a reference point is
    chosen to be used in the augmentation term, e.g., a separate
    reference point for the augmentation term is given (`reference_point_aug`), then
    the reference point components are subtracted from the objective function values
    in the nominator of the augmentation term. That is:

    \begin{equation}
        \mathcal{S}_\text{ASF}(F(\mathbf{x}); \mathbf{q}, \mathbf{w}) =
        \underset{i=1,\ldots,k}{\text{max}}
        \left[
        \frac{f_i(\mathbf{x}) - q_i}{w_i}
        \right]
        + \rho\sum_{i=1}^{k} \frac{f_i(\mathbf{x}) - q_i}{w_i}.
    \end{equation}

    Args:
        problem (Problem): the problem to which the scalarization function should be added.
        symbol (str): the symbol to reference the added scalarization function.
        reference_point (dict[str, float]): a reference point with as many components as there are objectives.
        weights (dict[str, float]): the weights to be used in the scalarization function. must be positive.
        reference_point_aug (dict[str, float], optional): a dict with keys corresponding to objective
            function symbols and values to reference point components for the augmentation term, i.e.,
            aspiration levels. Defeults to None.
        weights_aug (dict[str, float], optional): the weights to be used in the scalarization function's
            augmentation term. Must be positive. Defaults to None.
        rho (float, optional): the weight factor used in the augmentation term. Defaults to 0.000001.

    Raises:
        ScalarizationError: If either the reference point or the weights given are missing any of the objective
            components.
        ScalarizationError: If any of the ideal or nadir point values are undefined (None).

    Returns:
        tuple[Problem, str]: A tuple containing a copy of the problem with the scalarization function added,
            and the symbol of the added scalarization function.
    """
    # check reference point
    if not objective_dict_has_all_symbols(problem, reference_point):
        msg = f"The give reference point {reference_point} is missing a value for one or more objectives."
        raise ScalarizationError(msg)

    # check augmentation term reference point
    if reference_point_aug is not None and not objective_dict_has_all_symbols(problem, reference_point_aug):
        msg = f"The given reference point for the augmentation term {reference_point_aug} does not have a component defined for all the objectives."
        raise ScalarizationError(msg)

    # check the weight vector
    if not objective_dict_has_all_symbols(problem, weights):
        msg = f"The given weight vector {weights} is missing a value for one or more objectives."
        raise ScalarizationError(msg)

    # check the weight vector for the augmentation term
    if weights_aug is not None and not objective_dict_has_all_symbols(problem, weights_aug):
        msg = f"The given weight vector {weights_aug} is missing a value for one or more objectives."
        raise ScalarizationError(msg)

    # get the corrected reference point
    corrected_rp = get_corrected_reference_point(problem, reference_point)
    if reference_point_aug is not None:
        corrected_rp_aug = get_corrected_reference_point(problem, reference_point_aug)

    # check if minimizing or maximizing and adjust ideal and nadir values correspondingly
    ideal_point, nadir_point = get_corrected_ideal_and_nadir(problem)

    # Build the max term
    max_operands = [
        (f"({obj.symbol}_min - {corrected_rp[obj.symbol]}) / ({weights[obj.symbol]})") for obj in problem.objectives
    ]
    max_term = f"{Op.MAX}({', '.join(max_operands)})"

    # Build the augmentation term
    if reference_point_aug is None and weights_aug is None:
        # no reference point in augmentation term
        # same weights for both terms
        aug_expr = " + ".join([f"({obj.symbol}_min / {weights[obj.symbol]})" for obj in problem.objectives])
    elif reference_point_aug is None and weights_aug is not None:
        # different weights provided for augmentation term
        aug_expr = " + ".join([f"({obj.symbol}_min / {weights_aug[obj.symbol]})" for obj in problem.objectives])
    elif reference_point_aug is not None and weights_aug is None:
        # reference point in augmentation term
        aug_expr = " + ".join(
            [f"(({obj.symbol}_min - {corrected_rp_aug[obj.symbol]}) / {weights[obj.symbol]})" for obj in problem.objectives]
        )
    else:
        aug_expr = " + ".join(
            [f"(({obj.symbol}_min - {corrected_rp_aug[obj.symbol]}) / {weights_aug[obj.symbol]})" for obj in problem.objectives]
        )

    # Collect the terms
    sf = f"{max_term} + {rho} * ({aug_expr})"

    # Add the function to the problem
    scalarization_function = ScalarizationFunction(
        name="Generic achievement scalarizing function",
        symbol=symbol,
        func=sf,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=False,
    )
    return problem.add_scalarization(scalarization_function), symbol


def add_nimbus_sf_diff(
    problem: Problem,
    symbol: str,
    classifications: dict[str, tuple[str, float | None]],
    current_objective_vector: dict[str, float],
    delta: float = 0.000001,
    rho: float = 0.000001,
) -> Problem:
    r"""Implements the differentiable variant of the NIMBUS scalarization function.

    \begin{align*}
        \min \quad & \alpha + \rho \sum_{i =1}^k \frac{f_i(\mathbf{x})}{z_i^{nad} - z_i^{\star\star}} \\
        \text{s.t.} \quad & \frac{f_i(\mathbf{x}) - z_i^*}{z_i^{nad} - z_i^{\star\star}} - \alpha \leq 0 \quad & \forall i \in I^< \\
        & \frac{f_i(\mathbf{x}) - \hat{z}_i}{z_i^{nad} - z_i^{\star\star}} - \alpha \leq 0 \quad & \forall i \in I^\leq \\
        & f_i(\mathbf{x}) - f_i(\mathbf{x_c}) \leq 0 \quad & \forall i \in I^< \cup I^\leq \cup I^= \\
        & f_i(\mathbf{x}) - \epsilon_i \leq 0 \quad & \forall i \in I^\geq \\
        & \mathbf{x} \in S,
    \end{align*}

    where $f_i$ are objective functions, $f_i(\mathbf{x_c})$ is a component of
    the current objective function, $\hat{z}_i$ is an aspiration level,
    $\varepsilon_i$ is a reservation level, $z_i^\star$ is a component of the
    ideal point, $z_i^{\star\star} = z_i^\star - \delta$ is a component of the
    utopian point, $z_i^\text{nad}$ is a component of the nadir point, $\rho$ is
    a small scalar, $S$ is the feasible solution space of the problem (i.e., it
    means the other constraints of the problem being solved should be accounted
    for as well), and $\alpha$ is an auxiliary variable.

    The $I$-sets are related to the classifications given to each objective function value
    in respect to  the current objective vector (e.g., by a decision maker). They
    are as follows:

    - $I^{<}$: values that should improve,
    - $I^{\leq}$: values that should improve until a given aspiration level $\hat{z}_i$,
    - $I^{=}$: values that are fine as they are,
    - $I^{\geq}$: values that can be impaired until some reservation level $\varepsilon_i$, and
    - $I^{\diamond}$: values that are allowed to change freely (not present explicitly in this scalarization function).

    The aspiration levels and the reservation levels are supplied for each classification, when relevant, in
    the argument `classifications` as follows:

    ```python
    classifications = {
        "f_1": ("<", None),
        "f_2": ("<=", 42.1),
        "f_3": (">=", 22.2),
        "f_4": ("0", None)
        }
    ```

    Here, we have assumed four objective functions. The key of the dict is a function's symbol, and the tuple
    consists of a pair where the left element is the classification (self explanatory, '0' is for objective values
    that may change freely), the right element is either `None` or an aspiration or a reservation level
    depending on the classification.

    References:
        Miettinen, K., & Mäkelä, M. M. (2002). On scalarizing functions in
            multiobjective optimization. OR Spectrum, 24(2), 193–213.


    Args:
        problem (Problem): the problem to be scalarized.
        symbol (str): the symbol given to the scalarization function, i.e., target of the optimization.
        classifications (dict[str, tuple[str, float  |  None]]): a dict, where the key is a symbol
            of an objective function, and the value is a tuple with a classification and an aspiration
            or a reservation level, or `None`, depending on the classification. See above for an
            explanation.
        current_objective_vector (dict[str, float]): the current objective vector that corresponds to
            a Pareto optimal solution. The classifications are assumed to been given in respect to
            this vector.
        delta (float, optional): a small scalar used to define the utopian point. Defaults to 0.000001.
        rho (float, optional): a small scalar used in the augmentation term. Defaults to 0.000001.

    Returns:
        tuple[Problem, str]: a tuple with a copy of the problem with the added scalarizations and the
            symbol of the scalarization.
    """
    # check that classifications have been provided for all objective functions
    if not objective_dict_has_all_symbols(problem, classifications):
        msg = (
            f"The given classifications {classifications} do not define "
            "a classification for all the objective functions."
        )
        raise ScalarizationError(msg)

    # check that at least one objective function is allowed to be improved and one is
    # allowed to worsen
    if not any(classifications[obj.symbol][0] in ["<", "<="] for obj in problem.objectives) or not any(
        classifications[obj.symbol][0] in [">=", "0"] for obj in problem.objectives
    ):
        msg = (
            f"The given classifications {classifications} should allow at least one objective function value "
            "to improve and one to worsen."
        )
        raise ScalarizationError(msg)

    # check ideal and nadir exist
    ideal_point, nadir_point = get_corrected_ideal_and_nadir(problem)

    # define the auxiliary variable
    alpha = Variable(name="alpha", symbol="_alpha", variable_type=VariableTypeEnum.real, initial_value=1.0, lowerbound=1.0, upperbound=3.0,)

    # define the objective function of the scalarization
    aug_expr = " + ".join(
        [
            f"{obj.symbol}_min / ({nadir_point[obj.symbol]} - {ideal_point[obj.symbol] - delta})"
            for obj in problem.objectives
        ]
    )

    target_expr = f"_alpha + {rho}*" + f"({aug_expr})"
    scalarization = ScalarizationFunction(
        name="NIMBUS scalarization objective function", symbol=symbol, func=target_expr
    )

    constraints = []

    # create all the constraints
    for obj in problem.objectives:
        _symbol = obj.symbol
        match classifications[_symbol]:
            case ("<", _):
                expr = (
                    f"({_symbol}_min - {ideal_point[_symbol]}) / "
                    f"({nadir_point[_symbol] - (ideal_point[_symbol] - delta)}) - _alpha"
                )
                constraints.append(
                    Constraint(
                        name=f"improvement constraint for {_symbol}",
                        symbol=f"{_symbol}_lt",
                        func=expr,
                        cons_type=ConstraintTypeEnum.LTE,
                    )
                )

                # if obj is to be maximized, then the current objective vector value needs to be multiplied by -1
                expr = f"{_symbol}_min - {current_objective_vector[_symbol]}{' * -1' if obj.maximize else ''}"
                constraints.append(
                    Constraint(
                        name=f"stay at least equal constraint for {_symbol}",
                        symbol=f"{_symbol}_eq",
                        func=expr,
                        cons_type=ConstraintTypeEnum.LTE,
                    )
                )
            case ("<=", aspiration):
                # if obj is to be maximized, then the current reservation value needs to be multiplied by -1
                expr = (
                    f"({_symbol}_min - {aspiration}{' * -1' if obj.maximize else ''}) / "
                    f"({nadir_point[_symbol]} - {ideal_point[_symbol] - delta}) - _alpha"
                )
                constraints.append(
                    Constraint(
                        name=f"improvement until constraint for {_symbol}",
                        symbol=f"{_symbol}_lte",
                        func=expr,
                        cons_type=ConstraintTypeEnum.LTE,
                    )
                )

                # if obj is to be maximized, then the current objective vector value needs to be multiplied by -1
                expr = f"{_symbol}_min - {current_objective_vector[_symbol]}{' * -1' if obj.maximize else ''}"
                constraints.append(
                    Constraint(
                        name=f"stay at least equal constraint for {_symbol}",
                        symbol=f"{_symbol}_eq",
                        func=expr,
                        cons_type=ConstraintTypeEnum.LTE,
                    )
                )
            case ("=", _):
                # if obj is to be maximized, then the current objective vector value needs to be multiplied by -1
                expr = f"{_symbol}_min - {current_objective_vector[_symbol]}{' * -1' if obj.maximize else ''}"
                constraints.append(
                    Constraint(
                        name=f"stay at least equal constraint for {_symbol}",
                        symbol=f"{_symbol}_eq",
                        func=expr,
                        cons_type=ConstraintTypeEnum.LTE,
                    )
                )
            case (">=", reservation):
                # if obj is to be maximized, then the reservation value needs to be multiplied by -1
                expr = f"{_symbol}_min - {reservation}{' * -1' if obj.maximize else ''}"
                constraints.append(
                    Constraint(
                        name=f"worsen until constriant for {_symbol}",
                        symbol=f"{_symbol}_gte",
                        func=expr,
                        cons_type=ConstraintTypeEnum.LTE,
                    )
                )
            case ("0", _):
                # not relevant for this scalarization
                pass
            case (c, _):
                msg = (
                    f"Warning! The classification {c} was supplied, but it is not supported."
                    "Must be one of ['<', '<=', '0', '=', '>=']"
                )

    # add the auxiliary variable, scalarization, and constraints
    _problem = problem.add_variables([alpha])
    _problem = _problem.add_scalarization(scalarization)
    return _problem.add_constraints(constraints), symbol


def add_nimbus_sf_nondiff(
    problem: Problem,
    symbol: str,
    classifications: dict[str, tuple[str, float | None]],
    current_objective_vector: dict[str, float],
    delta: float = 0.000001,
    rho: float = 0.000001,
) -> Problem:
    r"""Implements the non-differentiable variant of the NIMBUS scalarization function.

    \begin{align*}
        \underset{\mathbf{x}}{\min}
        \underset{\substack{j \in I^\leq \\i \in I^<}}{\max}
        &\left[ \frac{f_i(\mathbf{x}) - z_i^\star}{z_i^\text{nad} - z_i^{\star\star}},
        \frac{f_j(\mathbf{x}) - \hat{z}_j}{z_j^\text{nad} - x_j^{\star\star}} \right]
        +\rho \sum_{i =1}^k \frac{f_i(\mathbf{x})}{z_i^{nad} - z_i^{\star\star}} \\
        \text{s.t.} \quad & f_i(\mathbf{x}) - f_i(\mathbf{x}^c) \leq 0\quad&\forall i \in I^< \cup I^\leq \cup I^=,\\
        & f_i(\mathbf{x}) - \epsilon_i \leq 0\quad&\forall i \in I^\geq,\\
        & \mathbf{x} \in S,
    \end{align*}

    where $f_i$ are objective functions, $f_i(\mathbf{x_c})$ is a component of
    the current objective function, $\hat{z}_i$ is an aspiration level,
    $\varepsilon_i$ is a reservation level, $z_i^\star$ is a component of the
    ideal point, $z_i^{\star\star} = z_i^\star - \delta$ is a component of the
    utopian point, $z_i^\text{nad}$ is a component of the nadir point, $\rho$ is
    a small scalar, and $S$ is the feasible solution space of the problem (i.e., it
    means the other constraints of the problem being solved should be accounted
    for as well).

    The $I$-sets are related to the classifications given to each objective function value
    in respect to  the current objective vector (e.g., by a decision maker). They
    are as follows:

    - $I^{<}$: values that should improve,
    - $I^{\leq}$: values that should improve until a given aspiration level $\hat{z}_i$,
    - $I^{=}$: values that are fine as they are,
    - $I^{\geq}$: values that can be impaired until some reservation level $\varepsilon_i$, and
    - $I^{\diamond}$: values that are allowed to change freely (not present explicitly in this scalarization function).

    The aspiration levels and the reservation levels are supplied for each classification, when relevant, in
    the argument `classifications` as follows:

    ```python
    classifications = {
        "f_1": ("<", None),
        "f_2": ("<=", 42.1),
        "f_3": (">=", 22.2),
        "f_4": ("0", None)
        }
    ```

    Here, we have assumed four objective functions. The key of the dict is a function's symbol, and the tuple
    consists of a pair where the left element is the classification (self explanatory, '0' is for objective values
    that may change freely), the right element is either `None` or an aspiration or a reservation level
    depending on the classification.

    References:
        Miettinen, K., & Mäkelä, M. M. (2002). On scalarizing functions in
            multiobjective optimization. OR Spectrum, 24(2), 193–213.


    Args:
        problem (Problem): the problem to be scalarized.
        symbol (str): the symbol given to the scalarization function, i.e., target of the optimization.
        classifications (dict[str, tuple[str, float  |  None]]): a dict, where the key is a symbol
            of an objective function, and the value is a tuple with a classification and an aspiration
            or a reservation level, or `None`, depending on the classification. See above for an
            explanation.
        current_objective_vector (dict[str, float]): the current objective vector that corresponds to
            a Pareto optimal solution. The classifications are assumed to been given in respect to
            this vector.
        delta (float, optional): a small scalar used to define the utopian point. Defaults to 0.000001.
        rho (float, optional): a small scalar used in the augmentation term. Defaults to 0.000001.

    Returns:
        tuple[Problem, str]: a tuple with a copy of the problem with the added scalarizations and the
            symbol of the scalarization.
    """
    # check that classifications have been provided for all objective functions
    if not objective_dict_has_all_symbols(problem, classifications):
        msg = (
            f"The given classifications {classifications} do not define "
            "a classification for all the objective functions."
        )
        raise ScalarizationError(msg)

    # check that at least one objective function is allowed to be improved and one is
    # allowed to worsen
    if not any(classifications[obj.symbol][0] in ["<", "<="] for obj in problem.objectives) or not any(
        classifications[obj.symbol][0] in [">=", "0"] for obj in problem.objectives
    ):
        msg = (
            f"The given classifications {classifications} should allow at least one objective function value "
            "to improve and one to worsen."
        )
        raise ScalarizationError(msg)

    # check ideal and nadir exist
    ideal_point, nadir_point = get_corrected_ideal_and_nadir(problem)
    corrected_current_point = get_corrected_reference_point(problem, current_objective_vector)

    # max term and constraints
    max_args = []
    constraints = []

    for obj in problem.objectives:
        _symbol = obj.symbol
        match classifications[_symbol]:
            case ("<", _):
                max_expr = (
                    f"({_symbol}_min - {ideal_point[_symbol]}) / "
                    f"({nadir_point[_symbol]} - {ideal_point[_symbol] - delta})"
                )
                max_args.append(max_expr)

                con_expr = f"{_symbol}_min - {corrected_current_point[_symbol]}"
                constraints.append(
                    Constraint(
                        name=f"improvement constraint for {_symbol}",
                        symbol=f"{_symbol}_lt",
                        func=con_expr,
                        cons_type=ConstraintTypeEnum.LTE,
                    )
                )

            case ("<=", aspiration):
                # if obj is to be maximized, then the current reservation value needs to be multiplied by -1
                max_expr = (
                    f"({_symbol}_min - {aspiration * -1 if obj.maximize else aspiration}) / "
                    f"({nadir_point[_symbol]} - {ideal_point[_symbol] - delta})"
                )
                max_args.append(max_expr)

                con_expr = f"{_symbol}_min - {corrected_current_point[_symbol]}"
                constraints.append(
                    Constraint(
                        name=f"improvement until constraint for {_symbol}",
                        symbol=f"{_symbol}_lte",
                        func=con_expr,
                        cons_type=ConstraintTypeEnum.LTE,
                    )
                )

            case ("=", _):
                con_expr = f"{_symbol}_min - {corrected_current_point[_symbol]}"
                constraints.append(
                    Constraint(
                        name=f"Stay at least as good constraint for {_symbol}",
                        symbol=f"{_symbol}_eq",
                        func=con_expr,
                        cons_type=ConstraintTypeEnum.LTE,
                        linear=False,  # TODO: check!
                    )
                )
            case (">=", reservation):
                con_expr = f"{_symbol}_min - {-1 * reservation if obj.maximize else reservation}"
                constraints.append(
                    Constraint(
                        name=f"Worsen until constriant for {_symbol}",
                        symbol=f"{_symbol}_gte",
                        func=con_expr,
                        cons_type=ConstraintTypeEnum.LTE,
                    )
                )
            case ("0", _):
                # not relevant for this scalarization
                pass
            case (c, _):
                msg = (
                    f"Warning! The classification {c} was supplied, but it is not supported."
                    "Must be one of ['<', '<=', '0', '=', '>=']"
                )

    max_expr = f"Max({','.join(max_args)})"

    # define the objective function of the scalarization
    aug_expr = " + ".join(
        [
            f"{obj.symbol}_min / ({nadir_point[obj.symbol]} - {ideal_point[obj.symbol] - delta})"
            for obj in problem.objectives
        ]
    )

    target_expr = f"{max_expr} + {rho}*({aug_expr})"
    scalarization = ScalarizationFunction(
        name="NIMBUS scalarization objective function",
        symbol=symbol,
        func=target_expr,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=False,
    )

    _problem = problem.add_scalarization(scalarization)
    return _problem.add_constraints(constraints), symbol


def add_stom_sf_diff(
    problem: Problem,
    symbol: str,
    reference_point: dict[str, float],
    rho: float = 1e-6,
    delta: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds the differentiable variant of the STOM scalarizing function.

    \begin{align*}
        \min \quad & \alpha + \rho \sum_{i=1}^k \frac{f_i(\mathbf{x})}{\bar{z}_i - z_i^{\star\star}} \\
        \text{s.t.} \quad & \frac{f_i(\mathbf{x}) - z_i^{\star\star}}{\bar{z}_i
        - z_i^{\star\star}} - \alpha \leq 0 \quad & \forall i = 1,\dots,k\\
        & \mathbf{x} \in S,
    \end{align*}

    where $f_i$ are objective functions, $z_i^{\star\star} = z_i^\star - \delta$ is
    a component of the utopian point, $\bar{z}_i$ is a component of the reference point,
    $\rho$ and $\delta$ are small scalar values, $S$ is the feasible solution
    space of the original problem,  and $\alpha$ is an auxiliary variable.

    References:
        H. Nakayama, Y. Sawaragi, Satisficing trade-off method for
            multiobjective programming, in: M. Grauer, A.P. Wierzbicki (Eds.),
            Interactive Decision Analysis, Springer Verlag, Berlin, 1984, pp.
            113-122.

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_point (dict[str, float]): a dict with keys corresponding to objective
            function symbols and values to reference point components, i.e.,
            aspiration levels.
        rho (float, optional): a small scalar value to scale the sum in the objective
            function of the scalarization. Defaults to 1e-6.
        delta (float, optional): a small scalar value to define the utopian point. Defaults to 1e-6.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """
    # check reference point
    if not objective_dict_has_all_symbols(problem, reference_point):
        msg = f"The give reference point {reference_point} is missing value for one or more objectives."
        raise ScalarizationError(msg)

    ideal_point, _ = get_corrected_ideal_and_nadir(problem)
    corrected_rp = get_corrected_reference_point(problem, reference_point)

    # define the auxiliary variable
    alpha = Variable(name="alpha", symbol="_alpha", variable_type=VariableTypeEnum.real, initial_value=1.0, lowerbound=1.0, upperbound=3.0,)

    # define the objective function of the scalarization
    aug_expr = " + ".join(
        [
            f"{obj.symbol}_min / ({reference_point[obj.symbol]} - {ideal_point[obj.symbol] - delta})"
            for obj in problem.objectives
        ]
    )

    target_expr = f"_alpha + {rho}*" + f"({aug_expr})"
    scalarization = ScalarizationFunction(
        name="STOM scalarization objective function",
        symbol=symbol,
        func=target_expr,
        is_twice_differentiable=problem.is_twice_differentiable,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
    )

    constraints = []

    for obj in problem.objectives:
        expr = (
            f"({obj.symbol}_min - {ideal_point[obj.symbol] - delta}) / "
            f"({corrected_rp[obj.symbol] - (ideal_point[obj.symbol] - delta)}) - _alpha"
        )
        constraints.append(
            Constraint(
                name=f"Max constraint for {obj.symbol}",
                symbol=f"{obj.symbol}_maxcon",
                func=expr,
                cons_type=ConstraintTypeEnum.LTE,
                is_twice_differentiable=obj.is_twice_differentiable,
                is_linear=obj.is_linear,
                is_convex=obj.is_convex,
            )
        )

    _problem = problem.add_variables([alpha])
    _problem = _problem.add_scalarization(scalarization)
    return _problem.add_constraints(constraints), symbol


def add_stom_sf_nondiff(
    problem: Problem,
    symbol: str,
    reference_point: dict[str, float],
    rho: float = 1e-6,
    delta: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds the non-differentiable variant of the STOM scalarizing function.

    \begin{align*}
        \underset{\mathbf{x}}{\min} \quad & \underset{i=1,\dots,k}{\max}\left[
            \frac{f_i(\mathbf{x}) - z_i^{\star\star}}{\bar{z}_i - z_i^{\star\star}}
            \right]
            + \rho \sum_{i=1}^k \frac{f_i(\mathbf{x})}{\bar{z}_i - z_i^{\star\star}} \\
        \text{s.t.}\quad & \mathbf{x} \in S,
    \end{align*}

    where $f_i$ are objective functions, $z_i^{\star\star} = z_i^\star - \delta$ is
    a component of the utopian point, $\bar{z}_i$ is a component of the reference point,
    $\rho$ and $\delta$ are small scalar values, and $S$ is the feasible solution
    space of the original problem.

    References:
        H. Nakayama, Y. Sawaragi, Satisficing trade-off method for
            multiobjective programming, in: M. Grauer, A.P. Wierzbicki (Eds.),
            Interactive Decision Analysis, Springer Verlag, Berlin, 1984, pp.
            113-122.

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_point (dict[str, float]): a dict with keys corresponding to objective
            function symbols and values to reference point components, i.e.,
            aspiration levels.
        rho (float, optional): a small scalar value to scale the sum in the objective
            function of the scalarization. Defaults to 1e-6.
        delta (float, optional): a small scalar value to define the utopian point. Defaults to 1e-6.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """
    # check reference point
    if not objective_dict_has_all_symbols(problem, reference_point):
        msg = f"The give reference point {reference_point} is missing value for one or more objectives."
        raise ScalarizationError(msg)

    ideal_point, _ = get_corrected_ideal_and_nadir(problem)
    corrected_rp = get_corrected_reference_point(problem, reference_point)

    # define the objective function of the scalarization
    max_expr = ", ".join(
        [
            (
                f"({obj.symbol}_min - {ideal_point[obj.symbol] - delta}) / "
                f"({corrected_rp[obj.symbol]} - {ideal_point[obj.symbol] - delta})"
            )
            for obj in problem.objectives
        ]
    )
    aug_expr = " + ".join(
        [
            f"{obj.symbol}_min / ({reference_point[obj.symbol]} - {ideal_point[obj.symbol] - delta})"
            for obj in problem.objectives
        ]
    )

    target_expr = f"{Op.MAX}({max_expr}) + {rho}*" + f"({aug_expr})"
    scalarization = ScalarizationFunction(
        name="STOM scalarization objective function",
        symbol=symbol,
        func=target_expr,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=False,
    )

    return problem.add_scalarization(scalarization), symbol


def add_guess_sf_diff(
    problem: Problem,
    symbol: str,
    reference_point: dict[str, float],
    rho: float = 1e-6,
    delta: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds the differentiable variant of the GUESS scalarizing function.

    \begin{align*}
        \min \quad & \alpha + \rho \sum_{i=1}^k \frac{f_i(\mathbf{x})}{d_i} \\
        \text{s.t.} \quad & \frac{f_i(\mathbf{x}) - z_i^{\star\star}}{\bar{z}_i
        - z_i^{\star\star}} - \alpha \leq 0 \quad & \forall i \notin I^{\diamond},\\
        & d_i =
        \begin{cases}
        z^\text{nad}_i - \bar{z}_i,\quad \forall i \notin I^\diamond,\\
        z^\text{nad}_i - z^{\star\star}_i,\quad \forall i \in I^\diamond,\\
        \end{cases}\\
        & \mathbf{x} \in S,
    \end{align*}

    where $f_i$ are objective functions, $z_i^{\star\star} = z_i^\star - \delta$ is
    a component of the utopian point, $\bar{z}_i$ is a component of the reference point,
    $\rho$ and $\delta$ are small scalar values, $S$ is the feasible solution
    space of the original problem, and $\alpha$ is an auxiliary variable. The index
    set $I^\diamond$ represents objective vectors whose values are free to change. The indices
    belonging to this set are interpreted as those objective vectors whose components in
    the reference point is set to be the the respective nadir point component of the problem.

    References:
        Buchanan, J. T. (1997). A naive approach for solving MCDM problems: The
        GUESS method. Journal of the Operational Research Society, 48, 202-206.

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_point (dict[str, float]): a dict with keys corresponding to objective
            function symbols and values to reference point components, i.e.,
            aspiration levels.
        rho (float, optional): a small scalar value to scale the sum in the objective
            function of the scalarization. Defaults to 1e-6.
        delta (float, optional): a small scalar to define the utopian point. Defaults to 1e-6.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """
    # check reference point
    if not objective_dict_has_all_symbols(problem, reference_point):
        msg = f"The give reference point {reference_point} is missing value for one or more objectives."
        raise ScalarizationError(msg)

    ideal_point, nadir_point = get_corrected_ideal_and_nadir(problem)
    corrected_rp = get_corrected_reference_point(problem, reference_point)

    # the indices that are free to change, set if component of reference point
    # has the corresponding nadir value, or if it is greater than the nadir value
    free_to_change = [
        sym
        for sym in corrected_rp
        if np.isclose(corrected_rp[sym], nadir_point[sym]) or corrected_rp[sym] > nadir_point[sym]
    ]

    # define the auxiliary variable
    alpha = Variable(name="alpha", symbol="_alpha", variable_type=VariableTypeEnum.real, initial_value=1.0, lowerbound=1.0, upperbound=3.0,)

    # define the objective function of the scalarization
    aug_expr = " + ".join(
        [
            (
                f"{obj.symbol}_min / ({nadir_point[obj.symbol]} - "
                f"{reference_point[obj.symbol] if obj.symbol not in free_to_change else ideal_point[obj.symbol] - delta})"
            )
            for obj in problem.objectives
        ]
    )

    target_expr = f"_alpha + {rho}*" + f"({aug_expr})"
    scalarization = ScalarizationFunction(
        name="GUESS scalarization objective function",
        symbol=symbol,
        func=target_expr,
        is_convex=problem.is_convex,
        is_linear=problem.is_linear,
        is_twice_differentiable=problem.is_twice_differentiable,
    )

    constraints = []

    for obj in problem.objectives:
        if obj.symbol in free_to_change:
            # if free to change, then do not add a constraint
            continue

        # not free to change, add constraint
        expr = (
            f"({obj.symbol}_min - {nadir_point[obj.symbol]}) / "
            f"({nadir_point[obj.symbol]} - {corrected_rp[obj.symbol]}) - _alpha"
        )

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


def add_guess_sf_nondiff(
    problem: Problem,
    symbol: str,
    reference_point: dict[str, float],
    rho: float = 1e-6,
    delta: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds the non-differentiable variant of the GUESS scalarizing function.

    \begin{align*}
        \underset{\mathbf{x}}{\min}\quad & \underset{i \notin I^\diamond}{\max}
        \left[
        \frac{f_i(\mathbf{x}) - z_i^{\star\star}}{\bar{z}_i - z_i^{\star\star}}
        \right]
        + \rho \sum_{j=1}^k \frac{f_j(\mathbf{x})}{d_j},
        \quad & \\
        \text{s.t.}\quad
        & d_j =
        \begin{cases}
        z^\text{nad}_j - \bar{z}_j,\quad \forall j \notin I^\diamond,\\
        z^\text{nad}_j - z^{\star\star}_j,\quad \forall j \in I^\diamond,\\
        \end{cases}\\
        & \mathbf{x} \in S,
    \end{align*}

    where $f_{i/j}$ are objective functions, $z_{i/j}^{\star\star} =
    z_{i/j}^\star - \delta$ is a component of the utopian point, $\bar{z}_{i/j}$
    is a component of the reference point, $\rho$ and $\delta$ are small scalar
    values, and $S$ is the feasible solution space of the original problem. The
    index set $I^\diamond$ represents objective vectors whose values are free to
    change. The indices belonging to this set are interpreted as those objective
    vectors whose components in the reference point is set to be the the
    respective nadir point component of the problem.

    References:
        Buchanan, J. T. (1997). A naive approach for solving MCDM problems: The
        GUESS method. Journal of the Operational Research Society, 48, 202-206.

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_point (dict[str, float]): a dict with keys corresponding to objective
            function symbols and values to reference point components, i.e.,
            aspiration levels.
        rho (float, optional): a small scalar value to scale the sum in the objective
            function of the scalarization. Defaults to 1e-6.
        delta (float, optional): a small scalar to define the utopian point. Defaults to 1e-6.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """
    # check reference point
    if not objective_dict_has_all_symbols(problem, reference_point):
        msg = f"The give reference point {reference_point} is missing value for one or more objectives."
        raise ScalarizationError(msg)

    ideal_point, nadir_point = get_corrected_ideal_and_nadir(problem)
    corrected_rp = get_corrected_reference_point(problem, reference_point)

    # the indices that are free to change, set if component of reference point
    # has the corresponding nadir value, or if it is greater than the nadir value
    free_to_change = [
        sym
        for sym in corrected_rp
        if np.isclose(corrected_rp[sym], nadir_point[sym]) or corrected_rp[sym] > nadir_point[sym]
    ]

    # define the max expression of the scalarization
    # if the objective symbol belongs to the class I^diamond, then do not add it
    # to the max expression
    max_expr = ", ".join(
        [
            (
                f"({obj.symbol}_min - {(ideal_point[obj.symbol] - delta)}) / "
                f"({reference_point[obj.symbol]} - {(ideal_point[obj.symbol] - delta)})"
            )
            for obj in problem.objectives
            if obj.symbol not in free_to_change
        ]
    )

    # define the augmentation term
    aug_expr = " + ".join(
        [
            (
                f"{obj.symbol}_min / ({nadir_point[obj.symbol]} - "
                f"{reference_point[obj.symbol] if obj.symbol not in free_to_change else ideal_point[obj.symbol] - delta})"
            )
            for obj in problem.objectives
        ]
    )

    target_expr = f"{Op.MAX}({max_expr}) + {rho}*({aug_expr})"
    scalarization = ScalarizationFunction(
        name="GUESS scalarization objective function",
        symbol=symbol,
        func=target_expr,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=False,
    )

    return problem.add_scalarization(scalarization), symbol


def add_asf_diff(
    problem: Problem,
    symbol: str,
    reference_point: dict[str, float],
    rho: float = 1e-6,
    delta: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds the differentiable variant of the achievement scalarizing function.

    \begin{align*}
        \min \quad & \alpha + \rho \sum_{i=1}^k \frac{f_i(\mathbf{x})}{z_i^\text{nad} - z_i^{\star\star}} \\
        \text{s.t.} \quad & \frac{f_i(\mathbf{x}) - \bar{z}_i}{z_i^\text{nad}
        - z_i^{\star\star}} - \alpha \leq 0,\\
        & \mathbf{x} \in S,
    \end{align*}

    where $f_i$ are objective functions, $z_i^{\star\star} = z_i^\star - \delta$ is
    a component of the utopian point, $\bar{z}_i$ is a component of the reference point,
    $\rho$ and $\delta$ are small scalar values, $S$ is the feasible solution
    space of the original problem, and $\alpha$ is an auxiliary variable.

    References:
        Wierzbicki, A. P. (1982). A mathematical basis for satisficing decision
            making. Mathematical modelling, 3(5), 391-405.

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_point (dict[str, float]): a dict with keys corresponding to objective
            function symbols and values to reference point components, i.e.,
            aspiration levels.
        rho (float, optional): a small scalar value to scale the sum in the objective
            function of the scalarization. Defaults to 1e-6.
        delta (float, optional): a small scalar to define the utopian point. Defaults to 1e-6.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.

    Todo:
        Add reference in augmentation term option!
    """
    # check reference point
    if not objective_dict_has_all_symbols(problem, reference_point):
        msg = f"The give reference point {reference_point} is missing value for one or more objectives."
        raise ScalarizationError(msg)

    ideal_point, nadir_point = get_corrected_ideal_and_nadir(problem)
    corrected_rp = get_corrected_reference_point(problem, reference_point)

    # define the auxiliary variable
    alpha = Variable(name="alpha", symbol="_alpha", variable_type=VariableTypeEnum.real, initial_value=1.0, lowerbound=1.0, upperbound=3.0,)

    # define the objective function of the scalarization
    aug_expr = " + ".join(
        [
            (f"{obj.symbol}_min / ({nadir_point[obj.symbol]} - {ideal_point[obj.symbol] - delta})")
            for obj in problem.objectives
        ]
    )

    target_expr = f"_alpha + {rho}*" + f"({aug_expr})"
    scalarization = ScalarizationFunction(name="ASF scalarization objective function", symbol=symbol, func=target_expr)

    constraints = []

    for obj in problem.objectives:
        expr = (
            f"({obj.symbol}_min - {corrected_rp[obj.symbol]}) / "
            f"({nadir_point[obj.symbol]} - {ideal_point[obj.symbol] - delta}) - _alpha"
        )

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


def add_weighted_sums(problem: Problem, symbol: str, weights: dict[str, float]) -> tuple[Problem, str]:
    r"""Add the weighted sums scalarization to a problem with the given weights.

    It is assumed that the weights add to 1.

    The scalarization is defined as follows:

    \begin{equation}
        \begin{aligned}
        & \mathcal{S}_\text{WS}(F(\mathbf{x});\mathbf{w}) = \sum_{i=1}^{k} w_i f_i(\mathbf{x}) \\
        & \text{s.t.} \sum_{i=1}^{k} w_i = 1,
        \end{aligned}
    \end{equation}

    where $\mathbf{w} = [w_1,\dots,w_k]$ are the weights and $k$ is the number of
    objective functions.

    Warning:
        The weighted sums scalarization is often not capable of finding most Pareto optimal
            solutions when optimized. It is advised to utilize some better scalarization
            functions.

    Args:
        problem (Problem): the problem to which the scalarization should be added.
        symbol (str): the symbol to reference the added scalarization function.
        weights (dict[str, float]): the weights. For the method to work, the weights
            should sum to 1. However, this is not a condition that is checked.

    Raises:
        ScalarizationError: if the weights are missing any of the objective components.

    Returns:
        tuple[Problem, str]: A tuple containing a copy of the problem with the scalarization function added,
            and the symbol of the added scalarization function.
    """
    # check that the weights have all the objective components
    if not all(obj.symbol in weights for obj in problem.objectives):
        msg = f"The given weight vector {weights} does not have a component defined for all the objectives."
        raise ScalarizationError(msg)

    # Build the sum
    sum_terms = [f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives]

    # aggregate the terms
    sf = " + ".join(sum_terms)

    # Add the function to the problem
    scalarization_function = ScalarizationFunction(
        name="Weighted sums scalarization function",
        symbol=symbol,
        func=sf,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=problem.is_twice_differentiable,
    )
    return problem.add_scalarization(scalarization_function), symbol


def add_objective_as_scalarization(problem: Problem, symbol: str, objective_symbol: str) -> tuple[Problem, str]:
    r"""Creates a scalarization where one of the problem's objective functions is optimized.

    The scalarization is defined as follows:

    \begin{equation}
        \operatorname{min}_{\mathbf{x} \in S} f_t(\mathbf{x}),
    \end{equation}

    where $f_t(\mathbf{x})$ is the objective function to be minimized.

    Args:
        problem (Problem): the problem to which the scalarization should be added.
        symbol (str): the symbol to reference the added scalarization function.
        objective_symbol (str): the symbol of the objective function to be optimized.

    Raises:
        ScalarizationError: the given objective_symbol does not exist in the problem.

    Returns:
        tuple[Problem, str]: A tuple containing a copy of the problem with the scalarization function added,
            and the symbol of the added scalarization function.
    """
    # check that symbol exists
    if objective_symbol not in (correct_symbols := [objective.symbol for objective in problem.objectives]):
        msg = f"The given objective symbol {objective_symbol} should be one of {correct_symbols}."
        raise ScalarizationError(msg)

    sf = ["Multiply", 1, f"{objective_symbol}_min"]

    # Add the function to the problem
    scalarization_function = ScalarizationFunction(
        name=f"Objective {objective_symbol}",
        symbol=symbol,
        func=sf,
    )
    return problem.add_scalarization(scalarization_function), symbol


def add_epsilon_constraints(
    problem: Problem, symbol: str, constraint_symbols: dict[str, str], objective_symbol: str, epsilons: dict[str, float]
) -> tuple[Problem, str, list[str]]:
    r"""Creates expressions for an epsilon constraints scalarization and constraints.

    It is assumed that epsilon have been given in a format where each objective is to be minimized.

    The scalarization is defined as follows:

    \begin{equation}
    \begin{aligned}
    & \operatorname{min}_{\mathbf{x} \in S}
    & & f_t(\mathbf{x}) \\
    & \text{s.t.}
    & & f_j(\mathbf{x}) \leq \epsilon_j \text{ for all } j = 1, \ldots ,k, \; j \neq t,
    \end{aligned}
    \end{equation}

    where $\epsilon_j$ are the epsilon bounds used in the epsilon constraints $f_j(\mathbf{x}) \leq \epsilon_j$,
    and $k$ is the number of objective functions.

    Args:
        problem (Problem): the problem to scalarize.
        symbol (str): the symbol of the added objective function to be optimized.
        constraint_symbols (dict[str, str]): a dict with the symbols to be used with the added
            constraints. The key indicates the name of the objective function the constraint
            is related to, and the value is the symbol to be used when defining the constraint.
        objective_symbol (str): the objective used as the objective in the epsilon constraint scalarization.
        epsilons (dict[str, float]): the epsilon constraint values in a dict
            with each key being an objective's symbol. The corresponding value
            is then used as the epsilon value for the respective objective function.

    Raises:
        ScalarizationError: `objective_symbol` not found in problem definition.

    Returns:
        tuple[Problem, str, list[str]]: A triple with the first element being a copy of the
            problem with the added epsilon constraints. The second element is the symbol of
            the objective to be optimized. The last element is a list with the symbols
            of the added constraints to the problem.
    """
    if objective_symbol not in (correct_symbols := [objective.symbol for objective in problem.objectives]):
        msg = f"The given objective symbol {objective_symbol} should be one of {correct_symbols}."
        raise ScalarizationError(msg)

    _problem, _ = add_objective_as_scalarization(problem, symbol, objective_symbol)

    # the epsilons must be given such that each objective function is to be minimized
    # TODO: check if objective function is linear
    constraints = [
        Constraint(
            name=f"Epsilon for {obj.symbol}",
            symbol=constraint_symbols[obj.symbol],
            func=["Add", f"{obj.symbol}_min", ["Negate", epsilons[obj.symbol]]],
            cons_type=ConstraintTypeEnum.LTE,
            is_linear=obj.is_linear,
            is_convex=obj.is_convex,
            is_twice_differentiable=obj.is_twice_differentiable,
        )
        for obj in problem.objectives
        if obj.symbol != objective_symbol
    ]

    _problem = _problem.add_constraints(constraints)

    return _problem, symbol, [con.symbol for con in constraints]


def create_epsilon_constraints_json(
    problem: Problem, objective_symbol: str, epsilons: dict[str, float]
) -> tuple[list[str | int | float], list[str]]:
    """Creates JSON expressions for an epsilon constraints scalarization and constraints.

    It is assumed that epsilon have been given in a format where each objective is to be minimized.

    Warning:
        To be deprecated.

    Args:
        problem (Problem): the problem to scalarize.
        objective_symbol (str): the objective used as the objective in the epsilon constraint scalarization.
        epsilons (dict[str, float]): the epsilon constraint values in a dict
            with each key being an objective's symbol.

    Raises:
        ScalarizationError: `objective_symbol` not found in problem definition.

    Returns:
        tuple[list, list]: the first element is the expression of the scalarized objective expressed in MathJSON format.
            The second element is a list of expressions of the constraints expressed in MathJSON format.
            The constraints are in less than or equal format.
    """
    correct_symbols = [objective.symbol for objective in problem.objectives]
    if objective_symbol not in correct_symbols:
        msg = f"The given objective symbol {objective_symbol} should be one of {correct_symbols}."
        raise ScalarizationError(msg)
    correct_symbols.remove(objective_symbol)

    scalarization_expr = ["Multiply", 1, f"{objective_symbol}_min"]

    # the epsilons must be given such that each objective function is to be minimized
    constraint_exprs = [["Add", f"{obj}_min", ["Negate", epsilons[obj]]] for obj in correct_symbols]

    return scalarization_expr, constraint_exprs


def add_scalarization_function(
    problem: Problem,
    func: str,
    symbol: str,
    name: str | None = None,
) -> tuple[Problem, str]:
    """Adds a scalarization function to a Problem.

    Returns a new instance of the Problem with the new scalarization function
    and the symbol of the scalarization function added.

    Args:
        problem (Problem): the problem to which the scalarization function should be added.
        func (str): the scalarization function to be added as a string in infix notation.
        symbol (str): the symbol reference the added scalarization function.
            This is important when the added scalarization function should be
            utilized when optimizing a problem.
        name (str, optional): the name to be given to the scalarization
            function. If None, the symbol is used as the name. Defaults to None.

    Returns:
        tuple[Problem, str]: A tuple with the new Problem with the added
            scalarization function and the function's symbol.
    """
    scalarization_function = ScalarizationFunction(
        name=symbol if name is None else name,
        symbol=symbol,
        func=func,
    )
    return problem.add_scalarization(scalarization_function), symbol


def add_lte_constraints(
    problem: Problem, funcs: list[str], symbols: list[str], names: list[str | None] | None = None
) -> Problem:
    """Adds constraints to a problem that are defined in the less than or equal format.

    Is is assumed that the constraints expression at position funcs[i] is symbolized by the
    symbol at position symbols[i] for all i.

    Does not modify problem, but makes a copy of it instead and returns it.

    Args:
        problem (Problem): the problem to which the constraints are added.
        funcs (list[str]): the expressions of the constraints.
        symbols (list[str]): the symbols of the constraints. In order.
        names (list[str  |  None] | None, optional): The names of the
            constraints. For any name with 'None' the symbol is used as the name. If
            names is None, then the symbol is used as the name for all the
            constraints. Defaults to None.

    Raises:
        ScalarizationError: if the lengths of the arguments do not match.

    Returns:
        Problem: a copy of the original problem with the constraints added.
    """
    if (len_f := len(funcs)) != (len_s := len(symbols)) and names is not None and (len_n := len(names)) != len(funcs):
        msg = (
            f"The lengths of ({len_f=}) and 'symbols' ({len_s=}) must match. "
            f"If 'names' is not None, then its length ({len_n=}) must also match."
        )
        raise ScalarizationError(msg)

    if names is None:
        names = symbols

    return problem.model_copy(
        update={
            "constraints": [
                *(problem.constraints if problem.constraints is not None else []),
                *[
                    Constraint(
                        name=(name if (name := names[i]) is not None else symbols[i]),
                        symbol=symbols[i],
                        cons_type=ConstraintTypeEnum.LTE,
                        func=funcs[i],
                    )
                    for i in range(len(funcs))
                ],
            ]
        }
    )
