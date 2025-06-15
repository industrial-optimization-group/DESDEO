"""Defines generic classes, functions, and objects utilized in the tools module."""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel, Field

from desdeo.problem import (
    Constraint,
    Objective,
    Problem,
    ScalarizationFunction,
    Variable,
)


class SolverError(Exception):
    """Raised when an error with a solver is encountered."""


class SolverResults(BaseModel):
    """Defines a schema for a dataclass to store the results of a solver."""

    optimal_variables: dict[str, int | float | list] = Field(description="The optimal decision variables found.")
    optimal_objectives: dict[str, float | list[float]] = Field(
        description="The objective function values corresponding to the optimal decision variables found."
    )
    constraint_values: dict[str, float | int | list[float] | list] | None | Any = Field(
        description=(
            "The constraint values of the problem. A negative value means the constraint is respected, "
            "a positive one means it has been breached."
        ),
        default=None,
    )
    extra_func_values: dict[str, float | list[float]] | None = Field(
        description=("The extra function values of the problem."), default=None
    )
    scalarization_values: dict[str, float | list[float]] | None = Field(
        description=("The scalarization function values of the problem."), default=None
    )
    success: bool = Field(description="A boolean flag indicating whether the optimization was successful or not.")
    message: str = Field(description="Description of the cause of termination.")

class UserSavedSolverResults(SolverResults):
    """Defines a schema for storing archived solutions."""
    name: str | None = Field(
        description="An optional name for the solution, useful for archiving purposes.", default=None
    )

    def to_solver_results(self) -> SolverResults:
        """Convert to SolverResults without the name field."""
        return SolverResults(
            optimal_variables=self.optimal_variables,
            optimal_objectives=self.optimal_objectives,
            constraint_values=self.constraint_values,
            extra_func_values=self.extra_func_values,
            scalarization_values=self.scalarization_values,
            success=self.success,
            message=self.message,
        )

class BaseSolver(ABC):
    """Defines a schema for a solver base class."""

    evaluator: object
    problem: Problem

    def __init__(self, problem: Problem, options: dict[str, any] | None = None):
        """Initializer for the persistent solver.

        Args:
            problem (Problem): The problem for the solver.
            options (dict[str,any]): Dictionary of parameters to set.
                What these should be depends on the solver used.
        """
        self.problem = problem

    @abstractmethod
    def solve(self, target: str) -> SolverResults:
        """Solves the current problem with the specified target.

        Args:
            target (str): a str representing the symbol of the target function.

        Returns:
            SolverResults: The results of the solver
        """


class PersistentSolver:
    """Defines a schema for a persistent solver class.

    Can be used when reinitializing the solver every time the problem is changed is not practical.
    """

    evaluator: object
    problem: Problem

    def __init__(self, problem: Problem, options: dict[str, any] | None = None):
        """Initializer for the persistent solver.

        Args:
            problem (Problem): The problem for the solver.
            options (dict[str,any]): Dictionary of parameters to set.
                What these should be depends on the solver used.
        """
        self.problem = problem

    def add_constraint(self, constraint: Constraint | list[Constraint]):
        """Add a constraint expression to the solver.

        Args:
            constraint (Constraint): the constraint function expression.
        """

    def add_objective(self, objective: Objective):
        """Adds an objective function expression to the solver.

        Args:
            objective (Objective): an objective function expression to be added.
        """

    def add_scalarization_function(self, scalarization: ScalarizationFunction):
        """Adds a scalrization expression to the solver.

        Args:
            scalarization (ScalarizationFunction): A scalarization function to be added.
        """

    def add_variable(self, variable: Variable):
        """Add a variable to the solver.

        Args:
            variable (Variable): The definition of the variable to be added.
        """

    def remove_constraint(self, symbol: str):
        """Removes a constraint from the solver.

        Args:
            symbol (str): a str representing the symbol of the constraint to be removed.
        """

    def remove_variable(self, symbol: str):
        """Removes a variable from the model.

        Args:
            symbol (str): a str representing the symbol of the variable to be removed.
        """

    def solve(self, target: str) -> SolverResults:
        """Solves the current problem with the specified target.

        Args:
            target (str): a str representing the symbol of the target function.

        Returns:
            SolverResults: The results of the solver
        """


SolverOptions = TypeVar("SolverOptions", bound=Any)
