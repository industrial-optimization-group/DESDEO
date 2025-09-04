"""Defines solver interfaces for gurobipy."""

import gurobipy as gp
from pydantic import BaseModel, Field, ConfigDict

from desdeo.problem import (
    Constraint,
    GurobipyEvaluator,
    Objective,
    Problem,
    ScalarizationFunction,
    TensorVariable,
    Variable,
)
from desdeo.tools.generics import BaseSolver, PersistentSolver, SolverResults


class GurobipyOptions(BaseModel):
    """Defines a pydantic model to store and pass options to the Gurobipy solvers.

    For available parameters see https://www.gurobi.com/documentation/current/refman/parameters.html

    Options with value None will be omitted, and won't be passed to the solver.

    Note:
        Not all options are available through this model.
        Please add options as they are needed and make a pull request.
    """
    model_config = ConfigDict(extra='forbid')

    time_limit: int = Field(
        description="The maximum amount of time (in seconds) the solver should run. Defaults to None.", default=None
    )
    """The maximum amount of time (in seconds) the solver should run. Defaults to None."""
    threads: int = Field(
        description="The number of threads used for solving the problem. 0 means automatic. Defaults to 0", default=0
    )
    """The number of threads used for solving the problem. 0 means automatic. Defaults to 0"""
    cutoff: float = Field(
        description="Omits the solutions that are worse than the specified value. Deafaults to None", default=None
    )
    """Omits the solutions that are worse than the specified value. Deafaults to None"""
    feasibility_tol: float = Field(
        description="Sets the feasibility tolerance for constraints. Defaults to 1e-6.", default=1e-6
    )
    """Sets the feasibility tolerance for constraints. Defaults to 1e-6."""
    int_feas_tol: float = Field(
        description="Sets the tolerance for integrality of integer variables. Defaults to 1e-5.", default=1e-5
    )
    """Sets the tolerance for integrality of integer variables. Defaults to 1e-5."""
    solution_limit: int = Field(
        description="Limits the number of feasible solutions found by the solver. Defaults to None", default=None
    )
    """Limits the number of feasible solutions found by the solver. Defaults to None"""
    presolve: int = Field(
        description=(
            "Controls the presolve level (-1: automatic, 0: no presolve, 1: default, 2: aggressive). Defaults to -1."
        ),
        default=-1
    )
    """Controls the presolve level (-1: automatic, 0: no presolve, 1: default, 2: aggressive). Defaults to -1."""


_default_gurobipy_options = GurobipyOptions()
"""Defines Gurobipy options with default values."""


def parse_gurobipy_optimizer_results(problem: Problem, evaluator: GurobipyEvaluator) -> SolverResults:
    """Parses results from GurobipyEvaluator's model into DESDEO SolverResults.

    Args:
        problem (Problem): the problem being solved.
        evaluator (GurobipyEvaluator): the evaluator utilized to solve the problem.

    Returns:
        SolverResults: DESDEO solver results.
    """
    results = evaluator.get_values()

    variable_values = {var.symbol: results[var.symbol] for var in problem.variables}
    objective_values = {obj.symbol: results[obj.symbol] for obj in problem.objectives}
    constraint_values = (
        {con.symbol: results[con.symbol] for con in problem.constraints} if problem.constraints is not None else None
    )
    extra_func_values = (
        {extra.symbol: results[extra.symbol] for extra in problem.extra_funcs}
        if problem.extra_funcs is not None
        else None
    )
    scalarization_values = (
        {scal.symbol: results[scal.symbol] for scal in problem.scalarization_funcs}
        if problem.scalarization_funcs is not None
        else None
    )
    success = evaluator.model.status == gp.GRB.OPTIMAL
    if evaluator.model.status == gp.GRB.OPTIMAL:
        status = "Optimal solution found."
    elif evaluator.model.status == gp.GRB.INFEASIBLE:
        status = "Model is infeasible."
    elif evaluator.model.status == gp.GRB.UNBOUNDED:
        status = "Model is unbounded."
    elif evaluator.model.status == gp.GRB.INF_OR_UNBD:
        status = "Model is either infeasible or unbounded."
    else:
        status = f"Optimization ended with status: {evaluator.model.status}"
    msg = f"Gurobipy solver status is: '{status}'"

    return SolverResults(
        optimal_variables=variable_values,
        optimal_objectives=objective_values,
        constraint_values=constraint_values,
        extra_func_values=extra_func_values,
        scalarization_values=scalarization_values,
        success=success,
        message=msg,
    )


class GurobipySolver(BaseSolver):
    """Creates a gurobipy solver that utilizes gurobi's own Python implementation."""

    def __init__(self, problem: Problem, options: GurobipyOptions | None = _default_gurobipy_options):
        """The solver is initialized by supplying a problem and options.

        Unlike with Pyomo you do not need to have gurobi installed on your system
        for this to work. Suitable for solving mixed-integer linear and quadratic optimization
        problems.

        Args:
            problem (Problem): the problem to be solved.
            options (GurobipyOptions, optional): Options to be passed to the Gurobipy solver.
                If `None` is passed, defaults to `_default_gurobipy_options` defined in
                this source file. Defaults to `None`.
                You probably don't need to set any of these and can just use the defaults.
                For available parameters see https://www.gurobi.com/documentation/current/refman/parameters.html
        """
        self.evaluator = GurobipyEvaluator(problem)
        self.problem = problem

        if options is None:
            options = _default_gurobipy_options
        for key, value in options:
            if value is not None:
                self.evaluator.model.setParam(key, value)

    def solve(self, target: str) -> SolverResults:
        """Solve the problem for the given target.

        Args:
            target (str): the symbol of the function to be optimized, and which is
                defined in the problem given when initializing the solver.

        Returns:
            SolverResults: the results of the optimization.
        """
        self.evaluator.set_optimization_target(target)
        self.evaluator.model.optimize()
        return parse_gurobipy_optimizer_results(self.problem, self.evaluator)


class PersistentGurobipySolver(PersistentSolver):
    """A persistent solver class utlizing gurobipy.

    Use this instead of create_gurobipy_solver when re-initializing the
    solver every time the problem is changed is not practical.
    """

    evaluator: GurobipyEvaluator

    def __init__(self, problem: Problem, options: GurobipyOptions | None = _default_gurobipy_options):
        """Initializer for the persistent solver.

        Args:
            problem (Problem): the problem to be transformed in a GurobipyModel.
            options (GurobipyOptions, optional): Options to be passed to the Gurobipy solver.
                If `None` is passed, defaults to `_default_gurobipy_options` defined in
                this source file. Defaults to `None`.
                You probably don't need to set any of these and can just use the defaults.
                For available parameters see https://www.gurobi.com/documentation/current/refman/parameters.html
        """
        self.problem = problem
        self.evaluator = GurobipyEvaluator(problem)

        if options is None:
            options = _default_gurobipy_options
        for key, value in options:
            if value is not None:
                self.evaluator.model.setParam(key, value)

    def add_constraint(self, constraint: Constraint | list[Constraint]) -> gp.Constr | list[gp.Constr]:
        """Add one or more constraint expressions to the solver.

        If adding a lot of constraints or dealing with a large model, this function
        may end up being very slow compared to adding the constraints to the model
        stored in the evaluator directly.

        Args:
            constraint (Constraint): the constraint function expression or a list of
                constraint function expressions.

        Raises:
            GurobipyEvaluatorError: when an unsupported constraint type is encountered.

        Returns:
            gurobipy.Constr: The gurobipy constraint that was added or a list of gurobipy
                constraints if the constraint argument was a list.
        """
        if isinstance(constraint, list):
            cons_list = list[gp.Constr]
            for cons in constraint:
                cons_list.append(self.evaluator.add_constraint(cons))
            return cons_list

        return self.evaluator.add_constraint(constraint)

    def add_objective(self, objective: Objective | list[Objective]):
        """Adds an objective function expression to the solver.

        Does not yet add any actual gurobipy optimization objectives, only adds them to the dict
        containing the expressions of the objectives. The objective expressions are stored in the
        evaluator and the evaluator must add the appropiate gurobipy objective before solving.

        Args:
            objective (Objective): an objective function expression or a list of objective function
                expressions to be added.
        """
        if not isinstance(objective, list):
            objective = [objective]

        for obj in objective:
            self.evaluator.add_objective(obj)

    def add_scalarization_function(self, scalarization: ScalarizationFunction | list[ScalarizationFunction]):
        """Adds a scalrization expression to the solver.

        Scalarizations work identically to objectives, except they are stored in a different
        dict in the evaluator. If you want to solve the problem using a scalarization, the
        evaluator needs to set it as an optimization target first.

        Args:
            scalarization (ScalarizationFunction): A scalarization function or a list of
                scalarization functions to be added.
        """
        if not isinstance(scalarization, list):
            scalarization = [scalarization]

        for scal in scalarization:
            self.evaluator.add_scalarization_function(scal)

    def add_variable(
        self, variable: Variable | TensorVariable | list[Variable] | list[TensorVariable]
    ) -> gp.Var | gp.MVar | list[gp.Var] | list[gp.MVar]:
        """Add one or more variables to the solver.

        If adding a lot of variables or dealing with a large model, this function
        may end up being very slow compared to adding the variables to the model
        stored in the evaluator directly.

        Args:
            variable (Variable): The definition of the variable or a list of variables to be added.

        Raises:
            GurobipyEvaluatorError: when a problem in extracting the variables is encountered.
                I.e., the variables are of a non supported type.

        Returns:
            gp.Var: the variable that was added to the model or a list of variables if
                variable argument was a list.
        """
        if isinstance(variable, list):
            var_list = list[gp.Var | gp.MVar]
            for var in variable:
                var_list.append(self.evaluator.add_variable(var))
            return var_list

        return self.evaluator.add_variable(variable)

    def remove_constraint(self, symbol: str | list[str]):
        """Removes a constraint from the solver.

        If removing a lot of constraints or dealing with a very large model this function
        may be slow because of the model.update() calls. Accessing the model stored in the
        evaluator directly may be faster.

        Args:
            symbol (str): a str representing the symbol of the constraint to be removed.
                Can also be a list of multiple symbols.
        """
        if not isinstance(symbol, list):
            symbol = [symbol]
        for s in symbol:
            self.evaluator.remove_constraint(s)

    def remove_variable(self, symbol: str | list[str]):
        """Removes a variable from the model.

        If removing a lot of variables or dealing with a very large model this function
        may be slow because of the model.update() calls. Accessing the model stored in
        the evaluator directly may be faster.

        Args:
            symbol (str): a str representing the symbol of the variable to be removed.
                Can also be a list of multiple symbols.
        """
        self.evaluator.remove_variable(symbol)

    def solve(self, target: str) -> SolverResults:
        """Solves the current problem with the specified target.

        Args:
            target (str): a str representing the symbol of the target function.

        Returns:
            SolverResults: The results of the solver
        """
        self.evaluator.set_optimization_target(target)
        self.evaluator.model.optimize()
        return parse_gurobipy_optimizer_results(self.problem, self.evaluator)
