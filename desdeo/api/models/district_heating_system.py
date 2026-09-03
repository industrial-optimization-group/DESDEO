"""Models for the JINA single-scenario pool-matching interactive method.

Generic: works with any problem that has an attached `JinaPoolMetaData` row (see
`desdeo/api/routers/district_heating_system_data.py`). District heating was the first problem
this served, ported from the decision maker's own `the_DM_session.ipynb`; it's no longer
special-cased. This method reads existing pre-computed data; it never solves a `Problem`.
"""

from sqlmodel import JSON, Column, Field, SQLModel

from desdeo.api.models.district_heating_robust import JinaProblemMeta


class DistrictHeatingIterateRequest(SQLModel):
    """Request to run one iteration of reference-point matching."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)

    reference_point: dict[str, float] = Field(sa_column=Column(JSON))
    max_solutions: int | None = Field(default=6)
    note: str | None = Field(default=None)


class DistrictHeatingMatchedSolution(SQLModel):
    """One matched candidate design returned by an iteration."""

    design_id: int
    solution_number: int
    matched_by: list[str] = Field(sa_column=Column(JSON))
    n_scenarios: int
    rows: list[dict] = Field(sa_column=Column(JSON), description="Per-scenario objective rows for this design.")
    worst_case: dict[str, float] = Field(sa_column=Column(JSON))
    best_case: dict[str, float] = Field(sa_column=Column(JSON))


class DistrictHeatingIterateResponse(SQLModel):
    """Response from an iteration of the District Heating System method."""

    state_id: int
    reference_point: dict[str, float] = Field(sa_column=Column(JSON))
    note: str | None = Field(default=None)
    solutions: list[DistrictHeatingMatchedSolution] = Field(sa_column=Column(JSON))
    wish_list: list[int] = Field(sa_column=Column(JSON), description="Current wish-listed design ids.")
    already_shown_ids: list[int] = Field(sa_column=Column(JSON))
    global_ideal: dict[str, float] = Field(sa_column=Column(JSON))
    global_nadir: dict[str, float] = Field(sa_column=Column(JSON))
    all_scenarios: list[str] = Field(sa_column=Column(JSON))
    meta: JinaProblemMeta


class DistrictHeatingWishlistUpdateRequest(SQLModel):
    """Add or remove design ids from the running wish list."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)

    design_ids: list[int] = Field(sa_column=Column(JSON))


class DistrictHeatingWishlistResponse(SQLModel):
    """Response after a wish-list add/remove."""

    state_id: int
    wish_list: list[int] = Field(sa_column=Column(JSON))
    skipped_ids: list[int] = Field(
        sa_column=Column(JSON), default_factory=list, description="Requested ids that were not found and were skipped."
    )


class DistrictHeatingAnalysisRequest(SQLModel):
    """Request for the robustness/antifragility analysis, with DM-supplied thresholds."""

    problem_id: int
    session_id: int | None = Field(default=None)
    domain_thresholds: dict[str, float] = Field(sa_column=Column(JSON))
    af_absolute_floors: dict[str, float] = Field(sa_column=Column(JSON))


class DistrictHeatingAnalysisResponse(SQLModel):
    """Robustness + antifragility analysis for the current wish list.

    Ports `stage_2c_analysis.ipynb`: max regret and antifragility are computed over the full
    candidate pool for stable normalization, then filtered to the wish list for display; domain
    criterion is computed over the wish list only. Rows are returned as loosely-typed JSON
    records (one dict per design, or per design/objective/scenario for deviations) rather than
    a strict schema, matching the same pragmatic pattern as `DistrictHeatingMatchedSolution.rows`.
    """

    wish_list: list[int] = Field(sa_column=Column(JSON))
    max_regret: list[dict] = Field(sa_column=Column(JSON))
    domain_criterion: list[dict] = Field(sa_column=Column(JSON))
    antifragility_summary: list[dict] = Field(sa_column=Column(JSON))
    antifragility_deviations: list[dict] = Field(sa_column=Column(JSON))
    af_objectives: list[str] = Field(sa_column=Column(JSON), description="Objectives with real upside potential.")
    baseline_scenario: str
    domain_thresholds: dict[str, float] = Field(sa_column=Column(JSON))
    af_absolute_floors: dict[str, float] = Field(sa_column=Column(JSON))


class DistrictHeatingStrategicDesign(SQLModel):
    """One design in the candidate pool — strategic capacities, the scenario it was originally
    optimized for, and its full performance breakdown. Port of the design table in
    `Vis_strategic_decisions.ipynb`.
    """

    design_id: int
    source_design_scenario: str
    reference_id: int
    scalarizer: str
    strategic_vals: dict[str, float] = Field(sa_column=Column(JSON))
    breakdown: list[dict] = Field(sa_column=Column(JSON))


class DistrictHeatingStrategicDesignsResponse(SQLModel):
    """Every design in the candidate pool, for the DM to browse capacities and cross-scenario
    performance. Stateless read of the pre-computed pool — no session dependency.
    """

    designs: list[DistrictHeatingStrategicDesign] = Field(sa_column=Column(JSON))
    axis_max: dict[str, float | None] = Field(
        sa_column=Column(JSON),
        description="Upper bound per strategic capacity variable (null if unbounded) — also this problem's existing capacity per component.",
    )


class DistrictHeatingSessionTreeEntry(SQLModel):
    """One node (iteration or wish-list update) in a session's history."""

    state_id: int
    kind: str
    parent_id: int | None = Field(default=None)
    reference_point: dict[str, float] | None = Field(default=None, sa_column=Column(JSON))
    note: str | None = Field(default=None)
    solutions: list[dict] | None = Field(default=None, sa_column=Column(JSON))
    wish_list: list[int] | None = Field(default=None, sa_column=Column(JSON))
