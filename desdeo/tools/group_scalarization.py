"""Group scalarization functions split from scalarization.py.

This module contains all functions with 'group' in their name, previously located in scalarization.py.
"""

# Imports will be copied from scalarization.py as needed
from typing import Literal

import numpy as np

from desdeo.problem import (
    Constraint,
    ConstraintTypeEnum,
    Problem,
    ScalarizationFunction,
    Variable,
    VariableTypeEnum,
)
from desdeo.tools.scalarization import Op, ScalarizationError, objective_dict_has_all_symbols
from desdeo.tools.utils import (
    flip_maximized_objective_values,
    get_corrected_ideal,
    get_corrected_nadir,
)

# Functions will be inserted here in the next step


def add_group_asf(
    problem: Problem,
    symbol: str,
    reference_points: list[dict[str, float]],
    agg_bounds: dict[str, float] | None = None,
    delta: dict[str, float] | float = 1e-6,
    ideal: dict[str, float] | None = None,
    nadir: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Add the achievement scalarizing function for multiple decision makers.

    The scalarization function is defined as follows:

    \begin{align}
        &\mbox{minimize} &&\max_{i,d} [w_{id}(f_{id}(\mathbf{x})-\overline{z}_{id})] +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x}) \\
        &\mbox{subject to} &&\mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{z^{nad}_{id} - z^{uto}_{id}}$.

    Args:
        problem (Problem): the problem to which the scalarization function should be added.
        symbol (str): the symbol to reference the added scalarization function.
        reference_points (list[dict[str, float]]): a list of reference points as objective dicts.
        agg_bounds dict[str, float]: a dictionary of bounds not to violate.
        ideal (dict[str, float], optional): ideal point values. If not given, attempt will be made
            to calculate ideal point from problem.
        nadir (dict[str, float], optional): nadir point values. If not given, attempt will be made
            to calculate nadir point from problem.
        delta (float, optional): a small scalar used to define the utopian point. Defaults to 1e-6.
        rho (float, optional): the weight factor used in the augmentation term. Defaults to 1e-6.

    Raises:
        ScalarizationError: there are missing elements in any reference point.

    Returns:
        tuple[Problem, str]: A tuple containing a copy of the problem with the scalarization function added,
            and the symbol of the added scalarization function.
    """
    # check reference points
    for reference_point in reference_points:
        if not objective_dict_has_all_symbols(problem, reference_point):
            msg = f"The give reference point {reference_point} is missing a value for one or more objectives."
            raise ScalarizationError(msg)

    # check if ideal point is specified
    # if not specified, try to calculate corrected ideal point
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined!"
        raise ScalarizationError(msg)

    # check if nadir point is specified
    # if not specified, try to calculate corrected nadir point
    if nadir is not None:
        nadir_point = nadir
    elif problem.get_nadir_point() is not None:
        nadir_point = get_corrected_nadir(problem)
    else:
        msg = "Nadir point not defined!"
        raise ScalarizationError(msg)

    # calculate the weights
    weights = None
    if type(delta) is dict:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta[obj.symbol]))
            for obj in problem.objectives
        }
    else:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta)) for obj in problem.objectives
        }

    # form the max and augmentation terms
    max_terms = []
    aug_exprs = []
    for i in range(len(reference_points)):
        corrected_rp = flip_maximized_objective_values(problem, reference_points[i])
        for obj in problem.objectives:
            max_terms.append(f"({weights[obj.symbol]}) * ({obj.symbol}_min - {corrected_rp[obj.symbol]})")

        aug_expr = " + ".join([f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
        aug_exprs.append(aug_expr)
    max_terms = ", ".join(max_terms)
    aug_exprs = " + ".join(aug_exprs)

    func = f"{Op.MAX}({max_terms}) + {rho} * ({aug_exprs})"

    scalarization_function = ScalarizationFunction(
        name="Achievement scalarizing function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_convex=problem.is_convex,
        is_linear=problem.is_linear,
        is_twice_differentiable=False,
    )
    problem = problem.add_scalarization(scalarization_function)
    #  get corrected bounds if exist
    if agg_bounds is not None:
        bounds = flip_maximized_objective_values(problem, agg_bounds)
        constraints = []
        for obj in problem.objectives:
            expr = f"({obj.symbol}_min - {bounds[obj.symbol]})"
            constraints.append(
                Constraint(
                    name=f"Constraint bound for {obj.symbol}",
                    symbol=f"{obj.symbol}_con",
                    func=expr,
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=obj.is_linear,
                    is_convex=obj.is_convex,
                    is_twice_differentiable=obj.is_twice_differentiable,
                )
            )
        problem = problem.add_constraints(constraints)

    return problem, symbol


def add_group_asf_agg(
    problem: Problem,
    symbol: str,
    agg_aspirations: dict[str, float],
    agg_bounds: dict[str, float],
    delta: dict[str, float] | float = 1e-6,
    ideal: dict[str, float] | None = None,
    nadir: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Add the achievement scalarizing function for multiple decision makers.

    Both aggregated aspiration levels (min aspirations) and agg bounds (max bounds) are required.

    The scalarization function is defined as follows:

    \begin{align}
        &\mbox{minimize} &&\max_{i,d} [w_{id}(f_{id}(\mathbf{x})-\overline{z}_{id})] +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x}) \\
        &\mbox{subject to} &&\mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{z^{nad}_{id} - z^{uto}_{id}}$.

    Args:
        problem (Problem): the problem to which the scalarization function should be added.
        symbol (str): the symbol to reference the added scalarization function.
        reference_points (list[dict[str, float]]): a list of reference points as objective dicts.
        ideal (dict[str, float], optional): ideal point values. If not given, attempt will be made
            to calculate ideal point from problem.
        nadir (dict[str, float], optional): nadir point values. If not given, attempt will be made
            to calculate nadir point from problem.
        delta (float, optional): a small scalar used to define the utopian point. Defaults to 1e-6.
        rho (float, optional): the weight factor used in the augmentation term. Defaults to 1e-6.

    Raises:
        ScalarizationError: there are missing elements in any reference point.

    Returns:
        tuple[Problem, str]: A tuple containing a copy of the problem with the scalarization function added,
            and the symbol of the added scalarization function.
    """
    # check if ideal point is specified
    # if not specified, try to calculate corrected ideal point
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined!"
        raise ScalarizationError(msg)

    # check if nadir point is specified
    # if not specified, try to calculate corrected nadir point
    if nadir is not None:
        nadir_point = nadir
    elif problem.get_nadir_point() is not None:
        nadir_point = get_corrected_nadir(problem)
    else:
        msg = "Nadir point not defined!"
        raise ScalarizationError(msg)

    # Correct the aspirations and hard_constraints
    agg_aspirations = flip_maximized_objective_values(problem, agg_aspirations)
    agg_bounds = flip_maximized_objective_values(problem, agg_bounds)  # calculate the weights

    weights = None
    if type(delta) is dict:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta[obj.symbol]))
            for obj in problem.objectives
        }
    else:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta)) for obj in problem.objectives
        }

    # form the max and augmentation terms
    max_terms = []
    aug_exprs = []
    for obj in problem.objectives:
        max_terms.append(f"({weights[obj.symbol]}) * ({obj.symbol}_min - {agg_aspirations[obj.symbol]})")

    aug_expr = " + ".join([f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
    aug_exprs.append(aug_expr)
    max_terms = ", ".join(max_terms)
    aug_exprs = " + ".join(aug_exprs)

    func = f"{Op.MAX}({max_terms}) + {rho} * ({aug_exprs})"

    scalarization_function = ScalarizationFunction(
        name="Achievement scalarizing function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_convex=problem.is_convex,
        is_linear=problem.is_linear,
        is_twice_differentiable=False,
    )

    constraints = []

    for obj in problem.objectives:
        expr = f"({obj.symbol}_min - {agg_bounds[obj.symbol]})"
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

    problem = problem.add_constraints(constraints)
    problem = problem.add_scalarization(scalarization_function)

    return problem, symbol


def add_group_asf_diff(
    problem: Problem,
    symbol: str,
    reference_points: list[dict[str, float]],
    agg_bounds: dict[str, float] | None = None,
    delta: dict[str, float] | float = 1e6,
    ideal: dict[str, float] | None = None,
    nadir: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Add the differentiable variant of the achievement scalarizing function for multiple decision makers.

    The scalarization function is defined as follows:

    \begin{align}
        &\mbox{minimize} &&\alpha +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x}) \\
        &\mbox{subject to} && w_{id}(f_{id}(\mathbf{x})-\overline{z}_{id}) - \alpha \leq 0,\\
        &&&\mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{z^{nad}_{id} - z^{uto}_{id}}$.

    Args:
        problem (Problem): the problem to which the scalarization function should be added.
        symbol (str): the symbol to reference the added scalarization function.
        reference_points (list[dict[str, float]]): a list of reference points as objective dicts.
        agg_bounds dict[str, float]: a dictionary of bounds not to violate.
        ideal (dict[str, float], optional): ideal point values. If not given, attempt will be made
            to calculate ideal point from problem.
        nadir (dict[str, float], optional): nadir point values. If not given, attempt will be made
            to calculate nadir point from problem.
        delta (float, optional): a small scalar used to define the utopian point. Defaults to 1e-6.
        rho (float, optional): the weight factor used in the augmentation term. Defaults to 1e-6.

    Raises:
        ScalarizationError: there are missing elements in any reference point.

    Returns:
        tuple[Problem, str]: A tuple containing a copy of the problem with the scalarization function added,
            and the symbol of the added scalarization function.
    """
    # check reference points
    for reference_point in reference_points:
        if not objective_dict_has_all_symbols(problem, reference_point):
            msg = f"The give reference point {reference_point} is missing a value for one or more objectives."
            raise ScalarizationError(msg)

    # check if ideal point is specified
    # if not specified, try to calculate corrected ideal point
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined!"
        raise ScalarizationError(msg)

    # check if nadir point is specified
    # if not specified, try to calculate corrected nadir point
    if nadir is not None:
        nadir_point = nadir
    elif problem.get_nadir_point() is not None:
        nadir_point = get_corrected_nadir(problem)
    else:
        msg = "Nadir point not defined!"
        raise ScalarizationError(msg)

    # define the auxiliary variable
    alpha = Variable(
        name="alpha",
        symbol="_alpha",
        variable_type=VariableTypeEnum.real,
        lowerbound=-float("Inf"),
        upperbound=float("Inf"),
        initial_value=1.0,
    )

    # calculate the weights
    weights = None
    if type(delta) is dict:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta[obj.symbol]))
            for obj in problem.objectives
        }
    else:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta)) for obj in problem.objectives
        }

    # form the constaint and augmentation expressions
    # constraint expressions are formed into a list of lists
    con_terms = []
    aug_exprs = []
    for i in range(len(reference_points)):
        corrected_rp = flip_maximized_objective_values(problem, reference_points[i])
        rp = {}
        for obj in problem.objectives:
            rp[obj.symbol] = f"(({weights[obj.symbol]}) * ({obj.symbol}_min - {corrected_rp[obj.symbol]})) - _alpha"
        con_terms.append(rp)
        aug_expr = " + ".join([f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
        aug_exprs.append(aug_expr)
    aug_exprs = " + ".join(aug_exprs)

    func = f"_alpha + {rho} * ({aug_exprs})"

    scalarization_function = ScalarizationFunction(
        name="Differentiable achievement scalarizing function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_convex=problem.is_convex,
        is_linear=problem.is_linear,
        is_twice_differentiable=problem.is_twice_differentiable,
    )

    constraints = []
    # loop to create a constraint for every objective of every reference point given
    for i in range(len(reference_points)):
        for obj in problem.objectives:
            # since we are subtracting a constant value, the linearity, convexity,
            # and differentiability of the objective function, and hence the
            # constraint, should not change.
            constraints.append(
                Constraint(
                    name=f"Constraint for {obj.symbol}",
                    symbol=f"{obj.symbol}_con_{i + 1}",
                    func=con_terms[i][obj.symbol],
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=obj.is_linear,
                    is_convex=obj.is_convex,
                    is_twice_differentiable=obj.is_twice_differentiable,
                )
            )

    #  get corrected bounds if exist
    if agg_bounds is not None:
        bounds = flip_maximized_objective_values(problem, agg_bounds)
        for obj in problem.objectives:
            expr = f"({obj.symbol}_min - {bounds[obj.symbol]} - _alpha)"
            constraints.append(
                Constraint(
                    name=f"Constraint bound for {obj.symbol}",
                    symbol=f"{obj.symbol}_con",
                    func=expr,
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=obj.is_linear,
                    is_convex=obj.is_convex,
                    is_twice_differentiable=obj.is_twice_differentiable,
                )
            )
    _problem = problem.add_variables([alpha])
    _problem = _problem.add_scalarization(scalarization_function)
    return _problem.add_constraints(constraints), symbol


def add_group_asf_agg_diff(
    problem: Problem,
    symbol: str,
    agg_aspirations: dict[str, float],
    agg_bounds: dict[str, float] | None = None,
    delta: dict[str, float] | float = 1e6,
    ideal: dict[str, float] | None = None,
    nadir: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Add the differentiable variant of the achievement scalarizing function for multiple decision makers.

    Both aggregated aspiration levels (min aspirations) and agg bounds (max bounds) are required.
    The scalarization function is defined as follows:

    \begin{align}
        &\mbox{minimize} &&\alpha +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x}) \\
        &\mbox{subject to} && w_{id}(f_{id}(\mathbf{x})-\overline{z}_{id}) - \alpha \leq 0,\\
        &&&\mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{z^{nad}_{id} - z^{uto}_{id}}$.

    Args:
        problem (Problem): the problem to which the scalarization function should be added.
        symbol (str): the symbol to reference the added scalarization function.
        reference_points (list[dict[str, float]]): a list of reference points as objective dicts.
        agg_bounds dict[str, float]: a dictionary of bounds not to violate.
        ideal (dict[str, float], optional): ideal point values. If not given, attempt will be made
            to calculate ideal point from problem.
        nadir (dict[str, float], optional): nadir point values. If not given, attempt will be made
            to calculate nadir point from problem.
        delta (float, optional): a small scalar used to define the utopian point. Defaults to 1e-6.
        rho (float, optional): the weight factor used in the augmentation term. Defaults to 1e-6.

    Raises:
        ScalarizationError: there are missing elements in any reference point.

    Returns:
        tuple[Problem, str]: A tuple containing a copy of the problem with the scalarization function added,
            and the symbol of the added scalarization function.
    """
    # check if ideal point is specified
    # if not specified, try to calculate corrected ideal point
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined!"
        raise ScalarizationError(msg)

    # check if nadir point is specified
    # if not specified, try to calculate corrected nadir point
    if nadir is not None:
        nadir_point = nadir
    elif problem.get_nadir_point() is not None:
        nadir_point = get_corrected_nadir(problem)
    else:
        msg = "Nadir point not defined!"
        raise ScalarizationError(msg)

    # define the auxiliary variable
    alpha = Variable(
        name="alpha",
        symbol="_alpha",
        variable_type=VariableTypeEnum.real,
        lowerbound=-float("Inf"),
        upperbound=float("Inf"),
        initial_value=1.0,
    )
    # Correct the aspirations and hard_constraints
    agg_aspirations = flip_maximized_objective_values(problem, agg_aspirations)
    # calculate the weights
    weights = None
    if type(delta) is dict:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta[obj.symbol]))
            for obj in problem.objectives
        }
    else:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta)) for obj in problem.objectives
        }

    # form the constaint and augmentation expressions
    # constraint expressions are formed into a list of lists
    con_terms = []
    for obj in problem.objectives:
        con_terms.append(f"(({weights[obj.symbol]}) * ({obj.symbol}_min - {agg_aspirations[obj.symbol]})) - _alpha")
    aug_exprs = []
    aug_expr = " + ".join([f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
    aug_exprs.append(aug_expr)
    aug_exprs = " + ".join(aug_exprs)

    func = f"_alpha + {rho} * ({aug_exprs})"

    scalarization_function = ScalarizationFunction(
        name="Differentiable achievement scalarizing function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_convex=problem.is_convex,
        is_linear=problem.is_linear,
        is_twice_differentiable=problem.is_twice_differentiable,
    )

    constraints = []
    # loop to create a constraint for every objective of every reference point given
    for obj in problem.objectives:
        if type(delta) is dict:
            expr = (
                f"({obj.symbol}_min - {agg_aspirations[obj.symbol]}) / "
                f"({nadir_point[obj.symbol]} - {ideal_point[obj.symbol] - delta[obj.symbol]}) - _alpha"
            )
        else:
            expr = (
                f"({obj.symbol}_min - {agg_aspirations[obj.symbol]}) / "
                f"({nadir_point[obj.symbol]} - {ideal_point[obj.symbol] - delta}) - _alpha"
            )
        constraints.append(
            Constraint(
                name=f"Constraint for {obj.symbol}",
                symbol=f"{obj.symbol}_maxcon",
                func=expr,
                cons_type=ConstraintTypeEnum.LTE,
                is_linear=obj.is_linear,
                is_convex=obj.is_convex,
                is_twice_differentiable=obj.is_twice_differentiable,
            )
        )

    #  get corrected bounds if exist
    if agg_bounds is not None:
        bounds = flip_maximized_objective_values(problem, agg_bounds)
        for obj in problem.objectives:
            expr = f"({obj.symbol}_min - {bounds[obj.symbol]} - _alpha)"
            constraints.append(
                Constraint(
                    name=f"Constraint bound for {obj.symbol}",
                    symbol=f"{obj.symbol}_con",
                    func=expr,
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=obj.is_linear,
                    is_convex=obj.is_convex,
                    is_twice_differentiable=obj.is_twice_differentiable,
                )
            )
    _problem = problem.add_variables([alpha])
    _problem = _problem.add_scalarization(scalarization_function)
    return _problem.add_constraints(constraints), symbol


def add_group_nimbus(  # noqa: PLR0913
    problem: Problem,
    symbol: str,
    classifications_list: list[dict[str, tuple[str, float | None]]],
    current_objective_vector: dict[str, float],
    agg_bounds: dict[str, float],
    delta: dict[str, float] | float = 0.000001,
    ideal: dict[str, float] | None = None,
    nadir: dict[str, float] | None = None,
    rho: float = 0.000001,
) -> tuple[Problem, str]:
    r"""Implements the multiple decision maker variant of the NIMBUS scalarization function.

    The scalarization function is defined as follows:

    \begin{align}
        &\mbox{minimize} &&\max_{i\in I^<,j\in I^\leq,d} [w_{id}(f_{id}(\mathbf{x})-z^{ideal}_{id}),
        w_{jd}(f_{jd}(\mathbf{x})-\hat{z}_{jd})] +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x}) \\
        &\mbox{subject to} &&\mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{z^{nad}_{id} - z^{uto}_{id}}$, and $w_{jd} = \frac{1}{z^{nad}_{jd} - z^{uto}_{jd}}$.

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

    Args:
        problem (Problem): the problem to be scalarized.
        symbol (str): the symbol given to the scalarization function, i.e., target of the optimization.
        classifications_list (list[dict[str, tuple[str, float  |  None]]]): a list of dicts, where the key is a symbol
            of an objective function, and the value is a tuple with a classification and an aspiration
            or a reservation level, or `None`, depending on the classification. See above for an
            explanation.
        current_objective_vector (dict[str, float]): the current objective vector that corresponds to
            a Pareto optimal solution. The classifications are assumed to been given in respect to
            this vector.
        agg_bounds dict[str, float]: a dictionary of bounds not to violate.
        ideal (dict[str, float], optional): ideal point values. If not given, attempt will be made
            to calculate ideal point from problem.
        nadir (dict[str, float], optional): nadir point values. If not given, attempt will be made
            to calculate nadir point from problem.
        delta (float, optional): a small scalar used to define the utopian point. Defaults to 0.000001.
        rho (float, optional): a small scalar used in the augmentation term. Defaults to 0.000001.

    Raises:
        ScalarizationError: any of the given classifications do not define a classification
            for all the objective functions or any of the given classifications do not allow at
            least one objective function value to improve and one to worsen.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """
    # check that classifications have been provided for all objective functions
    for classifications in classifications_list:
        if not objective_dict_has_all_symbols(problem, classifications):
            msg = (
                f"The given classifications {classifications} do not define "
                "a classification for all the objective functions."
            )
            raise ScalarizationError(msg)

    # check if ideal point is specified
    # if not specified, try to calculate corrected ideal point
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined!"
        raise ScalarizationError(msg)

    # check if nadir point is specified
    # if not specified, try to calculate corrected nadir point
    if nadir is not None:
        nadir_point = nadir
    elif problem.get_nadir_point() is not None:
        nadir_point = get_corrected_nadir(problem)
    else:
        msg = "Nadir point not defined!"
        raise ScalarizationError(msg)

    corrected_current_point = flip_maximized_objective_values(problem, current_objective_vector)
    bounds = flip_maximized_objective_values(problem, agg_bounds)

    # calculate the weights
    weights = None
    if type(delta) is dict:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta[obj.symbol]))
            for obj in problem.objectives
        }
    else:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta)) for obj in problem.objectives
        }

    # max term and constraints
    max_args = []
    constraints = []

    print(classifications_list)

    for i in range(len(classifications_list)):
        classifications = classifications_list[i]
        for obj in problem.objectives:
            _symbol = obj.symbol
            match classifications[_symbol]:
                case ("<", _):
                    max_expr = f"{weights[_symbol]} * ({_symbol}_min - {ideal_point[_symbol]})"
                    max_args.append(max_expr)

                    con_expr = f"{_symbol}_min - {corrected_current_point[_symbol]}"
                    constraints.append(
                        Constraint(
                            name=f"improvement constraint for {_symbol}",
                            symbol=f"{_symbol}_{i + 1}_lt",
                            func=con_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
                        )
                    )
                case ("<=", aspiration):
                    # if obj is to be maximized, then the current aspiration value needs to be multiplied by -1
                    max_expr = (
                        f"{weights[_symbol]} * ({_symbol}_min - {aspiration * -1 if obj.maximize else aspiration})"
                    )
                    max_args.append(max_expr)

                    con_expr = f"{_symbol}_min - {corrected_current_point[_symbol]}"
                    constraints.append(
                        Constraint(
                            name=f"improvement until constraint for {_symbol}",
                            symbol=f"{_symbol}_{i + 1}_lte",
                            func=con_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
                        )
                    )
                case ("=", _):
                    # not relevant for this group scalarization
                    pass

                case (">=", reservation):
                    con_expr = f"{_symbol}_min - {bounds[_symbol]} "
                    constraints.append(
                        Constraint(
                            name=f"Worsen until constraint for {_symbol}",
                            symbol=f"{_symbol}_{i + 1}_gte",
                            func=con_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
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

    # form the augmentation term
    aug_exprs = []
    for _ in range(len(classifications_list)):
        aug_expr = " + ".join([f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
        aug_exprs.append(aug_expr)
    aug_exprs = " + ".join(aug_exprs)

    func = f"{max_expr} + {rho} * ({aug_exprs})"
    scalarization = ScalarizationFunction(
        name="NIMBUS scalarization objective function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=False,
    )

    _problem = problem.add_scalarization(scalarization)
    return _problem.add_constraints(constraints), symbol


def add_group_nimbus_compromise(  # noqa: PLR0913
    problem: Problem,
    symbol: str,
    group_classification: dict[str, tuple[Literal["improve", "worsen", "conflict"], list[float]]],
    current_objective_vector: dict[str, float],
    agg_bounds: dict[str, float],
    *,
    delta: dict[str, float] | float = 0.000001,
    ideal: dict[str, float] | None = None,
    nadir: dict[str, float] | None = None,
    rho: float = 0.000001,
    find_compromise: bool = True,
) -> tuple[Problem, str]:
    """Add a group-based NIMBUS scalarization (multiple decision-maker variant) to a Problem.

    This function constructs and attaches a NIMBUS-style scalarization objective and
    corresponding constraints derived from a group-level classification of objectives.
    It supports three group classification types for each objective:
    - "improve": the group wants the objective to improve relative to the provided
        current objective vector;
    - "worsen": the group accepts a worsening of the objective but enforces an
        aggregate bound (agg_bounds);
    - "conflict": the group contains conflicting preferences; when find_compromise
        is True a compromise target is formed (median) and used like an "improve"
        preference if the compromise is an improvement, otherwise the original current
        point is enforced as in the "improve" fallback when find_compromise is False.
    Behavior summary
    - Validates that a classification is provided for every objective in the problem.
    - Ensures an ideal and nadir point are available (uses corrected problem values if
        not supplied; raises ScalarizationError otherwise).
    - Converts objective values for maximization problems to the same minimization
        convention used internally.
    - Computes normalization weights for each objective using nadir, ideal, and the
        provided delta (scalar or per-objective dict), i.e. weight_i = 1 / (nadir_i - (ideal_i - delta_i)).
    - For each objective, depending on the group classification:
            - "improve": may add a term to the scalarization's max(...) expression if the
                chosen target represents an improvement; always adds an improvement constraint
                that enforces the objective to be at least as good as the current point.
            - "worsen": adds a constraint preventing the objective from exceeding the
                provided agg_bounds value.
            - "conflict": if find_compromise is True, selects the median target from the
                group's values and treats it like an "improve" (if it improves); otherwise
                enforces the current point via an improvement constraint.
    - Constructs a scalarization objective of the form:
            Max(weight_i * (obj_i_min - ideal_i) for selected i) + rho * sum(weight_j * obj_j_min)
        where obj_k_min denotes the (possibly flipped) objective expression used for
        minimization in the scalarization and rho is the small augmentation coefficient.
    - Creates Constraint objects (with names and symbols derived from each objective)
        and appends them to the problem along with the new ScalarizationFunction.
    Parameters
    - problem (Problem): The problem instance to which the scalarization and constraints
        will be added. The function calls problem.add_scalarization(...) and
        problem.add_constraints(...).
    - symbol (str): Symbol/name for the new scalarization (target of optimization).
    - group_classification (dict[str, tuple[str, list[float]]]):
            A mapping from objective symbol -> (classification, group_targets).
            The classification must be one of: "improve", "worsen", "conflict".
            The second element is a list of numerical target values provided by the group
            members for that objective. Interpretation:
                - For "improve": the most ambitious group target is taken (currently the
                    maximum for maximization problems or minimum for minimization problems).
                - For "worsen": the strictest bound from the group is used to form a bound
                    constraint (implementation currently uses agg_bounds instead).
                - For "conflict": the median of the group targets is used when find_compromise
                    is True; otherwise treated like enforcing the current point.
    - current_objective_vector (dict[str, float]): Objective values corresponding to a
        (reference) Pareto-optimal solution; used as baseline for improvement constraints.
    - agg_bounds (dict[str, float]): Aggregate bounds that must not be violated for
        objectives marked as "worsen" (values are converted appropriately for
        maximization objectives).
    - delta (dict[str, float] | float, optional): Small utopian offset used to compute
        normalization weights. If a dict is given it should map objective symbols to
        deltas; if a scalar is given the same delta is used for all objectives.
        Default: 1e-6.
    - ideal (dict[str, float] | None, optional): Ideal point values. If None, the
        function attempts to obtain a corrected ideal point from the problem instance.
    - nadir (dict[str, float] | None, optional): Nadir point values. If None, the
        function attempts to obtain a corrected nadir point from the problem instance.
    - rho (float, optional): Small augmentation coefficient multiplied by the linear
        sum of weighted objectives to break ties and enforce weak Pareto optimality.
        Default: 1e-6.
    - find_compromise (bool, optional): If True, conflicting objectives use a median
        compromise target; otherwise conflicts are enforced to keep current values.
        Default: True.

    Returns:
    - tuple[Problem, str]: A tuple containing:
            - A new Problem instance (or the original problem mutated/augmented depending
                on Problem.add_scalarization/Problem.add_constraints semantics) with the
                scalarization objective and additional constraints appended.
            - The symbol (str) of the added scalarization.

    Raises:
    - ScalarizationError: if
            - the group_classification mapping does not provide a classification for every
                objective in the problem, or
            - neither an explicit ideal nor a computable corrected ideal is available, or
            - neither an explicit nadir nor a computable corrected nadir is available.
    - KeyError: if group_classification does not contain entries for objective symbols
        referenced in the problem (note: this will typically surface as KeyError during
        processing).
    Notes and implementation details
    - The function internally flips maximization objectives into a minimization form
        using flip_maximized_objective_values(...) so all scalarization math assumes
        minimization semantics.
    - Weight computation uses (nadir - (ideal - delta)); ensure delta is chosen so
        denominator is positive.
    - The "max" term in the scalarization is constructed from selected improving
        objectives only; the augmentation term is the (weighted) sum over all objectives.
    - Constraint objects are created with ConstraintTypeEnum.LTE and names/symbols
        formatted like "improvement constraint for {symbol}" or "Worsen until constraint
        for {symbol}".
    - The function currently prints group_classification (left for debugging) — this
        side effect may be removed in production code.
    """
    # check that classifications have been provided for all objective functions
    for classification in group_classification:
        if not objective_dict_has_all_symbols(problem, classification):
            msg = (
                f"The given classifications {classification} do not define "
                "a classification for all the objective functions."
            )
            raise ScalarizationError(msg)

    # check if ideal point is specified
    # if not specified, try to calculate corrected ideal point
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined!"
        raise ScalarizationError(msg)

    # check if nadir point is specified
    # if not specified, try to calculate corrected nadir point
    if nadir is not None:
        nadir_point = nadir
    elif problem.get_nadir_point() is not None:
        nadir_point = get_corrected_nadir(problem)
    else:
        msg = "Nadir point not defined!"
        raise ScalarizationError(msg)

    corrected_current_point = flip_maximized_objective_values(problem, current_objective_vector)
    bounds = flip_maximized_objective_values(problem, agg_bounds)

    # calculate the weights
    weights = None
    if type(delta) is dict:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta[obj.symbol]))
            for obj in problem.objectives
        }
    else:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta)) for obj in problem.objectives
        }

    # max term and constraints
    max_args = []
    constraints = []

    print(group_classification)

    # Derive the group classifications

    for obj in problem.objectives:
        _symbol = obj.symbol
        match group_classification[_symbol][0]:
            case "improve":
                # Take the most ambitious target among the group (could be changed to something else as well)
                target = (
                    -max(group_classification[_symbol][1]) if obj.maximize else min(group_classification[_symbol][1])
                )
                if target < corrected_current_point[_symbol]:
                    max_expr = f"{weights[_symbol]} * ({_symbol}_min - {ideal_point[_symbol]})"
                    max_args.append(max_expr)

                con_expr = f"{_symbol}_min - {corrected_current_point[_symbol]}"
                constraints.append(
                    Constraint(
                        name=f"improvement constraint for {_symbol}",
                        symbol=f"{_symbol}_lt",
                        func=con_expr,
                        cons_type=ConstraintTypeEnum.LTE,
                        is_linear=problem.is_linear,
                        is_convex=problem.is_convex,
                        is_twice_differentiable=problem.is_twice_differentiable,
                    )
                )

            case "worsen":
                # Take the strictest constraint given by the group (could be changed to something else as well)
                target = (
                    -max(group_classification[_symbol][1]) if obj.maximize else min(group_classification[_symbol][1])
                )
                con_expr = f"{_symbol}_min - {bounds[_symbol]} "
                constraints.append(
                    Constraint(
                        name=f"Worsen until constraint for {_symbol}",
                        symbol=f"{_symbol}_gte",
                        func=con_expr,
                        cons_type=ConstraintTypeEnum.LTE,
                        is_linear=problem.is_linear,
                        is_convex=problem.is_convex,
                        is_twice_differentiable=problem.is_twice_differentiable,
                    )
                )
            case "conflict":
                if find_compromise:
                    # Take the median target from the group (could be changed to something else as well)
                    target = np.median(group_classification[_symbol][1])
                    max_expr = f"{weights[_symbol]} * ({_symbol}_min - {ideal_point[_symbol]})"
                    max_args.append(max_expr)
                else:
                    con_expr = f"{_symbol}_min - {corrected_current_point[_symbol]}"
                    constraints.append(
                        Constraint(
                            name=f"improvement constraint for {_symbol}",
                            symbol=f"{_symbol}_lt",
                            func=con_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
                        )
                    )
            case _:
                msg = (
                    f"Warning! The classification {group_classification[_symbol]} was supplied, but it is not supported."
                    "Must be one of ['improve', 'worsen', 'conflict']"
                )
    max_expr = f"Max({','.join(max_args)})"

    # form the augmentation term
    aug_expr = " + ".join([f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])

    func = f"{max_expr} + {rho} * ({aug_expr})"
    scalarization = ScalarizationFunction(
        name="NIMBUS scalarization objective function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=False,
    )

    _problem = problem.add_scalarization(scalarization)
    return _problem.add_constraints(constraints), symbol


def add_group_nimbus_compromise_diff(  # noqa: PLR0913
    problem: Problem,
    symbol: str,
    group_classification: dict[str, tuple[Literal["improve", "worsen", "conflict"], list[float]]],
    current_objective_vector: dict[str, float],
    agg_bounds: dict[str, float],
    *,
    delta: dict[str, float] | float = 0.000001,
    ideal: dict[str, float] | None = None,
    nadir: dict[str, float] | None = None,
    rho: float = 0.000001,
    find_compromise: bool = True,
) -> tuple[Problem, str]:
    """Add a group-based NIMBUS scalarization (multiple decision-maker variant) to a Problem.

    This function constructs and attaches a NIMBUS-style scalarization objective and
    corresponding constraints derived from a group-level classification of objectives.
    It supports three group classification types for each objective:
    - "improve": the group wants the objective to improve relative to the provided
        current objective vector;
    - "worsen": the group accepts a worsening of the objective but enforces an
        aggregate bound (agg_bounds);
    - "conflict": the group contains conflicting preferences; when find_compromise
        is True a compromise target is formed (median) and used like an "improve"
        preference if the compromise is an improvement, otherwise the original current
        point is enforced as in the "improve" fallback when find_compromise is False.
    Behavior summary
    - Validates that a classification is provided for every objective in the problem.
    - Ensures an ideal and nadir point are available (uses corrected problem values if
        not supplied; raises ScalarizationError otherwise).
    - Converts objective values for maximization problems to the same minimization
        convention used internally.
    - Computes normalization weights for each objective using nadir, ideal, and the
        provided delta (scalar or per-objective dict), i.e. weight_i = 1 / (nadir_i - (ideal_i - delta_i)).
    - For each objective, depending on the group classification:
            - "improve": may add a term to the scalarization's max(...) expression if the
                chosen target represents an improvement; always adds an improvement constraint
                that enforces the objective to be at least as good as the current point.
            - "worsen": adds a constraint preventing the objective from exceeding the
                provided agg_bounds value.
            - "conflict": if find_compromise is True, selects the median target from the
                group's values and treats it like an "improve" (if it improves); otherwise
                enforces the current point via an improvement constraint.
    - Constructs a scalarization objective of the form:
            Max(weight_i * (obj_i_min - ideal_i) for selected i) + rho * sum(weight_j * obj_j_min)
        where obj_k_min denotes the (possibly flipped) objective expression used for
        minimization in the scalarization and rho is the small augmentation coefficient.
    - Creates Constraint objects (with names and symbols derived from each objective)
        and appends them to the problem along with the new ScalarizationFunction.
    Parameters
    - problem (Problem): The problem instance to which the scalarization and constraints
        will be added. The function calls problem.add_scalarization(...) and
        problem.add_constraints(...).
    - symbol (str): Symbol/name for the new scalarization (target of optimization).
    - group_classification (dict[str, tuple[str, list[float]]]):
            A mapping from objective symbol -> (classification, group_targets).
            The classification must be one of: "improve", "worsen", "conflict".
            The second element is a list of numerical target values provided by the group
            members for that objective. Interpretation:
                - For "improve": the most ambitious group target is taken (currently the
                    maximum for maximization problems or minimum for minimization problems).
                - For "worsen": the strictest bound from the group is used to form a bound
                    constraint (implementation currently uses agg_bounds instead).
                - For "conflict": the median of the group targets is used when find_compromise
                    is True; otherwise treated like enforcing the current point.
    - current_objective_vector (dict[str, float]): Objective values corresponding to a
        (reference) Pareto-optimal solution; used as baseline for improvement constraints.
    - agg_bounds (dict[str, float]): Aggregate bounds that must not be violated for
        objectives marked as "worsen" (values are converted appropriately for
        maximization objectives).
    - delta (dict[str, float] | float, optional): Small utopian offset used to compute
        normalization weights. If a dict is given it should map objective symbols to
        deltas; if a scalar is given the same delta is used for all objectives.
        Default: 1e-6.
    - ideal (dict[str, float] | None, optional): Ideal point values. If None, the
        function attempts to obtain a corrected ideal point from the problem instance.
    - nadir (dict[str, float] | None, optional): Nadir point values. If None, the
        function attempts to obtain a corrected nadir point from the problem instance.
    - rho (float, optional): Small augmentation coefficient multiplied by the linear
        sum of weighted objectives to break ties and enforce weak Pareto optimality.
        Default: 1e-6.
    - find_compromise (bool, optional): If True, conflicting objectives use a median
        compromise target; otherwise conflicts are enforced to keep current values.
        Default: True.

    Returns:
    - tuple[Problem, str]: A tuple containing:
            - A new Problem instance (or the original problem mutated/augmented depending
                on Problem.add_scalarization/Problem.add_constraints semantics) with the
                scalarization objective and additional constraints appended.
            - The symbol (str) of the added scalarization.

    Raises:
    - ScalarizationError: if
            - the group_classification mapping does not provide a classification for every
                objective in the problem, or
            - neither an explicit ideal nor a computable corrected ideal is available, or
            - neither an explicit nadir nor a computable corrected nadir is available.
    - KeyError: if group_classification does not contain entries for objective symbols
        referenced in the problem (note: this will typically surface as KeyError during
        processing).
    Notes and implementation details
    - The function internally flips maximization objectives into a minimization form
        using flip_maximized_objective_values(...) so all scalarization math assumes
        minimization semantics.
    - Weight computation uses (nadir - (ideal - delta)); ensure delta is chosen so
        denominator is positive.
    - The "max" term in the scalarization is constructed from selected improving
        objectives only; the augmentation term is the (weighted) sum over all objectives.
    - Constraint objects are created with ConstraintTypeEnum.LTE and names/symbols
        formatted like "improvement constraint for {symbol}" or "Worsen until constraint
        for {symbol}".
    - The function currently prints group_classification (left for debugging) — this
        side effect may be removed in production code.
    """
    # check that classifications have been provided for all objective functions
    for classification in group_classification:
        if not objective_dict_has_all_symbols(problem, classification):
            msg = (
                f"The given classifications {classification} do not define "
                "a classification for all the objective functions."
            )
            raise ScalarizationError(msg)

    # check if ideal point is specified
    # if not specified, try to calculate corrected ideal point
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined!"
        raise ScalarizationError(msg)

    # check if nadir point is specified
    # if not specified, try to calculate corrected nadir point
    if nadir is not None:
        nadir_point = nadir
    elif problem.get_nadir_point() is not None:
        nadir_point = get_corrected_nadir(problem)
    else:
        msg = "Nadir point not defined!"
        raise ScalarizationError(msg)

    corrected_current_point = flip_maximized_objective_values(problem, current_objective_vector)
    bounds = flip_maximized_objective_values(problem, agg_bounds)

    # calculate the weights
    weights = None
    if type(delta) is dict:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta[obj.symbol]))
            for obj in problem.objectives
        }
    else:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta)) for obj in problem.objectives
        }

    # max term and constraints
    constraints = []

    print(group_classification)

    # define the auxiliary variable
    alpha = Variable(
        name="alpha",
        symbol="_alpha",
        variable_type=VariableTypeEnum.real,
        lowerbound=-float("Inf"),
        upperbound=float("Inf"),
        initial_value=1.0,
    )

    # Derive the group classifications

    for obj in problem.objectives:
        _symbol = obj.symbol
        match group_classification[_symbol][0]:
            case "improve":
                # Take the most ambitious target among the group (could be changed to something else as well)
                target = (
                    -max(group_classification[_symbol][1]) if obj.maximize else min(group_classification[_symbol][1])
                )
                if target < corrected_current_point[_symbol]:
                    max_expr = f"{weights[_symbol]} * ({_symbol}_min - {ideal_point[_symbol]}) - _alpha"
                    constraints.append(
                        Constraint(
                            name=f"Max term linearization for {_symbol}",
                            symbol=f"max_con_{_symbol}",
                            func=max_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
                        )
                    )

                con_expr = f"{_symbol}_min - {corrected_current_point[_symbol]}"
                constraints.append(
                    Constraint(
                        name=f"improvement constraint for {_symbol}",
                        symbol=f"{_symbol}_lt",
                        func=con_expr,
                        cons_type=ConstraintTypeEnum.LTE,
                        is_linear=problem.is_linear,
                        is_convex=problem.is_convex,
                        is_twice_differentiable=problem.is_twice_differentiable,
                    )
                )

            case "worsen":
                # Take the strictest constraint given by the group (could be changed to something else as well)
                target = (
                    -max(group_classification[_symbol][1]) if obj.maximize else min(group_classification[_symbol][1])
                )
                con_expr = f"{_symbol}_min - {bounds[_symbol]} "
                constraints.append(
                    Constraint(
                        name=f"Worsen until constraint for {_symbol}",
                        symbol=f"{_symbol}_gte",
                        func=con_expr,
                        cons_type=ConstraintTypeEnum.LTE,
                        is_linear=problem.is_linear,
                        is_convex=problem.is_convex,
                        is_twice_differentiable=problem.is_twice_differentiable,
                    )
                )
            case "conflict":
                if find_compromise:
                    # Take the median target from the group (could be changed to something else as well)
                    target = np.median(group_classification[_symbol][1])
                    max_expr = f"{weights[_symbol]} * ({_symbol}_min - {ideal_point[_symbol]}) - _alpha"
                    constraints.append(
                        Constraint(
                            name=f"Max term linearization for {_symbol}",
                            symbol=f"max_con_{_symbol}",
                            func=max_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
                        )
                    )
                else:
                    con_expr = f"{_symbol}_min - {corrected_current_point[_symbol]}"
                    constraints.append(
                        Constraint(
                            name=f"improvement constraint for {_symbol}",
                            symbol=f"{_symbol}_lt",
                            func=con_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
                        )
                    )
            case _:
                msg = (
                    f"Warning! The classification {group_classification[_symbol]} was supplied, but it is not supported."
                    "Must be one of ['improve', 'worsen', 'conflict']"
                )

    # form the augmentation term
    aug_expr = " + ".join([f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])

    func = f"{alpha.symbol} + {rho} * ({aug_expr})"
    scalarization = ScalarizationFunction(
        name="NIMBUS scalarization objective function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=False,
    )

    _problem = problem.add_scalarization(scalarization)
    return _problem.add_constraints(constraints), symbol


def add_group_nimbus_sf(  # noqa: PLR0913
    problem: Problem,
    symbol: str,
    classifications_list: list[dict[str, tuple[str, float | None]]],
    current_objective_vector: dict[str, float],
    ideal: dict[str, float] | None = None,
    nadir: dict[str, float] | None = None,
    delta: float = 0.000001,
    rho: float = 0.000001,
) -> tuple[Problem, str]:
    r"""Implements the multiple decision maker variant of the NIMBUS scalarization function. Variant without aggregated bounds.

    The scalarization function is defined as follows:

    \begin{align}
        &\mbox{minimize} &&\max_{i\in I^<,j\in I^\leq,d} [w_{id}(f_{id}(\mathbf{x})-z^{ideal}_{id}),
        w_{jd}(f_{jd}(\mathbf{x})-\hat{z}_{jd})] +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x}) \\
        &\mbox{subject to} &&\mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{z^{nad}_{id} - z^{uto}_{id}}$, and $w_{jd} = \frac{1}{z^{nad}_{jd} - z^{uto}_{jd}}$.

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

    Args:
        problem (Problem): the problem to be scalarized.
        symbol (str): the symbol given to the scalarization function, i.e., target of the optimization.
        classifications_list (list[dict[str, tuple[str, float  |  None]]]): a list of dicts, where the key is a symbol
            of an objective function, and the value is a tuple with a classification and an aspiration
            or a reservation level, or `None`, depending on the classification. See above for an
            explanation.
        current_objective_vector (dict[str, float]): the current objective vector that corresponds to
            a Pareto optimal solution. The classifications are assumed to been given in respect to
            this vector.
        ideal (dict[str, float], optional): ideal point values. If not given, attempt will be made
            to calculate ideal point from problem.
        nadir (dict[str, float], optional): nadir point values. If not given, attempt will be made
            to calculate nadir point from problem.
        delta (float, optional): a small scalar used to define the utopian point. Defaults to 0.000001.
        rho (float, optional): a small scalar used in the augmentation term. Defaults to 0.000001.

    Raises:
        ScalarizationError: any of the given classifications do not define a classification
            for all the objective functions or any of the given classifications do not allow at
            least one objective function value to improve and one to worsen.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """
    # check that classifications have been provided for all objective functions
    for classifications in classifications_list:
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

    # check if ideal point is specified
    # if not specified, try to calculate corrected ideal point
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined!"
        raise ScalarizationError(msg)

    # check if nadir point is specified
    # if not specified, try to calculate corrected nadir point
    if nadir is not None:
        nadir_point = nadir
    elif problem.get_nadir_point() is not None:
        nadir_point = get_corrected_nadir(problem)
    else:
        msg = "Nadir point not defined!"
        raise ScalarizationError(msg)

    corrected_current_point = flip_maximized_objective_values(problem, current_objective_vector)

    # calculate the weights
    weights = {
        obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta)) for obj in problem.objectives
    }

    # max term and constraints
    max_args = []
    constraints = []

    for i in range(len(classifications_list)):
        classifications = classifications_list[i]
        for obj in problem.objectives:
            _symbol = obj.symbol
            match classifications[_symbol]:
                case ("<", _):
                    max_expr = f"{weights[_symbol]} * ({_symbol}_min - {ideal_point[_symbol]})"
                    max_args.append(max_expr)

                    con_expr = f"{_symbol}_min - {corrected_current_point[_symbol]}"
                    constraints.append(
                        Constraint(
                            name=f"improvement constraint for {_symbol}",
                            symbol=f"{_symbol}_{i + 1}_lt",
                            func=con_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
                        )
                    )
                case ("<=", aspiration):
                    # if obj is to be maximized, then the current aspiration value needs to be multiplied by -1
                    max_expr = (
                        f"{weights[_symbol]} * ({_symbol}_min - {aspiration * -1 if obj.maximize else aspiration})"
                    )
                    max_args.append(max_expr)

                    con_expr = f"{_symbol}_min - {corrected_current_point[_symbol]}"
                    constraints.append(
                        Constraint(
                            name=f"improvement until constraint for {_symbol}",
                            symbol=f"{_symbol}_{i + 1}_lte",
                            func=con_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
                        )
                    )
                case ("=", _):
                    con_expr = f"{_symbol}_min - {corrected_current_point[_symbol]}"
                    constraints.append(
                        Constraint(
                            name=f"Stay at least as good constraint for {_symbol}",
                            symbol=f"{_symbol}_{i + 1}_eq",
                            func=con_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
                        )
                    )
                case (">=", reservation):
                    # if obj is to be maximized, then the current reservation value needs to be multiplied by -1
                    con_expr = f"{_symbol}_min - {-1 * reservation if obj.maximize else reservation}"
                    constraints.append(
                        Constraint(
                            name=f"Worsen until constraint for {_symbol}",
                            symbol=f"{_symbol}_{i + 1}_gte",
                            func=con_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
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

    # form the augmentation term
    aug_exprs = []
    for _ in range(len(classifications_list)):
        aug_expr = " + ".join([f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
        aug_exprs.append(aug_expr)
    aug_exprs = " + ".join(aug_exprs)

    func = f"{max_expr} + {rho} * ({aug_exprs})"
    scalarization = ScalarizationFunction(
        name="NIMBUS scalarization objective function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=False,
    )

    _problem = problem.add_scalarization(scalarization)
    return _problem.add_constraints(constraints), symbol


def add_group_nimbus_diff(  # noqa: PLR0913
    problem: Problem,
    symbol: str,
    classifications_list: list[dict[str, tuple[str, float | None]]],
    current_objective_vector: dict[str, float],
    agg_bounds: dict[str, float],
    delta: dict[str, float] | float = 0.000001,
    ideal: dict[str, float] | None = None,
    nadir: dict[str, float] | None = None,
    rho: float = 0.000001,
) -> tuple[Problem, str]:
    r"""Implements the differentiable variant of the multiple decision maker of the group NIMBUS scalarization function.

    The scalarization function is defined as follows:

    \begin{align}
        \mbox{minimize} \quad
         &\alpha +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x})\\
        \mbox{subject to} \quad & w_{id}(f_{id}(\mathbf{x})-z^{ideal}_{id}) - \alpha \leq 0 \quad & \forall i \in I^<,\\
        & w_{jd}(f_{jd}(\mathbf{x})-\hat{z}_{jd}) - \alpha \leq 0 \quad & \forall j \in I^\leq ,\\
        & f_i(\mathbf{x}) - f_i(\mathbf{x_c}) \leq 0 \quad & \forall i \in I^< \cup I^\leq \cup I^= ,\\
        & f_i(\mathbf{x}) - \epsilon_i \leq 0 \quad & \forall i \in I^\geq ,\\
        & \mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{z^{nad}_{id} - z^{uto}_{id}}$, and $w_{jd} = \frac{1}{z^{nad}_{jd} - z^{uto}_{jd}}$.

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

    Args:
        problem (Problem): the problem to be scalarized.
        symbol (str): the symbol given to the scalarization function, i.e., target of the optimization.
        classifications_list (list[dict[str, tuple[str, float  |  None]]]): a list of dicts, where the key is a symbol
            of an objective function, and the value is a tuple with a classification and an aspiration
            or a reservation level, or `None`, depending on the classification. See above for an
            explanation.
        current_objective_vector (dict[str, float]): the current objective vector that corresponds to
            a Pareto optimal solution. The classifications are assumed to been given in respect to
            this vector.
        agg_bounds dict[str, float]: a dictionary of bounds not to violate.
        ideal (dict[str, float], optional): ideal point values. If not given, attempt will be made
            to calculate ideal point from problem.
        nadir (dict[str, float], optional): nadir point values. If not given, attempt will be made
            to calculate nadir point from problem.
        delta (float, optional): a small scalar used to define the utopian point. Defaults to 0.000001.
        rho (float, optional): a small scalar used in the augmentation term. Defaults to 0.000001.

    Raises:
        ScalarizationError: any of the given classifications do not define a classification
            for all the objective functions or any of the given classifications do not allow at
            least one objective function value to improve and one to worsen.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """
    # check that classifications have been provided for all objective functions
    for classifications in classifications_list:
        if not objective_dict_has_all_symbols(problem, classifications):
            msg = (
                f"The given classifications {classifications} do not define "
                "a classification for all the objective functions."
            )
            raise ScalarizationError(msg)

    # check if ideal point is specified
    # if not specified, try to calculate corrected ideal point
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined!"
        raise ScalarizationError(msg)

    # check if nadir point is specified
    # if not specified, try to calculate corrected nadir point
    if nadir is not None:
        nadir_point = nadir
    elif problem.get_nadir_point() is not None:
        nadir_point = get_corrected_nadir(problem)
    else:
        msg = "Nadir point not defined!"
        raise ScalarizationError(msg)

    corrected_current_point = flip_maximized_objective_values(problem, current_objective_vector)
    bounds = flip_maximized_objective_values(problem, agg_bounds)

    # define the auxiliary variable
    alpha = Variable(
        name="alpha",
        symbol="_alpha",
        variable_type=VariableTypeEnum.real,
        lowerbound=-float("Inf"),
        upperbound=float("Inf"),
        initial_value=1.0,
    )

    # calculate the weights
    weights = None
    if type(delta) is dict:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta[obj.symbol]))
            for obj in problem.objectives
        }
    else:
        weights = {
            obj.symbol: 1 / (nadir_point[obj.symbol] - (ideal_point[obj.symbol] - delta)) for obj in problem.objectives
        }

    constraints = []

    for i in range(len(classifications_list)):
        classifications = classifications_list[i]
        for obj in problem.objectives:
            _symbol = obj.symbol
            match classifications[_symbol]:
                case ("<", _):
                    max_expr = f"{weights[_symbol]} * ({_symbol}_min - {ideal_point[_symbol]}) - _alpha"
                    constraints.append(
                        Constraint(
                            name=f"Max term linearization for {_symbol}",
                            symbol=f"max_con_{_symbol}_{i + 1}",
                            func=max_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
                        )
                    )
                    con_expr = f"{_symbol}_min - {corrected_current_point[_symbol]} - _alpha"
                    constraints.append(
                        Constraint(
                            name=f"improvement constraint for {_symbol}",
                            symbol=f"{_symbol}_{i + 1}_lt",
                            func=con_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
                        )
                    )
                case ("<=", aspiration):
                    # if obj is to be maximized, then the current aspiration value needs to be multiplied by -1
                    max_expr = (
                        f"{weights[_symbol]} * ({_symbol}_min - {aspiration * -1 if obj.maximize else aspiration}) "
                        "- _alpha"
                    )
                    constraints.append(
                        Constraint(
                            name=f"Max term linearization for {_symbol}",
                            symbol=f"max_con_{_symbol}_{i + 1}",
                            func=max_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
                        )
                    )
                    con_expr = f"{_symbol}_min - {corrected_current_point[_symbol]} - _alpha"
                    constraints.append(
                        Constraint(
                            name=f"improvement until constraint for {_symbol}",
                            symbol=f"{_symbol}_{i + 1}_lte",
                            func=con_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
                        )
                    )
                case ("=", _):
                    # not relevant for this group scalarization
                    pass
                case (">=", reservation):
                    con_expr = f"{_symbol}_min - {bounds[_symbol]}"
                    constraints.append(
                        Constraint(
                            name=f"Worsen until constraint for {_symbol}",
                            symbol=f"{_symbol}_{i + 1}_gte",
                            func=con_expr,
                            cons_type=ConstraintTypeEnum.LTE,
                            is_linear=problem.is_linear,
                            is_convex=problem.is_convex,
                            is_twice_differentiable=problem.is_twice_differentiable,
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

    # form the augmentation term
    aug_exprs = []
    for _ in range(len(classifications_list)):
        aug_expr = " + ".join([f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
        aug_exprs.append(aug_expr)
    aug_exprs = " + ".join(aug_exprs)

    func = f"_alpha + {rho} * ({aug_exprs})"
    scalarization_function = ScalarizationFunction(
        name="Differentiable NIMBUS scalarization objective function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=problem.is_twice_differentiable,
    )
    _problem = problem.add_variables([alpha])
    _problem = _problem.add_scalarization(scalarization_function)
    return _problem.add_constraints(constraints), symbol


def add_group_stom(
    problem: Problem,
    symbol: str,
    reference_points: list[dict[str, float]],
    agg_bounds: dict[str, float] | None = None,
    delta: dict[str, float] | float = 1e-6,
    ideal: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds the multiple decision maker variant of the STOM scalarizing function.

    The scalarization function is defined as follows:

    \begin{align}
        &\mbox{minimize} &&\max_{i,d} [w_{id}(f_{id}(\mathbf{x})-z^{uto}_{id})] +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x}) \\
        &\mbox{subject to} &&\mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{\overline{z}_{id} - z^{uto}_{id}}$.

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_points (list[dict[str, float]]): a list of dicts with keys corresponding to objective
            function symbols and values to reference point components, i.e.,
            aspiration levels.
        agg_bounds dict[str, float]: a dictionary of bounds not to violate.
        ideal (dict[str, float], optional): ideal point values. If not given, attempt will be made
            to calculate ideal point from problem.
        rho (float, optional): a small scalar value to scale the sum in the objective
            function of the scalarization. Defaults to 1e-6.
        delta (float, optional): a small scalar value to define the utopian point. Defaults to 1e-6.

    Raises:
        ScalarizationError: there are missing elements in any reference point.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """
    # check reference points
    for reference_point in reference_points:
        if not objective_dict_has_all_symbols(problem, reference_point):
            msg = f"The give reference point {reference_point} is missing value for one or more objectives."
            raise ScalarizationError(msg)

    # check if ideal point is specified
    # if not specified, try to calculate corrected ideal point
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined!"
        raise ScalarizationError(msg)

    # calculate the weights
    weights = []
    for reference_point in reference_points:
        corrected_rp = flip_maximized_objective_values(problem, reference_point)
        if type(delta) is dict:
            weights.append(
                {
                    obj.symbol: 1 / ((corrected_rp[obj.symbol] - ideal_point[obj.symbol]) + delta[obj.symbol])
                    for obj in problem.objectives
                }
            )
        else:
            weights.append(
                {
                    obj.symbol: 1 / ((corrected_rp[obj.symbol] - ideal_point[obj.symbol]) + delta)
                    for obj in problem.objectives
                }
            )

    # form the max term
    max_terms = []
    for i in range(len(reference_points)):
        for obj in problem.objectives:
            if type(delta) is dict:
                max_terms.append(
                    f"{weights[i][obj.symbol]} * ({obj.symbol}_min - {ideal_point[obj.symbol] - delta[obj.symbol]})"
                )
            else:
                max_terms.append(f"{weights[i][obj.symbol]} * ({obj.symbol}_min - {ideal_point[obj.symbol] - delta})")
    max_terms = ", ".join(max_terms)

    # form the augmentation term
    aug_exprs = []
    for i in range(len(reference_points)):
        aug_expr = " + ".join([f"({weights[i][obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
        aug_exprs.append(aug_expr)
    aug_exprs = " + ".join(aug_exprs)

    func = f"{Op.MAX}({max_terms}) + {rho}*({aug_exprs})"

    scalarization_function = ScalarizationFunction(
        name="STOM scalarization objective function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=False,
    )
    problem = problem.add_scalarization(scalarization_function)
    #  get corrected bounds if exist
    if agg_bounds is not None:
        bounds = flip_maximized_objective_values(problem, agg_bounds)
        constraints = []
        for obj in problem.objectives:
            expr = f"({obj.symbol}_min - {bounds[obj.symbol]})"
            constraints.append(
                Constraint(
                    name=f"Constraint bound for {obj.symbol}",
                    symbol=f"{obj.symbol}_con",
                    func=expr,
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=obj.is_linear,
                    is_convex=obj.is_convex,
                    is_twice_differentiable=obj.is_twice_differentiable,
                )
            )
        problem = problem.add_constraints(constraints)

    return problem, symbol


def add_group_stom_agg(
    problem: Problem,
    symbol: str,
    agg_aspirations: dict[str, float],
    agg_bounds: dict[str, float],
    delta: dict[str, float] | float = 1e-6,
    ideal: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds the multiple decision maker variant of the STOM scalarizing function.

    Both aggregated aspiration levels (min aspirations) and agg bounds (max bounds) are required.

    The scalarization function is defined as follows:

    \begin{align}
        &\mbox{minimize} &&\max_{i,d} [w_{id}(f_{id}(\mathbf{x})-z^{uto}_{id})] +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x}) \\
        &\mbox{subject to} &&\mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{\overline{z}_{id} - z^{uto}_{id}}$.

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_points (list[dict[str, float]]): a list of dicts with keys corresponding to objective
            function symbols and values to reference point components, i.e.,
            aspiration levels.
        agg_bounds dict[str, float]: a dictionary of bounds not to violate.
        ideal (dict[str, float], optional): ideal point values. If not given, attempt will be made
            to calculate ideal point from problem.
        rho (float, optional): a small scalar value to scale the sum in the objective
            function of the scalarization. Defaults to 1e-6.
        delta (float, optional): a small scalar value to define the utopian point. Defaults to 1e-6.

    Raises:
        ScalarizationError: there are missing elements in any reference point.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """

    # check if ideal point is specified
    # if not specified, try to calculate corrected ideal point
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined!"
        raise ScalarizationError(msg)

    # Correct the aspirations and hard_constraints
    agg_aspirations = flip_maximized_objective_values(problem, agg_aspirations)
    agg_bounds = flip_maximized_objective_values(problem, agg_bounds)

    # calculate the weights
    weights = None
    if type(delta) is dict:
        weights = {
            obj.symbol: 1 / ((agg_aspirations[obj.symbol] - ideal_point[obj.symbol]) + delta[obj.symbol])
            for obj in problem.objectives
        }
    else:
        weights = {
            obj.symbol: 1 / ((agg_aspirations[obj.symbol] - ideal_point[obj.symbol]) + delta)
            for obj in problem.objectives
        }

    # form the max and augmentation terms
    max_terms = []
    aug_exprs = []
    for obj in problem.objectives:
        if type(delta) is dict:
            max_terms.append(
                f"({weights[obj.symbol]}) * ({obj.symbol}_min - {ideal_point[obj.symbol] - delta[obj.symbol]} )"
            )
        else:
            max_terms.append(f"{weights[obj.symbol]} * ({obj.symbol}_min - {ideal_point[obj.symbol] - delta})")

    aug_expr = " + ".join([f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
    aug_exprs.append(aug_expr)
    max_terms = ", ".join(max_terms)
    aug_exprs = " + ".join(aug_exprs)

    func = f"{Op.MAX}({max_terms}) + {rho} * ({aug_exprs})"

    scalarization_function = ScalarizationFunction(
        name="STOM scalarizing function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_convex=problem.is_convex,
        is_linear=problem.is_linear,
        is_twice_differentiable=False,
    )

    constraints = []

    for obj in problem.objectives:
        expr = f"({obj.symbol}_min - {agg_bounds[obj.symbol]})"
        constraints.append(
            Constraint(
                name=f"Constraint bound for {obj.symbol}",
                symbol=f"{obj.symbol}_con",
                func=expr,
                cons_type=ConstraintTypeEnum.LTE,
                is_linear=obj.is_linear,
                is_convex=obj.is_convex,
                is_twice_differentiable=obj.is_twice_differentiable,
            )
        )

    problem = problem.add_constraints(constraints)
    problem = problem.add_scalarization(scalarization_function)

    return problem, symbol


def add_group_stom_diff(
    problem: Problem,
    symbol: str,
    reference_points: list[dict[str, float]],
    agg_bounds: dict[str, float] | None = None,
    delta: dict[str, float] | float = 1e-6,
    ideal: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds the differentiable variant of the multiple decision maker variant of the STOM scalarizing function.

    The scalarization function is defined as follows:

    \begin{align}
        &\mbox{minimize} && \alpha +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x}) \\
        &\mbox{subject to} && w_{id}(f_{id}(\mathbf{x})-z^{uto}_{id}) - \alpha \leq 0,\\
        &&&\mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{\overline{z}_{id} - z^{uto}_{id}}$.

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_points (list[dict[str, float]]): a list of dicts with keys corresponding to objective
            function symbols and values to reference point components, i.e.,
            aspiration levels.
        ideal (dict[str, float], optional): ideal point values. If not given, attempt will be made
            to calculate ideal point from problem.
        agg_bounds dict[str, float]: a dictionary of bounds not to violate.
        rho (float, optional): a small scalar value to scale the sum in the objective
            function of the scalarization. Defaults to 1e-6.
        delta (float, optional): a small scalar value to define the utopian point. Defaults to 1e-6.

    Raises:
        ScalarizationError: there are missing elements in any reference point.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """
    # check reference points
    for reference_point in reference_points:
        if not objective_dict_has_all_symbols(problem, reference_point):
            msg = f"The give reference point {reference_point} is missing value for one or more objectives."
            raise ScalarizationError(msg)

    # check if ideal point is specified
    # if not specified, try to calculate corrected ideal point
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined!"
        raise ScalarizationError(msg)

    # define the auxiliary variable
    alpha = Variable(
        name="alpha",
        symbol="_alpha",
        variable_type=VariableTypeEnum.real,
        lowerbound=-float("Inf"),
        upperbound=float("Inf"),
        initial_value=1.0,
    )

    # calculate the weights
    weights = []
    for reference_point in reference_points:
        corrected_rp = flip_maximized_objective_values(problem, reference_point)
        if type(delta) is dict:
            weights.append(
                {
                    obj.symbol: 1 / ((corrected_rp[obj.symbol] - ideal_point[obj.symbol]) + delta[obj.symbol])
                    for obj in problem.objectives
                }
            )
        else:
            weights.append(
                {
                    obj.symbol: 1 / ((corrected_rp[obj.symbol] - ideal_point[obj.symbol]) + delta)
                    for obj in problem.objectives
                }
            )

    # form the max term
    con_terms = []
    for i in range(len(reference_points)):
        rp = {}
        for obj in problem.objectives:
            if type(delta) is dict:
                rp[obj.symbol] = (
                    f"{weights[i][obj.symbol]} * ({obj.symbol}_min - {ideal_point[obj.symbol] - delta[obj.symbol]}) - _alpha"
                )
            else:
                rp[obj.symbol] = (
                    f"{weights[i][obj.symbol]} * ({obj.symbol}_min - {ideal_point[obj.symbol] - delta}) - _alpha"
                )
        con_terms.append(rp)

    # form the augmentation term
    aug_exprs = []
    for i in range(len(reference_points)):
        aug_expr = " + ".join([f"({weights[i][obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
        aug_exprs.append(aug_expr)
    aug_exprs = " + ".join(aug_exprs)

    constraints = []
    # loop to create a constraint for every objective of every reference point given
    for i in range(len(reference_points)):
        for obj in problem.objectives:
            # since we are subtracting a constant value, the linearity, convexity,
            # and differentiability of the objective function, and hence the
            # constraint, should not change.
            constraints.append(
                Constraint(
                    name=f"Constraint for {obj.symbol}",
                    symbol=f"{obj.symbol}_con_{i + 1}",
                    func=con_terms[i][obj.symbol],
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=obj.is_linear,
                    is_convex=obj.is_convex,
                    is_twice_differentiable=obj.is_twice_differentiable,
                )
            )
    #  get corrected bounds if exist
    if agg_bounds is not None:
        bounds = flip_maximized_objective_values(problem, agg_bounds)
        for obj in problem.objectives:
            expr = f"({obj.symbol}_min - {bounds[obj.symbol]} -_alpha)"
            constraints.append(
                Constraint(
                    name=f"Constraint bound for {obj.symbol}",
                    symbol=f"{obj.symbol}_con",
                    func=expr,
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=obj.is_linear,
                    is_convex=obj.is_convex,
                    is_twice_differentiable=obj.is_twice_differentiable,
                )
            )
    func = f"_alpha + {rho}*({aug_exprs})"
    scalarization = ScalarizationFunction(
        name="Differentiable STOM scalarization objective function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=problem.is_twice_differentiable,
    )
    _problem = problem.add_variables([alpha])
    _problem = _problem.add_scalarization(scalarization)
    return _problem.add_constraints(constraints), symbol


def add_group_stom_agg_diff(
    problem: Problem,
    symbol: str,
    agg_aspirations: dict[str, float],
    agg_bounds: dict[str, float] | None = None,
    delta: dict[str, float] | float = 1e-6,
    ideal: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds the differentiable variant of the multiple decision maker variant of the STOM scalarizing function.

    Both aggregated aspiration levels (min aspirations) and agg bounds (max bounds) are required.
    The scalarization function is defined as follows:

    \begin{align}
        &\mbox{minimize} && \alpha +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x}) \\
        &\mbox{subject to} && w_{id}(f_{id}(\mathbf{x})-z^{uto}_{id}) - \alpha \leq 0,\\
        &&&\mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{\overline{z}_{id} - z^{uto}_{id}}$.

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_points (list[dict[str, float]]): a list of dicts with keys corresponding to objective
            function symbols and values to reference point components, i.e.,
            aspiration levels.
        ideal (dict[str, float], optional): ideal point values. If not given, attempt will be made
            to calculate ideal point from problem.
        agg_bounds dict[str, float]: a dictionary of bounds not to violate.
        rho (float, optional): a small scalar value to scale the sum in the objective
            function of the scalarization. Defaults to 1e-6.
        delta (float, optional): a small scalar value to define the utopian point. Defaults to 1e-6.

    Raises:
        ScalarizationError: there are missing elements in any reference point.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """

    # check if ideal point is specified
    # if not specified, try to calculate corrected ideal point
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined!"
        raise ScalarizationError(msg)

    # define the auxiliary variable
    alpha = Variable(
        name="alpha",
        symbol="_alpha",
        variable_type=VariableTypeEnum.real,
        lowerbound=-float("Inf"),
        upperbound=float("Inf"),
        initial_value=1.0,
    )
    # Correct the aspirations and hard_constraints
    agg_aspirations = flip_maximized_objective_values(problem, agg_aspirations)

    # calculate the weights
    weights = {}
    if type(delta) is dict:
        weights = {
            obj.symbol: 1 / ((agg_aspirations[obj.symbol] - ideal_point[obj.symbol]) + delta[obj.symbol])
            for obj in problem.objectives
        }
    else:
        weights = {
            obj.symbol: 1 / ((agg_aspirations[obj.symbol] - ideal_point[obj.symbol]) + delta)
            for obj in problem.objectives
        }

    # form the max term
    con_terms = []
    for obj in problem.objectives:
        if type(delta) is dict:
            con_terms.append(
                f"{weights[obj.symbol]} * ({obj.symbol}_min - {ideal_point[obj.symbol] - delta[obj.symbol]}) - _alpha"
            )
        else:
            con_terms.append(f"{weights[obj.symbol]} * ({obj.symbol}_min - {ideal_point[obj.symbol] - delta}) - _alpha")

    # form the augmentation term
    aug_exprs = []
    aug_expr = " + ".join([f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
    aug_exprs.append(aug_expr)
    aug_exprs = " + ".join(aug_exprs)

    constraints = []
    # loop to create a constraint for every objective of every reference point given
    for obj in problem.objectives:
        if type(delta) is dict:
            expr = (
                f"({obj.symbol}_min - {ideal_point[obj.symbol] - delta[obj.symbol]}) / "
                f"({agg_aspirations[obj.symbol] - (ideal_point[obj.symbol] - delta[obj.symbol])}) - _alpha"
            )
        else:
            expr = (
                f"({obj.symbol}_min - {ideal_point[obj.symbol] - delta}) / "
                f"({agg_aspirations[obj.symbol] - (ideal_point[obj.symbol] - delta)}) - _alpha"
            )
        constraints.append(
            Constraint(
                name=f"Constraint for {obj.symbol}",
                symbol=f"{obj.symbol}_maxcon",
                func=expr,
                cons_type=ConstraintTypeEnum.LTE,
                is_linear=obj.is_linear,
                is_convex=obj.is_convex,
                is_twice_differentiable=obj.is_twice_differentiable,
            )
        )
    #  get corrected bounds if exist
    if agg_bounds is not None:
        bounds = flip_maximized_objective_values(problem, agg_bounds)
        for obj in problem.objectives:
            expr = f"({obj.symbol}_min - {bounds[obj.symbol]} -_alpha)"
            constraints.append(
                Constraint(
                    name=f"Constraint bound for {obj.symbol}",
                    symbol=f"{obj.symbol}_con",
                    func=expr,
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=obj.is_linear,
                    is_convex=obj.is_convex,
                    is_twice_differentiable=obj.is_twice_differentiable,
                )
            )
    func = f"_alpha + {rho}*({aug_exprs})"
    scalarization = ScalarizationFunction(
        name="Differentiable STOM scalarization objective function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=problem.is_twice_differentiable,
    )
    _problem = problem.add_variables([alpha])
    _problem = _problem.add_scalarization(scalarization)
    return _problem.add_constraints(constraints), symbol


def add_group_guess(
    problem: Problem,
    symbol: str,
    reference_points: list[dict[str, float]],
    agg_bounds: dict[str, float] | None = None,
    delta: dict[str, float] | float = 1e-6,
    nadir: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds the non-differentiable variant of the multiple decision maker variant of the GUESS scalarizing function.

    The scalarization function is defined as follows:

    \begin{align}
        &\mbox{minimize} &&\max_{i,d} [w_{id}(f_{id}(\mathbf{x})-z^{nad}_{id})] +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x}) \\
        &\mbox{subject to} &&\mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{z^{nad}_{id} - \overline{z}_{id}}$.

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_points (list[dict[str, float]]): a list of dicts with keys corresponding to objective
            function symbols and values to reference point components, i.e.,
            aspiration levels.
        agg_bounds dict[str, float]: a dictionary of bounds not to violate.
        nadir (dict[str, float], optional): nadir point values. If not given, attempt will be made
            to calculate nadir point from problem.
        rho (float, optional): a small scalar value to scale the sum in the objective
            function of the scalarization. Defaults to 1e-6.
        delta (float, optional): a small scalar to define the utopian point. Defaults to 1e-6.

    Raises:
        ScalarizationError: there are missing elements in any reference point.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """
    # check reference points
    for reference_point in reference_points:
        if not objective_dict_has_all_symbols(problem, reference_point):
            msg = f"The give reference point {reference_point} is missing value for one or more objectives."
            raise ScalarizationError(msg)

    # check if nadir point is specified
    # if not specified, try to calculate corrected nadir point
    if nadir is not None:
        nadir_point = nadir
    elif problem.get_nadir_point() is not None:
        nadir_point = get_corrected_nadir(problem)
    else:
        msg = "Nadir point not defined!"
        raise ScalarizationError(msg)

    # calculate the weights
    weights = []
    for reference_point in reference_points:
        corrected_rp = flip_maximized_objective_values(problem, reference_point)
        if type(delta) is dict:
            weights.append(
                {
                    obj.symbol: 1 / ((nadir_point[obj.symbol] + delta[obj.symbol]) - (corrected_rp[obj.symbol]))
                    for obj in problem.objectives
                }
            )
        else:
            weights.append(
                {
                    obj.symbol: 1 / ((nadir_point[obj.symbol] + delta) - (corrected_rp[obj.symbol]))
                    for obj in problem.objectives
                }
            )

    # form the max term
    max_terms = []
    for i in range(len(reference_points)):
        corrected_rp = flip_maximized_objective_values(problem, reference_points[i])
        for obj in problem.objectives:
            if type(delta) is dict:
                max_terms.append(
                    f"{weights[i][obj.symbol]} * ({obj.symbol}_min - {nadir_point[obj.symbol] + delta[obj.symbol]} )"
                )
            else:
                max_terms.append(f"{weights[i][obj.symbol]} * ({obj.symbol}_min - {nadir_point[obj.symbol] + delta})")
    max_terms = ", ".join(max_terms)

    # form the augmentation term
    aug_exprs = []
    for i in range(len(reference_points)):
        aug_expr = " + ".join([f"({weights[i][obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
        aug_exprs.append(aug_expr)
    aug_exprs = " + ".join(aug_exprs)

    func = f"{Op.MAX}({max_terms}) + {rho}*({aug_exprs})"
    scalarization_function = ScalarizationFunction(
        name="GUESS scalarization objective function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=False,
    )
    problem = problem.add_scalarization(scalarization_function)
    #  get corrected bounds if exist
    if agg_bounds is not None:
        bounds = flip_maximized_objective_values(problem, agg_bounds)
        constraints = []
        for obj in problem.objectives:
            expr = f"({obj.symbol}_min - {bounds[obj.symbol]})"
            constraints.append(
                Constraint(
                    name=f"Constraint bound for {obj.symbol}",
                    symbol=f"{obj.symbol}_con",
                    func=expr,
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=obj.is_linear,
                    is_convex=obj.is_convex,
                    is_twice_differentiable=obj.is_twice_differentiable,
                )
            )
        problem = problem.add_constraints(constraints)

    return problem, symbol


def add_group_guess_agg(
    problem: Problem,
    symbol: str,
    agg_aspirations: dict[str, float],
    agg_bounds: dict[str, float],
    delta: dict[str, float] | float = 1e-6,
    ideal: dict[str, float] | None = None,
    nadir: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds the multiple decision maker variant of the GUESS scalarizing function.

    Both aggregated aspiration levels (min aspirations) and agg bounds (max bounds) are required.

    The scalarization function is defined as follows:

    \begin{align}
        &\mbox{minimize} &&\max_{i,d} [w_{id}(f_{id}(\mathbf{x})-z^{uto}_{id})] +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x}) \\
        &\mbox{subject to} &&\mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{\overline{z}_{id} - z^{uto}_{id}}$.

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_points (list[dict[str, float]]): a list of dicts with keys corresponding to objective
            function symbols and values to reference point components, i.e.,
            aspiration levels.
        ideal (dict[str, float], optional): ideal point values. If not given, attempt will be made
            to calculate ideal point from problem.
        rho (float, optional): a small scalar value to scale the sum in the objective
            function of the scalarization. Defaults to 1e-6.
        delta (float, optional): a small scalar value to define the utopian point. Defaults to 1e-6.

    Raises:
        ScalarizationError: there are missing elements in any reference point.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """

    # check if ideal point is specified
    # if not specified, try to calculate corrected ideal point
    if ideal is not None:
        ideal_point = ideal
    elif problem.get_ideal_point() is not None:
        ideal_point = get_corrected_ideal(problem)
    else:
        msg = "Ideal point not defined!"
        raise ScalarizationError(msg)

    # check if nadir point is specified
    # if not specified, try to calculate corrected nadir point
    if nadir is not None:
        nadir_point = nadir
    elif problem.get_nadir_point() is not None:
        nadir_point = get_corrected_nadir(problem)
    else:
        msg = "Nadir point not defined!"
        raise ScalarizationError(msg)

    # Correct the aspirations and hard_constraints
    agg_aspirations = flip_maximized_objective_values(problem, agg_aspirations)
    agg_bounds = flip_maximized_objective_values(problem, agg_bounds)

    # calculate the weights
    weights = None
    if type(delta) is dict:
        weights = {
            obj.symbol: 1 / ((nadir_point[obj.symbol] + delta[obj.symbol]) - (agg_aspirations[obj.symbol]))
            for obj in problem.objectives
        }
    else:
        weights = {
            obj.symbol: 1 / ((nadir_point[obj.symbol] + delta) - (agg_aspirations[obj.symbol]))
            for obj in problem.objectives
        }

    # form the max and augmentation terms
    max_terms = []
    aug_exprs = []
    for obj in problem.objectives:
        if type(delta) is dict:
            max_terms.append(
                f"{weights[obj.symbol]} * ({obj.symbol}_min - {nadir_point[obj.symbol] + delta[obj.symbol]} )"
            )
        else:
            max_terms.append(f"{weights[obj.symbol]} * ({obj.symbol}_min - {nadir_point[obj.symbol] + delta})")

    aug_expr = " + ".join([f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
    aug_exprs.append(aug_expr)
    max_terms = ", ".join(max_terms)
    aug_exprs = " + ".join(aug_exprs)

    func = f"{Op.MAX}({max_terms}) + {rho} * ({aug_exprs})"

    scalarization_function = ScalarizationFunction(
        name="GUESS scalarizing function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_convex=problem.is_convex,
        is_linear=problem.is_linear,
        is_twice_differentiable=False,
    )

    constraints = []

    for obj in problem.objectives:
        expr = f"({obj.symbol}_min - {agg_bounds[obj.symbol]})"
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

    problem = problem.add_constraints(constraints)
    problem = problem.add_scalarization(scalarization_function)

    return problem, symbol


def add_group_guess_diff(
    problem: Problem,
    symbol: str,
    reference_points: list[dict[str, float]],
    agg_bounds: dict[str, float] | None = None,
    delta: dict[str, float] | float = 1e-6,
    nadir: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds the differentiable variant of the multiple decision maker variant of the GUESS scalarizing function.

    The scalarization function is defined as follows:

    \begin{align}
        &\mbox{minimize} &&\alpha +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x}) \\
        &\mbox{subject to} && w_{id}(f_{id}(\mathbf{x})-z^{nad}_{id}) - \alpha \leq 0,\\
        &&&\mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{z^{nad}_{id} - \overline{z}_{id}}$.

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_points (list[dict[str, float]]): a list of dicts with keys corresponding to objective
            function symbols and values to reference point components, i.e.,
            aspiration levels.
        nadir (dict[str, float], optional): nadir point values. If not given, attempt will be made
            to calculate nadir point from problem.
        agg_bounds dict[str, float]: a dictionary of bounds not to violate.
        rho (float, optional): a small scalar value to scale the sum in the objective
            function of the scalarization. Defaults to 1e-6.
        delta (float, optional): a small scalar to define the utopian point. Defaults to 1e-6.

    Raises:
        ScalarizationError: there are missing elements in any reference point.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """
    # check reference points
    for reference_point in reference_points:
        if not objective_dict_has_all_symbols(problem, reference_point):
            msg = f"The give reference point {reference_point} is missing value for one or more objectives."
            raise ScalarizationError(msg)

    # check if nadir point is specified
    # if not specified, try to calculate corrected nadir point
    if nadir is not None:
        nadir_point = nadir
    elif problem.get_nadir_point() is not None:
        nadir_point = get_corrected_nadir(problem)
    else:
        msg = "Nadir point not defined!"
        raise ScalarizationError(msg)

    # define the auxiliary variable
    alpha = Variable(
        name="alpha",
        symbol="_alpha",
        variable_type=VariableTypeEnum.real,
        lowerbound=-float("Inf"),
        upperbound=float("Inf"),
        initial_value=1.0,
    )

    # calculate the weights
    weights = []
    for reference_point in reference_points:
        corrected_rp = flip_maximized_objective_values(problem, reference_point)
        if type(delta) is dict:
            weights.append(
                {
                    obj.symbol: 1 / ((nadir_point[obj.symbol] + delta[obj.symbol]) - (corrected_rp[obj.symbol]))
                    for obj in problem.objectives
                }
            )
        else:
            weights.append(
                {
                    obj.symbol: 1 / ((nadir_point[obj.symbol] + delta) - (corrected_rp[obj.symbol]))
                    for obj in problem.objectives
                }
            )

    # form the max term
    con_terms = []
    for i in range(len(reference_points)):
        corrected_rp = flip_maximized_objective_values(problem, reference_points[i])
        rp = {}
        for obj in problem.objectives:
            if type(delta) is dict:
                rp[obj.symbol] = (
                    f"{weights[i][obj.symbol]} * ({obj.symbol}_min - {nadir_point[obj.symbol] + delta[obj.symbol]}) - _alpha"
                )
            else:
                rp[obj.symbol] = (
                    f"{weights[i][obj.symbol]} * ({obj.symbol}_min - {nadir_point[obj.symbol] + delta}) - _alpha"
                )
        con_terms.append(rp)

    # form the augmentation term
    aug_exprs = []
    for i in range(len(reference_points)):
        aug_expr = " + ".join([f"({weights[i][obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
        aug_exprs.append(aug_expr)
    aug_exprs = " + ".join(aug_exprs)

    constraints = []
    # loop to create a constraint for every objective of every reference point given
    for i in range(len(reference_points)):
        for obj in problem.objectives:
            # since we are subtracting a constant value, the linearity, convexity,
            # and differentiability of the objective function, and hence the
            # constraint, should not change.
            constraints.append(
                Constraint(
                    name=f"Constraint for {obj.symbol}",
                    symbol=f"{obj.symbol}_con_{i + 1}",
                    func=con_terms[i][obj.symbol],
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=obj.is_linear,
                    is_convex=obj.is_convex,
                    is_twice_differentiable=obj.is_twice_differentiable,
                )
            )
    #  get corrected bounds if exist
    if agg_bounds is not None:
        bounds = flip_maximized_objective_values(problem, agg_bounds)
        for obj in problem.objectives:
            expr = f"({obj.symbol}_min - {bounds[obj.symbol]} - _alpha)"
            constraints.append(
                Constraint(
                    name=f"Constraint bound for {obj.symbol}",
                    symbol=f"{obj.symbol}_con",
                    func=expr,
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=obj.is_linear,
                    is_convex=obj.is_convex,
                    is_twice_differentiable=obj.is_twice_differentiable,
                )
            )
    func = f"_alpha + {rho}*({aug_exprs})"
    scalarization = ScalarizationFunction(
        name="Differentiable GUESS scalarization objective function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=problem.is_twice_differentiable,
    )
    _problem = problem.add_variables([alpha])
    _problem = _problem.add_scalarization(scalarization)
    return _problem.add_constraints(constraints), symbol


def add_group_guess_agg_diff(
    problem: Problem,
    symbol: str,
    agg_aspirations: dict[str, float],
    agg_bounds: dict[str, float] | None = None,
    delta: dict[str, float] | float = 1e-6,
    nadir: dict[str, float] | None = None,
    rho: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Adds the differentiable variant of the multiple decision maker variant of the GUESS scalarizing function.

    Both aggregated aspiration levels (min aspirations) and agg bounds (max bounds) are required.
    The scalarization function is defined as follows:

    \begin{align}
        &\mbox{minimize} &&\alpha +
        \rho \sum^k_{i=1} \sum^{n_d}_{d=1} w_{id}f_{id}(\mathbf{x}) \\
        &\mbox{subject to} && w_{id}(f_{id}(\mathbf{x})-z^{nad}_{id}) - \alpha \leq 0,\\
        &&&\mathbf{x} \in \mathbf{X},
    \end{align}

    where $w_{id} = \frac{1}{z^{nad}_{id} - \overline{z}_{id}}$.

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_points (list[dict[str, float]]): a list of dicts with keys corresponding to objective
            function symbols and values to reference point components, i.e.,
            aspiration levels.
        nadir (dict[str, float], optional): nadir point values. If not given, attempt will be made
            to calculate nadir point from problem.
        agg_bounds dict[str, float]: a dictionary of bounds not to violate.
        rho (float, optional): a small scalar value to scale the sum in the objective
            function of the scalarization. Defaults to 1e-6.
        delta (float, optional): a small scalar to define the utopian point. Defaults to 1e-6.

    Raises:
        ScalarizationError: there are missing elements in any reference point.

    Returns:
        tuple[Problem, str]: a tuple with the copy of the problem with the added
            scalarization and the symbol of the added scalarization.
    """

    # check if nadir point is specified
    # if not specified, try to calculate corrected nadir point
    if nadir is not None:
        nadir_point = nadir
    elif problem.get_nadir_point() is not None:
        nadir_point = get_corrected_nadir(problem)
    else:
        msg = "Nadir point not defined!"
        raise ScalarizationError(msg)

    # define the auxiliary variable
    alpha = Variable(
        name="alpha",
        symbol="_alpha",
        variable_type=VariableTypeEnum.real,
        lowerbound=-float("Inf"),
        upperbound=float("Inf"),
        initial_value=1.0,
    )

    # Correct the aspirations and hard_constraints
    agg_aspirations = flip_maximized_objective_values(problem, agg_aspirations)

    # calculate the weights
    weights = None
    if type(delta) is dict:
        weights = {
            obj.symbol: 1 / ((nadir_point[obj.symbol] + delta[obj.symbol]) - (agg_aspirations[obj.symbol]))
            for obj in problem.objectives
        }
    else:
        weights = {
            obj.symbol: 1 / ((nadir_point[obj.symbol] + delta) - (agg_aspirations[obj.symbol]))
            for obj in problem.objectives
        }

    # form the max term
    con_terms = []
    for obj in problem.objectives:
        if type(delta) is dict:
            con_terms.append(
                f"{weights[obj.symbol]} * ({obj.symbol}_min - {nadir_point[obj.symbol] + delta[obj.symbol]}) - _alpha"
            )
        else:
            con_terms.append(f"{weights[obj.symbol]} * ({obj.symbol}_min - {nadir_point[obj.symbol] + delta}) - _alpha")

    # form the augmentation term
    aug_exprs = []
    aug_expr = " + ".join([f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives])
    aug_exprs.append(aug_expr)
    aug_exprs = " + ".join(aug_exprs)

    constraints = []
    # loop to create a constraint for every objective of every reference point given
    for obj in problem.objectives:
        expr = (
            f"({obj.symbol}_min - {nadir_point[obj.symbol]}) / "
            f"({nadir_point[obj.symbol]} - {agg_aspirations[obj.symbol]}) - _alpha"
        )
        constraints.append(
            Constraint(
                name=f"Constraint for {obj.symbol}",
                symbol=f"{obj.symbol}_maxcon",
                func=expr,
                cons_type=ConstraintTypeEnum.LTE,
                is_linear=obj.is_linear,
                is_convex=obj.is_convex,
                is_twice_differentiable=obj.is_twice_differentiable,
            )
        )
    #  get corrected bounds if exist
    if agg_bounds is not None:
        bounds = flip_maximized_objective_values(problem, agg_bounds)
        for obj in problem.objectives:
            expr = f"({obj.symbol}_min - {bounds[obj.symbol]} - _alpha)"
            constraints.append(
                Constraint(
                    name=f"Constraint bound for {obj.symbol}",
                    symbol=f"{obj.symbol}_con",
                    func=expr,
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=obj.is_linear,
                    is_convex=obj.is_convex,
                    is_twice_differentiable=obj.is_twice_differentiable,
                )
            )
    func = f"_alpha + {rho}*({aug_exprs})"
    scalarization = ScalarizationFunction(
        name="Differentiable GUESS scalarization objective function for multiple decision makers",
        symbol=symbol,
        func=func,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=problem.is_twice_differentiable,
    )
    _problem = problem.add_variables([alpha])
    _problem = _problem.add_scalarization(scalarization)
    return _problem.add_constraints(constraints), symbol


def add_group_scenario_sf_nondiff(
    problem: Problem,
    symbol: str,
    reference_points: list[dict[str, float]],
    weights: list[dict[str, float]],
    epsilon: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Add the non-differentiable scenario based scalarization function.

    Add the following scalarization function:
    \begin{align}
      \min_{\mathbf{x}}\quad
        &\max_{i,p}\bigl[w_{ip}\bigl(f_{ip}(\mathbf{x}) - \bar z_{ip}\bigr)\bigr]
        \;+\;\varepsilon \sum_{i,p} w_{ip}\bigl(f_{ip}(\mathbf{x}) - \bar z_{ip}\bigr) \\[6pt]
      \text{s.t.}\quad
        &\mathbf{x} \in \mathcal{X}\,,
    \end{align}

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_points (list[dict[str, float]]): a list of reference points as objective dicts.
            function symbols and values to reference point components, i.e., aspiration levels.
        weights (list[dict[str, float]]): the list of weights to be used in the scalarization function.
            Must be positive.
        epsilon: small augmentation multiplier ε

    Returns:
        tuple[Problem, str]: A tuple containing a copy of the problem with the scalarization function added,
            and the symbol of the added scalarization function.
    """
    if len(reference_points) != len(weights):
        raise ScalarizationError("reference_points and weights must have same length")

    for reference_point, weight in zip(reference_points, weights, strict=True):
        if not objective_dict_has_all_symbols(problem, reference_point):
            raise ScalarizationError(
                f"The give reference point {reference_point} is missing value for one or more objectives."
            )
        if not objective_dict_has_all_symbols(problem, weight):
            raise ScalarizationError(f"The given weight vector {weight} is missing a value for one or more objectives.")

    max_list: list[str] = []
    sum_list: list[str] = []
    for reference_point, weight in zip(reference_points, weights, strict=True):
        corrected_ref_point = flip_maximized_objective_values(problem, reference_point)

        for obj in problem.objectives:
            expr = f"{weight[obj.symbol]}*({obj.symbol}_min - {corrected_ref_point[obj.symbol]})"
            max_list.append(expr)
            sum_list.append(expr)

    max_part = f"{Op.MAX}({', '.join(max_list)})"
    sum_part = " + ".join(sum_list)
    func = f"{max_part} + {epsilon}*({sum_part})"

    scalar = ScalarizationFunction(
        name="Group non differentiable scalarization function for scenario based problems.",
        symbol=symbol,
        func=func,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=problem.is_twice_differentiable,
    )
    return problem.add_scalarization(scalar), symbol


def add_group_scenario_sf_diff(
    problem: Problem,
    symbol: str,
    reference_points: list[dict[str, float]],
    weights: list[dict[str, float]],
    epsilon: float = 1e-6,
) -> tuple[Problem, str]:
    r"""Add the differentiable scenario-based scalarization.

    Adds the following scalarization function:
    \begin{align}
      \min_{x,\alpha}\quad
        & \alpha \;+\; \varepsilon \sum_{i,p} w_{ip}\bigl(f_{ip}(x) - \bar z_{ip}\bigr) \\
      \text{s.t.}\quad
        & w_{ip}\bigl(f_{ip}(x) - \bar z_{ip}\bigr)\;-\;\alpha \;\le\;0
          \quad\forall\,i,p,\\
        & x \in \mathcal{X}\,,
    \end{align}

    Args:
        problem (Problem): the problem the scalarization is added to.
        symbol (str): the symbol given to the added scalarization.
        reference_points (list[dict[str, float]]): a list of reference points as objective dicts.
            function symbols and values to reference point components, i.e., aspiration levels.
        weights (list[dict[str, float]]): the list of weights to be used in the scalarization function.
            Must be positive.
        epsilon: small augmentation multiplier ε

    Returns:
        tuple[Problem, str]: A tuple containing a copy of the problem with the scalarization function added,
            and the symbol of the added scalarization function.
    """
    if len(reference_points) != len(weights):
        raise ScalarizationError("reference_points and weights must have same length")

    for idx, (ref_point, weight) in enumerate(zip(reference_points, weights, strict=True)):
        if not objective_dict_has_all_symbols(problem, ref_point):
            raise ScalarizationError(f"reference_points[{idx}] missing some objectives")
        if not objective_dict_has_all_symbols(problem, weight):
            raise ScalarizationError(f"weights[{idx}] missing some objectives")

    alpha = Variable(
        name="alpha",
        symbol="_alpha",
        variable_type=VariableTypeEnum.real,
        lowerbound=-float("Inf"),
        upperbound=float("Inf"),
        initial_value=0.0,
    )

    sum_list = []
    constraints = []

    for idx, (ref_point, weight) in enumerate(zip(reference_points, weights, strict=True)):
        corrected_rp = flip_maximized_objective_values(problem, ref_point)
        for obj in problem.objectives:
            expr = f"{weight[obj.symbol]}*({obj.symbol}_min - {corrected_rp[obj.symbol]})"
            sum_list.append(expr)

            constraints.append(
                Constraint(
                    name=f"ssf_con_{obj.symbol}",
                    symbol=f"{obj.symbol}_con_{idx}",
                    func=f"{expr} - {alpha.symbol}",
                    cons_type=ConstraintTypeEnum.LTE,
                    is_linear=obj.is_linear,
                    is_convex=obj.is_convex,
                    is_twice_differentiable=obj.is_twice_differentiable,
                )
            )

    sum_part = " + ".join(sum_list)

    func = f"_alpha + {epsilon}*({sum_part})"
    scalar = ScalarizationFunction(
        name="Scenario-based differentiable ASF",
        symbol=symbol,
        func=func,
        is_linear=problem.is_linear,
        is_convex=problem.is_convex,
        is_twice_differentiable=problem.is_twice_differentiable,
    )

    problem_ = problem.add_variables([alpha])
    problem_ = problem_.add_constraints(constraints)
    problem_ = problem_.add_scalarization(scalar)

    return problem_, symbol
