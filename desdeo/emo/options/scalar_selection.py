"""JSON Schema for scalar selector operator options."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from desdeo.emo.operators.scalar_selection import BaseScalarSelector, ElitistSelection, TournamentSelection

if TYPE_CHECKING:
    from desdeo.problem import Problem
    from desdeo.tools.patterns import Publisher


class TournamentSelectionOptions(BaseModel):
    """Options for tournament selection operator."""

    name: Literal["TournamentSelection"] = Field(
        default="TournamentSelection", frozen=True, description="The name of the scalar selection operator."
    )
    """The name of the scalar selection operator."""
    tournament_size: int = Field(
        default=2,
        description="The number of individuals participating in the tournament.",
    )
    """The number of individuals participating in the tournament."""
    winner_size: int = Field(
        gt=1,
        description="The number of winners to select (equivalent to population size).",
    )
    """The number of winners to select (equivalent to population size)."""
    comparison: Literal["fitness", "dominance"] = Field(
        default="fitness",
        description=(
            "How the members of a tournament are compared. 'fitness' picks the highest fitness the selector "
            "publishes. 'dominance' picks uniformly among the members no other member dominates, under "
            "constrained domination, and ignores the fitness."
        ),
    )
    """How the members of a tournament are compared. 'fitness' picks the highest fitness the selector publishes.
    'dominance' picks uniformly among the members no other member dominates, under constrained domination, and
    ignores the fitness."""


class RouletteWheelSelectionOptions(TournamentSelectionOptions):
    """Options for roulette wheel selection operator."""

    name: Literal["RouletteWheelSelection"] = Field(
        default="RouletteWheelSelection", frozen=True, description="The name of the scalar selection operator."
    )
    """The name of the scalar selection operator."""
    comparison: Literal["fitness"] = Field(  # type: ignore[assignment]
        default="fitness",
        description="A roulette wheel draws the winner in proportion to fitness, so it only compares by fitness.",
    )
    """A roulette wheel draws the winner in proportion to fitness, so it only compares by fitness."""


class ElitistSelectionOptions(BaseModel):
    """Options for elitist scalar selection (top ``winner_size`` by a target column)."""

    name: Literal["ElitistSelection"] = Field(
        default="ElitistSelection", frozen=True, description="The name of the scalar selection operator."
    )
    """The name of the scalar selection operator."""
    winner_size: int = Field(gt=0, description="The number of individuals to keep after selection.")
    """The number of individuals to keep after selection."""
    target_column: str = Field(description="Name of the output column to sort by (ascending, lower is better).")
    """Name of the output column to sort by (ascending, lower is better)."""


ScalarSelectionOptions = TournamentSelectionOptions | RouletteWheelSelectionOptions | ElitistSelectionOptions


def scalar_selector_constructor(
    options: ScalarSelectionOptions,
    seed: int,
    publisher: Publisher,
    verbosity: int,
    problem: Problem | None = None,
) -> BaseScalarSelector:
    """Construct a scalar selector operator based on the provided options.

    Args:
        options (ScalarSelectionOptions): The options of the operator.
        seed (int): The seed of the operator's random number generator.
        publisher (Publisher): The publisher the operator subscribes to.
        verbosity (int): The verbosity of the operator's messages.
        problem (Problem | None, optional): The problem being solved. A tournament that compares by dominance
            reads its targets and constraints from it. Defaults to None.

    Returns:
        BaseScalarSelector: The operator.

    Raises:
        ValueError: If the operator is unknown, or if a dominance tournament is asked for without a problem.
    """
    if options.name == "TournamentSelection":
        if options.comparison == "dominance":
            if problem is None:
                raise ValueError("A tournament that compares by dominance needs the problem to read its targets.")
            return TournamentSelection(
                tournament_size=options.tournament_size,
                winner_size=options.winner_size,
                seed=seed,
                publisher=publisher,
                verbosity=verbosity,
                comparison="dominance",
                target_symbols=[f"{obj.symbol}_min" for obj in problem.objectives],
                constraint_symbols=[con.symbol for con in problem.constraints] if problem.constraints else None,
            )
        return TournamentSelection(
            tournament_size=options.tournament_size,
            winner_size=options.winner_size,
            seed=seed,
            publisher=publisher,
            verbosity=verbosity,
        )
    if options.name == "RouletteWheelSelection":
        return TournamentSelection(  # It implements both (and more)
            winner_size=options.winner_size,
            seed=seed,
            stochastic=True,  # Drawing the winner by fitness is what makes it a roulette wheel
            publisher=publisher,
            verbosity=verbosity,
            tournament_size=options.tournament_size,
        )
    if options.name == "ElitistSelection":
        return ElitistSelection(
            winner_size=options.winner_size,
            target_column=options.target_column,
            publisher=publisher,
            verbosity=verbosity,
        )
    raise ValueError(f"Unknown scalar selection operator: {options.name}")
