"""Implements a interactive SCORE bands based GDM."""

from typing import Literal

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from desdeo.gdm.voting_rules import consensus_rule
from desdeo.tools.score_bands import SCOREBandsConfig, SCOREBandsResult, score_json


class SCOREBandsGDMConfig(BaseModel):
    """Configuration for the SCORE bands based GDM."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    score_bands_config: SCOREBandsConfig = Field(default_factory=lambda: SCOREBandsConfig())
    """Configuration for the SCORE bands method."""
    minimum_votes: int = Field(default=1, gt=0)
    """Minimum number of votes required to select a cluster."""
    from_iteration: int | None
    """The iteration number from which to consider the clusters. Set to None if method is initializing."""


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
    iteration: int
    previous_iteration: int | None
    """The previous iteration number, if any."""


def score_bands_gdm(
    data: pl.DataFrame,
    config: SCOREBandsGDMConfig,
    state: list[SCOREBandsGDMResult],
    votes: dict[str, int] | None = None,
) -> list[SCOREBandsGDMResult]:
    """Run the SCORE bands based interactive GDM.

    Args:
        data (pl.DataFrame): The data to run the GDM on.
        config (SCOREBandsGDMConfig): Configuration for the GDM.
        state (list[SCOREBandsGDMResult]): List of previous state of the GDM. Empty list if first iteration.
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
        return [
            SCOREBandsGDMResult(
                score_bands_result=score_bands_result,
                relevant_ids=list(range(len(data))),
                iteration=1,
                previous_iteration=None,
            )
        ]
    if not state:
        raise ValueError("State must be provided if votes are provided.")
    elif config.from_iteration is None:
        raise ValueError("from_iteration must be set in the config for subsequent iterations.")

    winning_clusters = consensus_rule(votes, config.minimum_votes)

    index_column_name = "index"
    if index_column_name in data.columns:
        index_column_name = "index_"
    cluster_column_name = "cluster"
    if cluster_column_name in data.columns:
        cluster_column_name = "cluster_"

    current_iteration = state[-1].iteration + 1

    clusters = state[config.from_iteration - 1].score_bands_result.clusters
    relevant_data = (
        data.with_row_index(name=index_column_name)  # Add index column
        .filter(
            pl.col(index_column_name).is_in(state[config.from_iteration - 1].relevant_ids)
        )  # Get the solutions from previous iteration
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
            iteration=current_iteration,
            previous_iteration=config.from_iteration,
        ),
    ]
