"""Models specific to the JINA method."""

import math
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

from desdeo.mcdm.jina import Measure, SolveView, Target, View
from desdeo.tools.robustness_metrics import Antifragility, DomainCriterion
from desdeo.tools.scenario_designs import LeafOutcome

from .generic_states import StateKind

# A finite float.  NaN and infinity are replaced by a non-numeric string, which fails validation
# with an error whose echoed input can be serialised as JSON.
FiniteFloat = Annotated[
    float,
    BeforeValidator(
        lambda value: f"non-finite {value}" if isinstance(value, float) and not math.isfinite(value) else value
    ),
    Field(allow_inf_nan=False),
]

# Scalar, vector and matrix design variables are supported.
DesignValue = float | list[float] | list[list[float]]


class JinaSessionRequest(BaseModel):
    """Request with the problem, interactive session and parent state of a JINA step."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)


class JinaSetupRequest(JinaSessionRequest):
    """Request model for the JINA setup endpoint."""

    scenario_model_id: int | None = Field(
        default=None, description="DB id of the ScenarioModelDB. Defaults to the problem's first scenario model."
    )
    design_variables: list[str] | None = Field(
        default=None, description="Root variables forming a design. Defaults to all root variables."
    )
    measure: Measure = Field(default="worst_case", description="The aggregation of the aggregated view.")
    cvar_alpha: FiniteFloat = Field(default=0.9, gt=0, lt=1, description="The CVaR confidence level.")
    baseline_leaf: str | None = Field(default=None, description="Leaf the antifragility analysis compares against.")
    design_rtol: FiniteFloat = Field(
        default=1e-4, ge=0, description="Relative tolerance for identifying equal designs."
    )


class JinaIterateRequest(JinaSessionRequest):
    """Request model for the JINA iterate endpoint."""

    setup_state_id: int
    view: SolveView = Field(default="aggregated")
    leaf: str | None = Field(
        default=None,
        description=(
            "Scenario the designs are optimised for; required by and only allowed in the scenario_optimal view."
        ),
    )
    reference_point: dict[str, FiniteFloat] = Field(
        description="Aspiration levels by target symbol, original direction."
    )


class JinaImportRequest(JinaSessionRequest):
    """Request model for importing designs from a representative solution set."""

    setup_state_id: int
    representative_set_id: int = Field(description="Id of a RepresentativeNonDominatedSolutions of the problem.")
    reference_point: dict[str, FiniteFloat] = Field(
        description="Aspiration levels by original objective symbol at which the designs are evaluated."
    )


class JinaEvaluateRequest(JinaSessionRequest):
    """Request model for the JINA evaluate endpoint."""

    setup_state_id: int
    scenario_model_id: int | None = Field(
        default=None, description="Scenario model to evaluate in. Defaults to the setup's scenario model."
    )
    design_ids: list[int] | None = Field(default=None, description="Designs to evaluate. Defaults to all.")
    thresholds: dict[str, FiniteFloat] = Field(
        description=(
            "Domain-criterion thresholds by objective, original direction; the reference point every leaf is "
            "re-solved at."
        )
    )


class JinaSelectRequest(JinaSessionRequest):
    """Request model for the JINA select endpoint."""

    setup_state_id: int
    wishlist: list[int] = Field(default_factory=list)
    final_design_id: int | None = Field(default=None)


class JinaAntifragilityRequest(JinaSessionRequest):
    """Request model for the JINA antifragility endpoint."""

    setup_state_id: int
    evaluate_state_id: int = Field(description="The StateDB id of the evaluate state whose outcomes are analysed.")
    design_ids: list[int] | None = Field(default=None, description="Designs to compare. Defaults to all evaluated.")
    absolute_floors: dict[str, FiniteFloat] | None = Field(
        default=None,
        description="Worst acceptable outcome by objective for the antifragility classes, original direction.",
    )
    loss_floors: dict[str, FiniteFloat] | None = Field(
        default=None,
        description="Largest acceptable loss relative to the baseline leaf by objective, in original units.",
    )


class JinaScenarioModelInfo(BaseModel):
    """A scenario model of a problem."""

    id: int
    leaves: list[str]
    n_leaves: int
    has_probabilities: bool
    root_variables: list[str] = Field(description="Variables shared by all scenarios, the candidate design variables.")
    default_design_variables: list[str] = Field(description="The design variables a setup defaults to.")
    objectives: list[str] = Field(description="Symbols of the objectives of the scenario model.")
    maximize: dict[str, bool] = Field(description="Whether each objective of the scenario model is maximised.")


class JinaDesign(BaseModel):
    """A design in the design registry of a JINA setup."""

    id: int = Field(description="Id of the design, unique within the registry.")
    values: dict[str, DesignValue] = Field(description="Design variable values.")
    effective_reference_point: dict[str, float] | None = Field(
        default=None, description="The target-keyed reference point a solved design was found at; None for imports."
    )
    import_reference_point: dict[str, float] | None = Field(
        default=None, description="The objective-keyed reference point an imported design was evaluated at."
    )
    view: SolveView | None = Field(default=None, description="View the design was solved in; None for imports.")
    leaf: str | None = Field(
        default=None, description="Scenario the design was optimised for; scenario_optimal view only."
    )
    source: Literal["solve", "import"]
    leaf_objectives: dict[str, dict[str, float]] = Field(
        default_factory=dict, description="Objective values by leaf and objective symbol."
    )


class JinaDesignInfo(JinaDesign):
    """A design of the registry with the state it was found in and its target values."""

    state_id: int = Field(description="The StateDB id of the iterate state that added the design.")
    target_values: dict[View, dict[str, float]] = Field(description="Target values by view and target symbol.")


class JinaIterateResult(BaseModel):
    """Result of one variant or imported row of an iterate state."""

    name: str = Field(description="Variant name or 'row_<i>'.")
    success: bool
    message: str
    effective_reference_point: dict[str, float] = Field(default_factory=dict)
    target_values: dict[str, float] = Field(default_factory=dict)
    alpha: float | None = Field(default=None)
    binding: list[str] = Field(default_factory=list)
    outcomes: dict[str, LeafOutcome] = Field(
        default_factory=dict, description="The design's outcome in every leaf; scenario_optimal view only."
    )
    design_id: int | None = Field(default=None, description="Registry id of the resulting design.")


class JinaSetupResult(BaseModel):
    """Contents of a JINA setup state."""

    kind: Literal["jina.setup"]
    scenario_model_id: int
    design_variables: list[str]
    measure: Measure
    cvar_alpha: float
    baseline_leaf: str | None
    design_rtol: float
    targets: dict[View, list[Target]] | None
    ranges: dict[View, dict[str, tuple[float, float]]] | None
    scenario_targets: dict[str, list[Target]] | None = Field(
        description="The objectives of each leaf alone, as targets by leaf."
    )
    scenario_ranges: dict[str, dict[str, tuple[float, float]]] | None = Field(
        description="(ideal, nadir) by leaf and objective symbol, with each leaf solved alone."
    )


class JinaIterateStateResult(BaseModel):
    """Contents of a JINA iterate state."""

    kind: Literal["jina.iterate"]
    setup_state_id: int
    mode: Literal["solve", "import"]
    view: SolveView | None
    leaf: str | None
    reference_point: dict[str, float]
    results: list[JinaIterateResult]
    new_design_ids: list[int]
    designs: list[JinaDesign]


class JinaEvaluateResult(BaseModel):
    """Contents of a JINA evaluate state."""

    kind: Literal["jina.evaluate"]
    setup_state_id: int
    scenario_model_id: int
    design_ids: list[int]
    thresholds: dict[str, float]
    outcomes: dict[int, dict[str, LeafOutcome]]
    domain_criterion: dict[int, DomainCriterion] | None = Field(
        default=None, description="Domain criterion of each design at the thresholds; None until ready."
    )


class JinaSelectResult(BaseModel):
    """Contents of a JINA select state."""

    kind: Literal["jina.select"]
    setup_state_id: int
    wishlist: list[int]
    final_design_id: int | None


class JinaStateResponse(BaseModel):
    """A JINA state and whether its background job has finished."""

    state_id: int
    kind: StateKind
    is_ready: bool
    error: str | None = None
    result: Annotated[
        JinaSetupResult | JinaIterateStateResult | JinaEvaluateResult | JinaSelectResult, Field(discriminator="kind")
    ]


class JinaGetOrInitializeResponse(BaseModel):
    """The latest JINA setup of the session and its later states, oldest first."""

    setup: JinaStateResponse | None
    states: list[JinaStateResponse]


class JinaAntifragilityResponse(BaseModel):
    """Antifragility of evaluated designs relative to the setup's baseline leaf, by design id."""

    antifragility: dict[int, Antifragility]
    antifragile_objectives: list[str]
