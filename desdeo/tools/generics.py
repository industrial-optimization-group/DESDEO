"""Defines generic classes, functions, and objects utilized in the tools module."""
from typing import Callable, TypeVar

from pydantic import BaseModel, Field

from desdeo.problem import Problem, Constraint, Objective, ScalarizationFunction, Variable


class SolverError(Exception):
    """Raised when an error with a solver is encountered."""


class SolverResults(BaseModel):
    """Defines a schema for a dataclass to store the results of a solver."""

    optimal_variables: dict[str, float | list[float]] = Field(description="The optimal decision variables found.")
    optimal_objectives: dict[str, float | list[float]] = Field(
        description="The objective function values corresponding to the optimal decision variables found."
    )
    constraint_values: dict[str, float | list[float]] | None = Field(
        description=(
            "The constraint values of the problem. A negative value means the constraint is respected, "
            "a positive one means it has been breached."
        ),
        default=None,
    )
    success: bool = Field(description="A boolean flag indicating whether the optimization was successful or not.")
    message: str = Field(description="Description of the cause of termination.")

class PersistentSolver(BaseModel):
    """Defines a schema for a persistent solver class, that can be used when reinitializing 
    the solver every time the problem is changed is not practical."""
    evaluator: object = Field(description="The evaluator used by the solver.")
    problem: Problem = Field(description="The problem associated with the solver")

    def __init__(self, problem: Problem, options: dict[str,any]):
        """Initializer for the persistent solver
        
        Args:
            problem (Problem): The problem for the solver.
            options (dict[str,any]): Dictionary of parameters to set.
                What these should be depends on the solver used.
        """
        self.problem = problem

    def addConstraint(self, constraint: Constraint):
        """Add a constraint expression to the solver.

        Args:
            constraint (Constraint): the constraint function expression.
        """
        pass
    
    def addObjective(self, objective: Objective):
        """Adds an objective function expression to the solver.

        Args:
            objectve (Objective): an objective function expression to be added.
        """
        pass

    def addScalarizationFunction(self, scal: ScalarizationFunction):
        """Adds a scalrization expression to the solver.

        Args:
            scalarization (ScalarizationFunction): A scalarization function to be added.
        """
        pass

    def addVariable(self, variable: Variable):
        """Add a variable to the solver.

        Args:
            variable (Variable): The definition of the variable to be added.
        """
        pass

    def removeConstraint(self, symbol: str):
        """Removes a constraint from the solver.
        
        Args:
            symbol (str): a str representing the symbol of the constraint to be removed.
        """
        pass

    def removeVariable(self, symbol: str):
        """Removes a variable from the model.
        
        Args:
            symbol (str): a str representing the symbol of the variable to be removed.
        """
        pass

    def solve(self, target: str) -> SolverResults:
        """Solves the current problem with the specified target.

        Args:
            target (str): a str representing the symbol of the target function.
        
        Returns:
            SolverResults: The results of the solver
        """
        pass


Kwargs = TypeVar("Kwargs", bound=dict)
CreateSolverType = Callable[[Problem, Kwargs], Callable[[str], SolverResults]]
