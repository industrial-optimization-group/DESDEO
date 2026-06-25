"""JSON Schema for scalar selector operator options."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from desdeo.emo.operators.scalar_selection import BaseScalarSelector, TournamentSelection

if TYPE_CHECKING:
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


class RouletteWheelSelectionOptions(TournamentSelectionOptions):
    """Options for roulette wheel selection operator."""

    name: Literal["RouletteWheelSelection"] = Field(
        default="RouletteWheelSelection", frozen=True, description="The name of the scalar selection operator."
    )
    """The name of the scalar selection operator."""


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
    options: ScalarSelectionOptions, seed: int, publisher: Publisher, verbosity: int
) -> BaseScalarSelector:
    """Construct a scalar selector operator based on the provided options."""
    if options.name == "TournamentSelection":
        return TournamentSelection(
            tournament_size=options.tournament_size,
            winner_size=options.winner_size,
            publisher=publisher,
            verbosity=verbosity,
        )
    if options.name == "RouletteWheelSelection":
        return TournamentSelection(  # It implements both (and more)
            winner_size=options.winner_size,
            seed=seed,  # By providing seed tournament selection behaves like roulette wheel
            publisher=publisher,
            verbosity=verbosity,
            tournament_size=options.tournament_size,
        )
    raise ValueError(f"Unknown scalar selection operator: {options.name}")
