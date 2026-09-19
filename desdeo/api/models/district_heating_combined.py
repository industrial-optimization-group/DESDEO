"""Request/response models for the JINA combined multi-scenario method.

Separate from `district_heating_robust`'s models on purpose: that method's payload is keyed by
base objective symbol (one aspiration level per objective, aggregated to its worst case over the
scenarios), while this one is keyed by combined-problem symbol — one level per (objective,
scenario) cell. Sharing a model between the two would make the key space ambiguous.
"""

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field, SQLModel


class DistrictHeatingCombinedCell(SQLModel):
    """One (objective, scenario) pair the decision maker sets an aspiration level for."""

    symbol: str = Field(description="Objective symbol in the combined problem, e.g. 'price_spike_january_obj1'.")
    obj_symbol: str = Field(description="The base objective this cell measures, e.g. 'obj1'.")
    scenario: str = Field(description="The leaf scenario it measures it in; empty for a shared objective.")
    shared: bool = Field(
        description=(
            "True when the objective does not vary by scenario (it depends only on the first-stage "
            "decision), so it appears as a single cell rather than one per scenario."
        )
    )
    label: str
    unit: str | None = None
    maximize: bool = False
    ideal: float = Field(description="Best value reachable for this objective in this scenario alone.")
    nadir: float = Field(description="Worst value in that scenario's payoff table.")
    weight: float = Field(description="|nadir - ideal|, the ASF normalization applied to this cell.")


class DistrictHeatingCombinedInitializeRequest(SQLModel):
    """Request to start or resume a JINA multi-scenario session for a problem."""

    problem_id: int
    session_id: int | None = Field(default=None)


class DistrictHeatingCombinedInitializeResponse(SQLModel):
    """The grid the decision maker fills in, plus what they need to fill it in sensibly."""

    problem_id: int
    problem_name: str
    scenarios: list[str] = Field(sa_column=Column(JSON), description="Leaf scenario names, in display order.")
    objectives: list[str] = Field(sa_column=Column(JSON), description="Base objective symbols, in display order.")
    objective_labels: dict[str, str] = Field(sa_column=Column(JSON))
    strategic_symbols: list[str] = Field(sa_column=Column(JSON))
    strategic_labels: dict[str, str] = Field(sa_column=Column(JSON))
    strategic_units: dict[str, str] = Field(sa_column=Column(JSON))
    strategic_components: dict[str, str] = Field(
        sa_column=Column(JSON),
        default_factory=dict,
        description="{symbol: short component name}, for compact table columns.",
    )
    strategic_axis_max: dict[str, float | None] = Field(
        sa_column=Column(JSON),
        default_factory=dict,
        description=(
            "Upper bound of each strategic variable, read from the problem, or null if it is "
            "unbounded. For a problem that follows the district heating convention this doubles "
            "as the capacity that already exists for that component, which is what lets a "
            "solution's decision be reported as capacity *added* on top of it."
        ),
    )
    cells: list[DistrictHeatingCombinedCell] = Field(
        sa_column=Column(JSON), description="One entry per aspiration level the DM must supply."
    )
    scalarizer_count: int = Field(
        default=0,
        description=(
            "Number of scalarizer variants (balanced + one per objective), i.e. the most distinct "
            "designs a single round can produce and the maximum the UI should let the DM ask for."
        ),
    )
    scalarizer_labels: list[str] = Field(
        sa_column=Column(JSON), default_factory=list, description="Display labels, in priority order."
    )


class DistrictHeatingCombinedIterateRequest(SQLModel):
    """Request to solve one iteration against the decision maker's reference point."""

    problem_id: int
    session_id: int | None = Field(default=None)
    reference_point: dict[str, float] = Field(
        sa_column=Column(JSON),
        description=(
            "One aspiration level per cell, keyed by the cell's combined-problem symbol. Must "
            "cover every cell returned by /initialize — the ASF scalarizes exactly the objectives "
            "named here, so a partial reference point would silently drop cells from the solve "
            "rather than fail."
        ),
    )
    max_solutions: int | None = Field(
        default=None,
        description=(
            "Cap on how many distinct designs to return this round; null means every scalarizer "
            "variant's result. Every variant still solves regardless — this trims what is "
            "returned, not what is solved, so nothing is lost from the design registry or wish "
            "list. Designs are kept in scalarizer priority order, balanced first."
        ),
    )
    note: str | None = Field(default=None)


class DistrictHeatingCombinedCellResult(SQLModel):
    """Outcome of one (objective, scenario) cell in an iteration."""

    symbol: str
    aspiration: float
    achieved: float
    scaled: float = Field(description="(achieved - aspiration) / weight — this cell's term in the ASF max.")
    binds: bool = Field(
        description=(
            "True when this cell's scaled value equals alpha, i.e. the solution is limited by it. "
            "Relaxing a binding cell is what frees up improvement elsewhere; relaxing a "
            "non-binding one changes nothing."
        )
    )


class DistrictHeatingCombinedSolution(SQLModel):
    """The single design one iteration produces.

    One ASF solve means one design per round, so unlike the multi-scenario method's matched
    solutions there is no scalarizer-variant list — but a design can still resurface in a later
    round, in which case it keeps its original `solution_number` and is flagged as a `repeat`.
    """

    design_id: int
    solution_number: int
    matched_by: list[str] = Field(
        sa_column=Column(JSON),
        default_factory=list,
        description=(
            "Which scalarizer variants landed on this design — e.g. ['balanced', "
            "'emphasize_obj4']. Several variants agreeing on one design is informative: it means "
            "the emphasis did not buy a different build."
        ),
    )
    repeat: bool = Field(description="True if this design first appeared in an earlier iteration.")
    alpha: float
    all_reached: bool
    cell_results: list[DistrictHeatingCombinedCellResult] = Field(sa_column=Column(JSON))
    strategic_values: dict[str, float] = Field(
        sa_column=Column(JSON), description="The first-stage capacities this solution builds."
    )
    breakdown: list[dict] = Field(
        sa_column=Column(JSON),
        description=(
            "One row per scenario, keyed by base objective symbol — the same shape the "
            "multi-scenario method's per-scenario views consume. A shared objective's single value "
            "is repeated into every row."
        ),
    )


class DistrictHeatingCombinedIterateResponse(SQLModel):
    """State after one iteration.

    Also what /get-or-initialize returns, so the UI has one shape to render whether it just solved or is resuming an
    existing session.
    """

    state_id: int
    iteration_number: int = 1
    reference_point: dict[str, float] = Field(sa_column=Column(JSON), default_factory=dict)
    note: str | None = None
    solution: DistrictHeatingCombinedSolution | None = Field(
        default=None,
        sa_column=Column(JSON),
        description=(
            "The primary (balanced) design, or None before the first iteration. Retained alongside "
            "`solutions` so rounds recorded before this method solved several variants — and any "
            "client written against the single-design shape — still read correctly."
        ),
    )
    solutions: list[DistrictHeatingCombinedSolution] = Field(
        sa_column=Column(JSON),
        default_factory=list,
        description=(
            "Every distinct design this round produced, balanced first, already trimmed to the "
            "round's `max_solutions`. Empty before the first iteration."
        ),
    )
    max_solutions: int | None = Field(
        default=None, description="The cap this round used, so the UI can show what was asked for."
    )
    scalarizer_count: int = Field(
        default=0,
        description=(
            "How many scalarizer variants this problem has — the ceiling on distinct designs per "
            "round, and the maximum the UI should offer."
        ),
    )
    wish_list: list[int] = Field(sa_column=Column(JSON), default_factory=list)
    scenarios: list[str] = Field(sa_column=Column(JSON), default_factory=list)
    objectives: list[str] = Field(sa_column=Column(JSON), default_factory=list)
    objective_labels: dict[str, str] = Field(sa_column=Column(JSON), default_factory=dict)
    default_domain_thresholds: dict[str, float] = Field(sa_column=Column(JSON), default_factory=dict)


class DistrictHeatingCombinedSessionTreeEntry(SQLModel):
    """One past iteration, for browsing history without re-solving."""

    state_id: int
    iteration_number: int
    note: str | None = None
    reference_point: dict[str, float] = Field(sa_column=Column(JSON))
    solution: DistrictHeatingCombinedSolution | None = Field(
        default=None, sa_column=Column(JSON), description="The round's primary (balanced) design."
    )
    solutions: list[DistrictHeatingCombinedSolution] = Field(
        sa_column=Column(JSON),
        default_factory=list,
        description=(
            "Every design the round produced. A round recorded before this method solved several "
            "scalarizer variants yields the single design it did produce."
        ),
    )


class DistrictHeatingCombinedSessionTreeResponse(SQLModel):
    """All iterations of a session, oldest first."""

    entries: list[DistrictHeatingCombinedSessionTreeEntry] = Field(sa_column=Column(JSON))


class DistrictHeatingCombinedWishlistUpdateRequest(SQLModel):
    """Add or remove design ids from the running wish list."""

    problem_id: int
    session_id: int | None = Field(default=None)
    design_ids: list[int] = Field(sa_column=Column(JSON))


class DistrictHeatingCombinedWishlistResponse(SQLModel):
    """The wish list after an add or remove."""

    state_id: int
    wish_list: list[int] = Field(sa_column=Column(JSON))


class DistrictHeatingCombinedAnalysisRequest(SQLModel):
    """Request to analyse the wish-listed designs."""

    problem_id: int
    session_id: int | None = Field(default=None)
    domain_thresholds: dict[str, float] | None = Field(
        sa_column=Column(JSON),
        default=None,
        description=(
            "{objective_symbol: threshold}. An objective with no threshold is left out of the "
            "domain criterion rather than counted as passing. Defaults to the problem's "
            "JinaMultiScenarioMetaData.default_domain_thresholds."
        ),
    )


class DistrictHeatingCombinedAnalysisResponse(SQLModel):
    """Domain criterion over the wish-listed designs."""

    wish_list: list[int] = Field(sa_column=Column(JSON))
    domain_criterion: list[dict] = Field(
        sa_column=Column(JSON),
        description=(
            "Per design: how many scenarios meet each thresholded objective, plus mean_domain_criterion across them."
        ),
    )
    domain_thresholds: dict[str, float] = Field(sa_column=Column(JSON))
    scenario_count: int = Field(description="Total scenarios, i.e. the maximum a count can reach.")
