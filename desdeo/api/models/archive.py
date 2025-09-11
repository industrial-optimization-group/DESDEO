"""Defines models for archiving solutions."""

from sqlmodel import Field

from desdeo.tools.generics import EMOResults


class UserSavedEMOResults(EMOResults):
    """Defines a schema for storing emo solutions."""

    name: str | None = Field(
        description="An optional name for the solution, useful for archiving purposes.",
        default=None,
    )

    def to_emo_results(self) -> EMOResults:
        """Convert to SolverResults without the name field."""
        return EMOResults(
            optimal_variables=self.optimal_variables,
            optimal_objectives=self.optimal_objectives,
            constraint_values=self.constraint_values,
            extra_func_values=self.extra_func_values,
        )
