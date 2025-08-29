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


ScalarSelectionOptions = TournamentSelectionOptions | RouletteWheelSelectionOptions


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
            winner_size=options.winner_size, seed=seed, publisher=publisher, verbosity=verbosity
        )
    else:
        raise ValueError(f"Unknown scalar selection operator: {options.name}")
