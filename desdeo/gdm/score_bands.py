"""Implements a interactive SCORE bands based GDM."""

from typing import Literal

import polars as pl
from pydantic import BaseModel, Field, ConfigDict

from desdeo.tools.score_bands import SCOREBandsConfig, SCOREBandsResult, score_json
from desdeo.gdm.voting_rules import majority_rule, plurality_rule


class SCOREBandsGDMConfig(BaseModel):
    """Configuration for the SCORE bands based GDM."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    num_interations: int = Field(default=5)
    """Number of iterations to perform."""
    score_bands_config: SCOREBandsConfig = Field(default_factory=lambda: SCOREBandsConfig())
    """Configuration for the SCORE bands method."""
    voting_method: Literal["majority", "plurality"] = Field(default="plurality")
    """Voting method to use."""


class SCOREBandsGDMResult(BaseModel):
    """Result of the SCORE bands based GDM."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    votes: dict[str, int] | None = Field(default=None)
    """The votes given by the decision makers."""
    score_bands_result: SCOREBandsResult
    """Result of the SCORE bands method."""
    relevant_ids: list[int]
    """IDs of the relevant solutions in the current iteration. Assumes that data is not modified between iterations."""
    # If the data keeps changing, we need to store the actual data instead of just the IDs.


def run_score_bands_gdm(
    data: pl.DataFrame,
    config: SCOREBandsGDMConfig,
    state: list[SCOREBandsGDMResult] | None = None,
    votes: dict[str, int] | None = None,
) -> list[SCOREBandsGDMResult]:
    """Run the SCORE bands based interactive GDM.

    Args:
        data (pl.DataFrame): The data to run the GDM on.
        config (SCOREBandsGDMConfig): Configuration for the GDM.
        state (list[SCOREBandsGDMResult] | None, optional): List of previous state of the GDM. Defaults to None.
        votes (dict[str, int] | None, optional): Votes from the decision makers. Defaults to None.

    Raises:
        ValueError: Both state and votes must be provided or neither.

    Returns:
        list[SCOREBandsGDMResult]: The updated state of the GDM.
    """
    if bool(state) != bool(votes):
        raise ValueError("Both state and votes must be provided or neither.")
    if votes is None:
        # First iteration. No votes yet.
        score_bands_result = score_json(data, config.score_bands_config)
        return [SCOREBandsGDMResult(score_bands_result=score_bands_result, relevant_ids=list(range(len(data))))]
    if state is None:  # Just to shut up ruff
        raise ValueError("State must be provided if votes are provided.")

    if config.voting_method == "majority":
        winning_clusters = [majority_rule(votes)]
    elif config.voting_method == "plurality":
        winning_clusters = plurality_rule(votes)
    else:  # Handle future voting methods
        raise ValueError(f"Unknown voting method: {config.voting_method}")

    index_column_name = "index"
    if index_column_name in data.columns:
        index_column_name = "index_"
    cluster_column_name = "cluster"
    if cluster_column_name in data.columns:
        cluster_column_name = "cluster_"

    clusters = state[-1].score_bands_result.clusters
    relevant_data = (
        data.with_row_index(name=index_column_name)  # Add index column
        .filter(pl.col(index_column_name).is_in(state[-1].relevant_ids))  # Get the solutions from last iteration
        .with_columns(pl.Series(cluster_column_name, clusters))  # Add clustering information from last iteration
        .filter(pl.col(cluster_column_name).is_in(winning_clusters))  # Keep only winning clusters
        .drop(cluster_column_name)  # Drop cluster column
    )

    relevant_ids = relevant_data[index_column_name].to_list()
    relevant_data = relevant_data.drop(index_column_name)  # Drop index column

    return [
        *state,
        SCOREBandsGDMResult(
            votes=votes,
            score_bands_result=score_json(relevant_data, config.score_bands_config),
            relevant_ids=relevant_ids,
        ),
    ]
