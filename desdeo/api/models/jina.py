"""Models specific to the JINA method."""

import math
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

from desdeo.mcdm.jina import Measure, Target, View
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
        default=None, description="Root variables forming a design. Defaults to the scalar root variables."
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
    mode: Literal["solve", "pool"] = Field(
        default="solve", description="Solve new designs, or pick designs found earlier from the design pool."
    )
    view: View = Field(default="aggregated")
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
    reference_point: dict[str, FiniteFloat] | None = Field(
        default=None,
        description=(
            "Aspiration levels by original objective symbol for leaves a design's own reference point does not "
            "cover; overrides the reference point of imported designs."
        ),
    )


class JinaSelectRequest(JinaSessionRequest):
    """Request model for the JINA select endpoint."""

    setup_state_id: int
    wishlist: list[int] = Field(default_factory=list)
    final_design_id: int | None = Field(default=None)


class JinaAnalysisRequest(JinaSessionRequest):
    """Request model for the JINA robustness analysis endpoint."""

    setup_state_id: int
    evaluate_state_id: int = Field(description="The StateDB id of the evaluate state whose outcomes are analysed.")
    design_ids: list[int] | None = Field(default=None, description="Designs to compare. Defaults to all evaluated.")
    thresholds: dict[str, FiniteFloat] = Field(
        default_factory=dict, description="Domain-criterion thresholds by objective, original direction."
    )
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
    view: View | None = Field(default=None, description="View the design was solved in; None for imports.")
    source: Literal["solve", "import"]
    leaf_objectives: dict[str, dict[str, float]] = Field(
        default_factory=dict, description="Objective values by leaf and objective symbol."
    )


class JinaDesignInfo(JinaDesign):
    """A design of the registry with the state it was found in and its target values."""

    state_id: int = Field(description="The StateDB id of the iterate state that added the design.")
    target_values: dict[View, dict[str, float]] = Field(description="Target values by view and target symbol.")


class JinaIterateResult(BaseModel):
    """Result of one variant, pool scorer or imported row of an iterate state."""

    name: str = Field(description="Variant name, pool scorer name or 'row_<i>'.")
    success: bool
    message: str
    effective_reference_point: dict[str, float] = Field(default_factory=dict)
    target_values: dict[str, float] = Field(default_factory=dict)
    alpha: float | None = Field(default=None)
    binding: list[str] = Field(default_factory=list)
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


class JinaIterateStateResult(BaseModel):
    """Contents of a JINA iterate state."""

    kind: Literal["jina.iterate"]
    setup_state_id: int
    mode: Literal["solve", "pool", "import"]
    view: View | None
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
    reference_point: dict[str, float] | None
    outcomes: dict[int, dict[str, LeafOutcome]]


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


class JinaAnalysisResponse(BaseModel):
    """Robustness metrics of evaluated designs, by design id."""

    domain_criterion: dict[int, DomainCriterion]
    antifragility: dict[int, Antifragility] | None = Field(
        default=None, description="None when the setup has no baseline leaf in the evaluated outcomes."
    )
    antifragile_objectives: list[str] | None = None
