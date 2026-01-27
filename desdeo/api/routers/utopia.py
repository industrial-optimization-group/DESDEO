"""Utopia router."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import select

from desdeo.api.models import (
    ForestProblemMetaData,
    NIMBUSFinalState,
    NIMBUSInitializationState,
    NIMBUSSaveState,
    ProblemMetaDataDB,
    StateDB,
    UtopiaRequest,
    UtopiaResponse,
)
from desdeo.api.routers.utils import SessionContext, get_session_context

router = APIRouter(prefix="/utopia")

@router.post("/")
def get_utopia_data(  # noqa: C901
    request: UtopiaRequest,
    context: Annotated[SessionContext, Depends(get_session_context)],
) -> UtopiaResponse:
    """Request and receive the Utopia map corresponding to the decision variables sent.

    Args:
        request (UtopiaRequest): the set of decision variables and problem for which the utopia forest map is requested
            for.
        context (Annotated[SessionContext, Depends(get_session_context)]): the current session context

    Raises:
        HTTPException:
    Returns:
        UtopiaResponse: the map for the forest, to be rendered in frontend
    """
    session = context.db_session

    empty_response = UtopiaResponse(is_utopia=False, map_name="", map_json={}, options={}, description="", years=[])

    state = session.exec(select(StateDB).where(StateDB.id == request.solution.state_id)).first()
    if state is None or not hasattr(state, "state"):
        return empty_response

    actual_state = state.state

    if type(actual_state) is NIMBUSSaveState:
        decision_variables = actual_state.result_variable_values[0]

    elif type(actual_state) in [NIMBUSInitializationState, NIMBUSFinalState]:
        decision_variables = actual_state.solver_results.optimal_variables

    else:
        # Check if solver_results exists and has the needed index
        if (
            not hasattr(actual_state, "solver_results")
            or request.solution.solution_index >= len(actual_state.solver_results)
            or actual_state.solver_results[request.solution.solution_index] is None
        ):
            return empty_response

        result = actual_state.solver_results[request.solution.solution_index]
        if not hasattr(result, "optimal_variables") or not result.optimal_variables:
            return empty_response
        decision_variables = result.optimal_variables  # expects a list of variables, won't work without.

    from_db_metadata = session.exec(
        select(ProblemMetaDataDB).where(ProblemMetaDataDB.problem_id == request.problem_id)
    ).first()
    if from_db_metadata is None:
        return empty_response

    # Get the last instance of forest related metadata from the database.
    # If for some reason there's more than one forest metadata, return the latest.
    forest_metadata: ForestProblemMetaData = [
        metadata for metadata in from_db_metadata.all_metadata if metadata.metadata_type == "forest_problem_metadata"
    ][-1]
    if forest_metadata is None:
        return empty_response

    # Figure out the treatments from the decision variables and utopia data

    def treatment_index(part: str) -> str:
        if "clearcut" in part:
            return 1
        if "below" in part:
            return 2
        if "above" in part:
            return 3
        if "even" in part:
            return 4
        if "first" in part:
            return 5
        return -1

    treatments_dict = {}
    for key in decision_variables:
        if not key.startswith("X"):
            continue
        # The dict keys get converted to ints to strings when it's loaded from database
        try:
            treatments = forest_metadata.schedule_dict[key][str(decision_variables[key].index(1))]
        except ValueError:
            # if the optimization didn't choose any decision alternative, it's safe to assume
            #  that nothing is being done at that forest stand
            treatments = forest_metadata.schedule_dict[key]["0"]
            # print(e)
        treatments_dict[key] = {forest_metadata.years[0]: 0, forest_metadata.years[1]: 0, forest_metadata.years[2]: 0}
        for year in treatments_dict[key]:
            if year in treatments:
                for part in treatments.split():
                    if year in part:
                        treatments_dict[key][year] = treatment_index(part)

    # Create the options for the webui

    treatment_colors = {
        0: "#4daf4a",
        1: "#e41a1c",
        2: "#984ea3",
        3: "#e3d802",
        4: "#ff7f00",
        5: "#377eb8",
    }

    description_dict = {
        0: "Do nothing",
        1: "Clearcut",
        2: "Thinning from below",
        3: "Thinning from above",
        4: "Even thinning",
        5: "First thinning",
    }

    map_name = "ForestMap"  # This isn't visible anywhere on the ui

    options = {}
    for year in forest_metadata.years:
        options[year] = {
            "tooltip": {
                "trigger": "item",
                "showDelay": 0,
                "transitionDuration": 0.2,
            },
            "visualMap": {  # // vis eg. stock levels
                "left": "right",
                "showLabel": True,
                "type": "piecewise",  # // for different plans
                "pieces": [],
                "text": ["Management plans"],
                "calculable": True,
            },
            # // predefined symbols for visumap'circle': 'rect': 'roundRect': 'triangle': 'diamond': 'pin':'arrow':
            # // can give custom svgs also
            "toolbox": {
                "show": True,
                #   //orient: 'vertical',
                "left": "left",
                "top": "top",
                "feature": {
                    "dataView": {"readOnly": True},
                    "restore": {},
                    "saveAsImage": {},
                },
            },
            # // can draw graphic components to indicate different things at least
            "series": [
                {
                    "name": year,
                    "type": "map",
                    "roam": True,
                    "map": map_name,
                    "nameProperty": forest_metadata.stand_id_field,
                    "label": {
                        "show": False  # Hide text labels on the map
                    },
                    # "colorBy": "data",
                    # "itemStyle": {"symbol": "triangle", "color": "red"},
                    "data": [],
                    "nameMap": {},
                }
            ],
        }

        for key in decision_variables:
            if not key.startswith("X"):
                continue
            stand = int(forest_metadata.schedule_dict[key]["unit"])
            treatment_id = treatments_dict[key][year]
            piece = {
                "value": treatment_id,
                "symbol": "circle",
                "label": description_dict[treatment_id],
                "color": treatment_colors[treatment_id],
            }
            if piece not in options[year]["visualMap"]["pieces"]:
                options[year]["visualMap"]["pieces"].append(piece)
            if forest_metadata.stand_descriptor:
                name = forest_metadata.stand_descriptor[str(stand)] + description_dict[treatment_id]
            else:
                name = "Stand " + str(stand) + " " + description_dict[treatment_id]
            options[year]["series"][0]["data"].append(
                {
                    "name": name,
                    "value": treatment_id,
                }
            )
            options[year]["series"][0]["nameMap"][stand] = name

    # Let's also generate a nice description for the map
    map_description = (
        f"Income from harvesting in the first period {int(decision_variables['P_1'])}€.\n"
        + f"Income from harvesting in the second period {int(decision_variables['P_2'])}€.\n"
        + f"Income from harvesting in the third period {int(decision_variables['P_3'])}€.\n"
        + f"The discounted value of the remaining forest at the end of the plan {int(decision_variables['V_end'])}€."
    )

    return UtopiaResponse(
        is_utopia=True,
        map_name=map_name,
        options=options,
        map_json=json.loads(forest_metadata.map_json),
        description=map_description,
        years=forest_metadata.years,
    )
