"""Models for the JINA multi-scenario robust interactive method.

Generic: works with any problem that has an attached scenario model (see
`desdeo.api.routers.district_heating_robust_data`). District heating was the first problem
ported this way (from a decision maker's own `multi_scenario_DM_session.ipynb`), and is migrated
to the same generic path as any other problem via `desdeo/api/db_init_district_heating.py` —
nothing here is district-heating-specific any more. Separate models/tables from the sibling
pool-matching method — design ids are independently numbered per method and would otherwise risk
colliding within a shared session.
"""

from sqlmodel import JSON, Column, Field, SQLModel


class JinaObjectiveMeta(SQLModel):
    """Display metadata for one objective, derived from the loaded problem."""

    symbol: str
    name: str
    unit: str | None = Field(default=None)
    label: str = Field(description="Display label, e.g. 'Operational Cost (EUR)'.")
    maximize: bool
    varies_by_scenario: bool = Field(
        description="False for an objective shared across all scenarios (e.g. a first-stage-only investment cost)."
    )


class JinaStrategicVarMeta(SQLModel):
    """Display metadata for one strategic (first-stage) variable."""

    symbol: str
    name: str
    label: str
    component: str = Field(description="Short display name, e.g. for compact table columns.")
    unit: str | None = Field(default=None)
    axis_max: float | None = Field(
        default=None, description="Upper bound, or null if the variable is unbounded (falls back to observed max)."
    )


class JinaScalarizerMeta(SQLModel):
    """Display metadata for one scalarizer variant."""

    name: str
    emphasize: str | None = Field(default=None, description="Objective symbol emphasized, or null for 'balanced'.")
    label: str


class JinaProblemMeta(SQLModel):
    """Everything the frontend needs to render generically against the loaded problem.

    One fetch (bundled into `DistrictHeatingRobustIterateResponse`), not per-endpoint duplication.
    """

    problem_id: int
    problem_name: str
    scenario_model_id: int | None = Field(
        default=None, description="Null for methods (e.g. JINA single-scenario) that don't use a ScenarioModelDB."
    )
    objectives: list[JinaObjectiveMeta] = Field(sa_column=Column(JSON))
    strategic_vars: list[JinaStrategicVarMeta] = Field(sa_column=Column(JSON))
    scalarizers: list[JinaScalarizerMeta] = Field(sa_column=Column(JSON))
    all_scenarios: list[str] = Field(sa_column=Column(JSON))
    default_domain_thresholds: dict[str, float] = Field(sa_column=Column(JSON))
    default_af_absolute_floors: dict[str, float] = Field(sa_column=Column(JSON))
    supports_compound_scenarios: bool
    compound_description: str | None = Field(default=None)
    lambda_objective: str | None = Field(
        default=None, description="Objective symbol for the loss-aversion (λ) re-ranking card, if this method has one."
    )


class DistrictHeatingRobustIterateRequest(SQLModel):
    """Request to run one robust-solve iteration."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)

    reference_point: dict[str, float] = Field(sa_column=Column(JSON))
    note: str | None = Field(default=None)
    max_solutions: int | None = Field(
        default=None,
        description=(
            "Cap on how many distinct designs to return this round; null means show every scalarizer variant's "
            "result. Every scalarizer still solves live regardless — this only trims what's returned/highlighted, "
            "not what's solved."
        ),
    )


class DistrictHeatingRobustMatchedSolution(SQLModel):
    """One matched (deduplicated by first-stage design) candidate returned by an iteration."""

    design_id: int
    solution_number: int
    matched_by: list[str] = Field(sa_column=Column(JSON))
    repeat: bool = Field(description="True if this design first appeared in an earlier iteration.")
    breakdown: list[dict] = Field(sa_column=Column(JSON), description="Per-scenario objective rows for this design.")
    worst_case: dict[str, float] = Field(sa_column=Column(JSON))
    best_case: dict[str, float] = Field(sa_column=Column(JSON))


class DistrictHeatingRobustIterateResponse(SQLModel):
    """Response from a robust-solve iteration."""

    state_id: int
    iteration_number: int = 1
    reference_point: dict[str, float] = Field(sa_column=Column(JSON))
    note: str | None = Field(default=None)
    solutions: list[DistrictHeatingRobustMatchedSolution] = Field(sa_column=Column(JSON))
    wish_list: list[int] = Field(sa_column=Column(JSON), description="Current wish-listed design ids.")
    global_ideal: dict[str, float] = Field(sa_column=Column(JSON))
    global_nadir: dict[str, float] = Field(sa_column=Column(JSON))
    all_scenarios: list[str] = Field(sa_column=Column(JSON))
    meta: JinaProblemMeta = Field(sa_column=Column(JSON))


class DistrictHeatingRobustWishlistUpdateRequest(SQLModel):
    """Add or remove design ids from the running wish list."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)

    design_ids: list[int] = Field(sa_column=Column(JSON))


class DistrictHeatingRobustWishlistResponse(SQLModel):
    """Response after a wish-list add/remove."""

    state_id: int
    wish_list: list[int] = Field(sa_column=Column(JSON))
    skipped_ids: list[int] = Field(
        sa_column=Column(JSON), default_factory=list, description="Requested ids that were not found and were skipped."
    )


class DistrictHeatingRobustAnalysisRequest(SQLModel):
    """Request for the robustness/antifragility analysis, with DM-supplied thresholds."""

    problem_id: int
    session_id: int | None = Field(default=None)
    domain_thresholds: dict[str, float] = Field(sa_column=Column(JSON))
    af_absolute_floors: dict[str, float] = Field(sa_column=Column(JSON))


class DistrictHeatingRobustAnalysisResponse(SQLModel):
    """Robustness + antifragility analysis for the current wish list.

    Reuses `compute_robustness_metrics`/`compute_antifragility_metrics` from the sibling
    (pool-matching) method's data module unchanged, fed from this method's session-discovered
    `design_registry` instead of a precomputed CSV pool.
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


class DistrictHeatingRobustStrategicDesign(SQLModel):
    """One discovered strategic (first-stage) design.

    Variable values, the scalarizer that discovered it, and its worst-case robust objectives.
    """

    design_id: int
    solution_number: int
    scalarizer: str
    first_iteration: int | None = Field(default=None)
    strategic_vals: dict[str, float] = Field(sa_column=Column(JSON))
    robust_vals: dict[str, float] = Field(sa_column=Column(JSON))
    breakdown: list[dict] = Field(sa_column=Column(JSON))


class DistrictHeatingRobustStrategicDesignsResponse(SQLModel):
    """Every strategic design discovered this session, with its variable values and cross-scenario performance.

    A stateless read of the already-solved `design_registry` — no new Gurobi solve.
    """

    designs: list[DistrictHeatingRobustStrategicDesign] = Field(sa_column=Column(JSON))
    axis_max: dict[str, float | None] = Field(
        sa_column=Column(JSON),
        description=(
            "Upper bound per strategic variable, or null if unbounded — also this problem's existing capacity per "
            "component, where that convention applies."
        ),
    )


class DistrictHeatingRobustCombinedScenarioRequest(SQLModel):
    """Request for the compound-disruption (two-at-once) stress test."""

    problem_id: int
    session_id: int | None = Field(default=None)
    design_ids: list[int] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description=(
            "Explicit design ids to test. Defaults to the current wish list, falling back to "
            "every discovered design if the wish list is empty."
        ),
    )
    reference_point: dict[str, float] = Field(
        sa_column=Column(JSON),
        description=(
            "Required aspiration level per objective symbol (obj1..objN), in each objective's own "
            "raw units. Every (design, combined scenario) pair is re-evaluated by solving one ASF "
            "against this point, so each row is the objective vector of a single achievable "
            "operating plan. There is deliberately no default: the re-evaluation says how a design "
            "performs when operated toward some aspiration, and has no meaning without one."
        ),
    )


class DistrictHeatingRobustCombinedScenarioResponse(SQLModel):
    """Compound-disruption stress test results.

    Built via the problem's configured `compound_scenario_hook` (see `desdeo.api.routers.jina_compound`).
    """

    candidate_ids: list[int] = Field(sa_column=Column(JSON))
    combo_names: list[str] = Field(sa_column=Column(JSON), description="All combined-scenario names tested.")
    rows: list[dict] = Field(sa_column=Column(JSON), description="One row per (design, combined scenario) pair.")
    summary: list[dict] = Field(
        sa_column=Column(JSON),
        description="Worst compound-disruption case vs. single-disruption worst case, per design/objective.",
    )
    supports_superadditivity: bool = Field(
        default=False,
        description=(
            "True if the problem also configures a compound_reference_hook, in which case each "
            "row additionally carries '{obj}_superadd' — see jina_compound.compute_superadditivity."
        ),
    )
    reference_rows: list[dict] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description=(
            "One row per (design, reference scenario) pair — baseline + each single disruption "
            "alone, only present when supports_superadditivity is True. Same row shape as `rows`, "
            "with `combined_scenario` holding the reference scenario's own name (e.g. 'baseline', "
            "'price_spike'). Lets the frontend compare a design's single-disruption performance "
            "against its combined-disruption performance for any pair."
        ),
    )
    pair_components: dict[str, tuple[str, str]] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description=(
            "{combo_name: (reference_name_a, reference_name_b)} — which two reference_rows entries a combo name "
            "pairs, for the frontend to resolve a chosen (A, B) pair to its combo name."
        ),
    )


class DistrictHeatingRobustSessionTreeEntry(SQLModel):
    """One node (iteration or wish-list update) in a session's history."""

    state_id: int
    kind: str
    parent_id: int | None = Field(default=None)
    iteration_number: int | None = Field(default=None)
    reference_point: dict[str, float] | None = Field(default=None, sa_column=Column(JSON))
    note: str | None = Field(default=None)
    solutions: list[dict] | None = Field(default=None, sa_column=Column(JSON))
    wish_list: list[int] | None = Field(default=None, sa_column=Column(JSON))
