"""Implements a provider for the test problems found in Pymoo."""

import json
from functools import lru_cache
from typing import Any

import numpy as np
from pydantic import BaseModel, Field
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

pymoo_locator_evaluate = "desdeo://external/pymoo/evaluate"


class PymooParams(BaseModel):
    name: str = Field(description="The name of the model. See https://pymoo.org/problems/test_problems.html")
    n_var: int | None = Field(description="The number of desirable variables (if relevant).", default=None)
    n_obj: int | None = Field(description="The number of desirable objective functions (if relevant).", default=None)
    extra: dict[str, Any] | None = Field(description="Any other extra parameters.", default=None)


# TODO: move to core
class ExternalProblemInfo(BaseModel):
    name: str = Field(description="Name of the problem")
    description: str | None = Field(description="Description of the problem. Default to 'None'.", default=None)
    variable_symbols: list[str] = Field(description="The symbols of the variables.")
    variable_names: dict[str, str] | None = Field(
        description=(
            "The names of the variables. It is expected that the keys are the same as the provided symbols. "
            "Defaults to 'None', in which case the symbols are used."
        )
    )
    variable_type: dict[str, VariableTypeEnum] | None = Field(
        description=(
            "The type of each variable (real, integer, binary). It is "
            "expected that the keys are the same as the provided symbols. If 'None', "
            "the type 'real' is assumed for all variables. Defaults to 'None'."
        )
    )
    variable_lower_bounds: dict[str, VariableType | None] | None = Field(
        description=(
            "The lower bound of each variable. It is "
            "expected that the keys are the same as the provided symbols. If 'None', "
            "the value is None, no bounds are assumed for all lower bounds. variables. Defaults to 'None'."
        )
    )
    variable_upper_bounds: dict[str, VariableType | None] | None = Field(
        description=(
            "The upper bound of each variable. It is "
            "expected that the keys are the same as the provided symbols. If 'None', "
            "the value is None, no bounds are assumed for all upper bounds. variables. Defaults to 'None'."
        )
    )
    objective_symbols: list[str] = Field(description="The names of the objective functions.")
    objective_names: dict[str, str] | None = Field(
        description=(
            "The names of the objectives. It is expected that the keys are the same as the provided symbols. "
            "Defaults to 'None', in which case the symbols are used."
        )
    )
    objective_maximize: dict[str, bool] | None = Field(
        description=(
            "Whether objective are to be maximized. It is "
            "expected that the keys are the same as the provided symbols. "
            "Defaults to 'None', in which case minimization is assumed."
        )
    )
    constraint_symbols: list[str] | None = Field(
        description=(
            "The symbols of constraints. If 'None', no constraints are defined for the problem. Defaults to None."
        )
    )
    constraint_names: dict[str, str] | None = Field(
        description=(
            "The names of the constraints. It is expected that the keys are the same as the provided symbols. "
            "Defaults to 'None', in which case the symbols are used."
        )
    )
    constraint_types: dict[str, ConstraintTypeEnum] | None = Field(
        description=(
            "The types (LTE, EQ...) of the constraints. It is expected that the "
            "keys are the same as the provided symbols. Defaults to 'None', in "
            "which case no symbols are assumed to be defined."
        )
    )


def _stable_json(d: dict[str, Any]) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _params_key(params: PymooParams) -> str:
    """Canonical cache key for a PymooParams instance.

    Canonical cache key for a PymooParams instance.
    Includes 'extra' (if present) and omits None fields.
    """
    return _stable_json(params.model_dump(exclude_none=True))


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
        constraint_symbols=constr_symbols,
        constraint_names=dict(zip(constr_symbols, constr_symbols, strict=True)) if constr_symbols is not None else None,
        constraint_types=dict(zip(constr_symbols, constr_types, strict=True)) if len(constr_types) > 0 else None,
    )


class PymooProvider:
    def info(self, params: PymooParams) -> ExternalProblemInfo:
        return _get_cached_info(_params_key(params))

    def evaluate(self, xs: list[list[float]], params: PymooParams) -> dict[str, Any]:
        # TODO: return type
        params_key = _params_key(params)
        problem = _get_cached_pymoo_problem(params_key)
        info = _get_cached_info(params_key)

        out = {"F": None, "G": None, "H": None}
        problem._evaluate(np.asarray(xs, dtype=float), out)

        # parse output
        obj_results = dict(zip(info.objective_symbols, out["F"].tolist(), strict=True))
        _constrs = (np.atleast_2d(out["G"]).tolist() if out["G"] is not None else []) + (
            np.atleast_2d(out["H"]).tolist() if out["H"] is not None else []
        )
        constr_results = dict(zip(info.constraint_symbols, _constrs, strict=True)) if len(_constrs) > 0 else None

        return obj_results | constr_results


def create_pymoo_problem(params: PymooParams) -> Problem:
    provider = PymooProvider()
    info = provider.info(params)

    simulator_url = Url(url=pymoo_locator_evaluate)

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

    return Problem(
        name=info.name,
        description=info.description,
        variables=variables,
        objectives=objectives,
        constraints=constraints if len(constraints) > 0 else None,
        simulators=[simulator],
    )
