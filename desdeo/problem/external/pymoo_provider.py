"""Implements a provider for the test problems found in Pymoo."""

import json
from functools import lru_cache
from typing import Any

import numpy as np
from pydantic import Field
from pymoo.problems import get_problem as pymoo_get_problem

from desdeo.problem import (
    Constraint,
    ConstraintTypeEnum,
    Objective,
    Problem,
    Simulator,
    Url,
    Variable,
    VariableType,
    VariableTypeEnum,
)

from .core import ExternalProblemInfo, ExternalProblemParams, Provider

_pymoo_locator_evaluate = "desdeo://external/pymoo/evaluate"


class PymooProblemParams(ExternalProblemParams):
    """Parameters to generate Pymoo test problems.

    See: https://pymoo.org/problems/test_problems.html
    """

    name: str = Field(description="The name of the model. See https://pymoo.org/problems/test_problems.html")
    n_var: int | None = Field(description="The number of desirable variables (if relevant).", default=None)
    n_obj: int | None = Field(description="The number of desirable objective functions (if relevant).", default=None)
    extra: dict[str, Any] | None = Field(description="Any other extra parameters.", default=None)


def _stable_json(d: dict[str, Any]) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _params_key(params: dict) -> str:
    """Canonical cache key for a PymooParams instance.

    Canonical cache key for a PymooParams instance.
    Includes 'extra' (if present) and omits None fields.
    """
    return _stable_json(params)


@lru_cache(maxsize=256)
def _get_cached_pymoo_problem(params_key: str):
    """Cache pymoo Problem instances by a stable JSON key.

    Note: per-process cache (fine for typical single-worker runs).
    """
    params_dict = json.loads(params_key)

    extra = params_dict.pop("extra", None)
    if isinstance(extra, dict):
        params_dict |= extra

    return pymoo_get_problem(**params_dict)


@lru_cache(maxsize=256)
def _get_cached_info(params_key: str) -> ExternalProblemInfo:
    """Cache ExternalProblemInfo too, since it derives from the cached pymoo problem."""
    pymoo_problem = _get_cached_pymoo_problem(params_key)

    p_name = pymoo_problem.name()  # why?
    p_n_var = pymoo_problem.n_var
    p_n_obj = pymoo_problem.n_obj
    p_n_ieq_constr = pymoo_problem.n_ieq_constr
    p_n_eq_constr = pymoo_problem.n_eq_constr
    p_xl = pymoo_problem.xl
    p_xu = pymoo_problem.xu
    p_vtype = pymoo_problem.vtype

    try:
        p_ideal = pymoo_problem.ideal_point()
    except Exception:
        p_ideal = None
    try:
        p_nadir = pymoo_problem.nadir_point()
    except Exception:
        p_nadir = None

    var_symbols = [f"x_{i}" for i in range(1, p_n_var + 1)]
    obj_symbols = [f"f_{i}" for i in range(1, p_n_obj + 1)]
    constr_symbols = (
        [f"c_{i}" for i in range(1, p_n_ieq_constr + p_n_eq_constr + 1)] if p_n_ieq_constr + p_n_eq_constr > 0 else None
    )
    constr_types = [ConstraintTypeEnum.LTE] * p_n_ieq_constr + [ConstraintTypeEnum.EQ] * p_n_eq_constr

    var_type_mapping = {float: VariableTypeEnum.real, int: VariableTypeEnum.integer, bool: VariableTypeEnum.binary}

    return ExternalProblemInfo(
        name=p_name,
        description=f"The {p_name} problem as defined in the Pymoo library.",
        variable_symbols=var_symbols,
        variable_names=dict(zip(var_symbols, var_symbols, strict=True)),
        variable_type=dict.fromkeys(var_symbols, var_type_mapping[p_vtype]),  # assumed all same
        variable_lower_bounds=dict(zip(var_symbols, p_xl, strict=True)),
        variable_upper_bounds=dict(zip(var_symbols, p_xu, strict=True)),
        objective_symbols=obj_symbols,
        objective_names=dict(zip(obj_symbols, obj_symbols, strict=True)),
        objective_maximize=dict.fromkeys(obj_symbols, False),  # assumed all min
        ideal_point=dict(zip(obj_symbols, p_ideal, strict=True)) if p_ideal is not None else None,
        nadir_point=dict(zip(obj_symbols, p_nadir, strict=True)) if p_nadir is not None else None,
        constraint_symbols=constr_symbols,
        constraint_names=dict(zip(constr_symbols, constr_symbols, strict=True)) if constr_symbols is not None else None,
        constraint_types=dict(zip(constr_symbols, constr_types, strict=True)) if len(constr_types) > 0 else None,
    )


class PymooProvider(Provider):
    """Provider to get info on and evaluate Pymoo test problems.

    Note:
        the methods `info` and `evaluate` use caching so that the Pymoo problem is generated only once
            in case of multiple consecutive evaluations of the same problem.
    """

    def info(self, params: PymooProblemParams | dict[str, Any]) -> ExternalProblemInfo:
        """Get info on a Pymoo test problem.

        Args:
            params (PymooProblemParams | dict[str, Any]): parameters to generate the problem.

        Returns:
            ExternalProblemInfo: info on the problem generated based on the provided parameters.
        """
        return _get_cached_info(_params_key(params if isinstance(params, dict) else params.model_dump()))

    def evaluate(
        self, xs: dict[str, VariableType | list[VariableType]], params: PymooProblemParams | dict[str, Any]
    ) -> dict[str, float]:
        """Evaluate a Pymoo test problem.

        Args:
            xs (dict[str, VariableType]): a set of variables to be evaluated.
                Expected format is {variable symbol: [values]}.
            params (ProviderParams | dict[str, Any]): parameters that generate the problem Pymoo
                problem to be evaluated.

        Returns:
            dict[str, float]: a dict with keys corresponding to evaluated fields of the problem, e.g.,
                objective functions, constraints, etc., and values consisting of lists.

        Note:
            When multiple values are provided for the variables, it is assumed that
            the external problem is evaluated pointwise and that the returned values
            correspond to the input values in the same order.
        """
        params_key = _params_key(params if isinstance(params, dict) else params.model_dump())
        problem = _get_cached_pymoo_problem(params_key)
        info = _get_cached_info(params_key)

        out = {"F": None, "G": None, "H": None}

        xs_arr = np.atleast_2d(np.column_stack([xs[k] for k in info.variable_symbols]))
        problem._evaluate(np.asarray(xs_arr, dtype=float), out)

        # parse output
        obj_results = dict(zip(info.objective_symbols, out["F"].squeeze().T.tolist(), strict=True))
        _constrs = (np.atleast_2d(out["G"]).tolist() if out["G"] is not None else []) + (
            np.atleast_2d(out["H"]).tolist() if out["H"] is not None else []
        )
        constr_results = dict(zip(info.constraint_symbols, _constrs, strict=True)) if len(_constrs) > 0 else {}

        return obj_results | constr_results


def create_pymoo_problem(params: PymooProblemParams) -> Problem:
    """Create a Pymoo test problem based on given parameters.

    Args:
        params (PymooProblemParams): the parameters to generate the Pymoo test problem.

    Returns:
        Problem: an instance of a Pymoo test problem generated based on the given parameters.

    Note:
        Any `Problem` generated with this function should be considered to be black-box, i.e.,
        the exact mathematical forms are not available. However, if the user is knowledgeable
        about the properties of the problem, they can still use, for example, some gradient-based
        solvers available in DESDEO to try and solve the problem, if the problem is differentiable.

        Ideal and nadir point values will be available, if they are available in Pymoo for a given problem.

        For info on the possible problems to generate, see https://pymoo.org/problems/test_problems.html
    """
    provider = PymooProvider()
    info = provider.info(params)

    simulator_url = Url(url=_pymoo_locator_evaluate)

    variables: list[Variable] = []
    for sym in info.variable_symbols:
        v_name = info.variable_names[sym] if info.variable_names is not None else sym
        v_type = info.variable_type[sym] if info.variable_type is not None else VariableTypeEnum.real
        lb = info.variable_lower_bounds[sym] if info.variable_lower_bounds is not None else None
        ub = info.variable_upper_bounds[sym] if info.variable_upper_bounds is not None else None

        variables.append(
            Variable(
                name=v_name,
                symbol=sym,
                lowerbound=lb,
                upperbound=ub,
                variable_type=v_type,
            )
        )

    objectives: list[Objective] = []
    for sym in info.objective_symbols:
        o_name = info.objective_names[sym] if info.objective_names is not None else sym
        maximize = info.objective_maximize[sym] if info.objective_maximize is not None else False

        objectives.append(
            Objective(
                name=o_name,
                symbol=sym,
                simulator_path=simulator_url,
                objective_type="simulator",
                maximize=maximize,
            )
        )

    # Constraints (optional)
    constraints: list[Constraint] = []
    if info.constraint_symbols is not None and len(info.constraint_symbols) > 0:
        for sym in info.constraint_symbols:
            c_name = info.constraint_names[sym] if info.constraint_names is not None else sym
            c_type = info.constraint_types[sym] if info.constraint_types is not None else ConstraintTypeEnum.LTE

            constraints.append(
                Constraint(
                    name=c_name,
                    symbol=sym,
                    simulator_path=simulator_url,
                    constraint_type=c_type,
                )
            )

    simulator = Simulator(
        name="pymoo_sim",
        symbol="pymoo_sim",
        url=simulator_url,
        parameter_options=params.model_dump(exclude_none=True),
    )

    problem = Problem(
        name=info.name,
        description=info.description,
        variables=variables,
        objectives=objectives,
        constraints=constraints if len(constraints) > 0 else None,
        simulators=[simulator],
    )

    # add ideal and nadir (might be None)
    return problem.update_ideal_and_nadir(info.ideal_point, info.nadir_point)
