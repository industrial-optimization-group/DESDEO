"""A selection of utilities for handling routers and data therein.

NOTE: No routers should be defined in this file!
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, HTTPException, status
from numpy import allclose
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    ENautilusStepRequest,
    Group,
    InteractiveSessionDB,
    NautilusNavigatorInitRequest,
    NautilusNavigatorNavigateRequest,
    ProblemDB,
    RPMSolveRequest,
    SavedSolutionReference,
    ScenarioModelDB,
    SolutionReference,
    StateDB,
    User,
    UserRole,
    UserSavedSolutionDB,
)
from desdeo.api.models.cumulus import ProblemModification
from desdeo.api.models.generic_states import StateKind
from desdeo.api.models.problem import (
    ForestProblemMetaData,
    ProblemMetaDataDB,
    RepresentativeNonDominatedSolutions,
    SiteSelectionMetaData,
    SolutionDescriptionMetaData,
    SolverSelectionMetadata,
)
from desdeo.api.models.session import CreateSessionRequest
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.problem import Problem
from desdeo.problem.schema import (
    Constant,
    Constraint,
    ExtraFunction,
    Objective,
    ScalarizationFunction,
    TensorConstant,
    TensorVariable,
    Variable,
)
from desdeo.problem.utils import ProblemUtilsError, add_soft_constraint
from desdeo.tools import guess_best_solver
from desdeo.tools.robust import add_weighted_scenarios, add_worst_case_robust
from desdeo.tools.scenarios import build_combined_scenario_problem
from desdeo.tools.stochastic import add_conditional_value_at_risk, add_expected_value
from desdeo.tools.utils import payoff_table_method


def copy_problem_metadata(source_problem_db: ProblemDB, target_problem_db: ProblemDB, db_session: Session) -> None:
    """Copy all ProblemMetaDataDB entries from source to target.

    target_problem_db must already have a valid id (i.e. committed and refreshed).
    Does nothing if the source has no metadata.
    """
    db_session.refresh(source_problem_db)
    source_meta = source_problem_db.problem_metadata
    if source_meta is None:
        return

    new_meta = ProblemMetaDataDB(problem_id=target_problem_db.id, problem=target_problem_db)
    db_session.add(new_meta)
    db_session.commit()
    db_session.refresh(new_meta)

    for item in source_meta.forest_metadata or []:
        db_session.add(
            ForestProblemMetaData(
                metadata_id=new_meta.id,
                map_json=item.map_json,
                schedule_dict=item.schedule_dict,
                years=item.years,
                stand_id_field=item.stand_id_field,
                stand_descriptor=item.stand_descriptor,
                compensation=item.compensation,
            )
        )
    for item in source_meta.representative_nd_metadata or []:
        db_session.add(
            RepresentativeNonDominatedSolutions(
                metadata_id=new_meta.id,
                solution_data=item.solution_data,
                ideal=item.ideal,
                nadir=item.nadir,
            )
        )
    for item in source_meta.solver_selection_metadata or []:
        db_session.add(
            SolverSelectionMetadata(
                metadata_id=new_meta.id,
                solver_string_representation=item.solver_string_representation,
            )
        )
    for item in source_meta.site_selection_metadata or []:
        db_session.add(
            SiteSelectionMetaData(
                metadata_id=new_meta.id,
                sites_json=item.sites_json,
                nodes_json=item.nodes_json,
                travel_time_matrix_json=item.travel_time_matrix_json,
                site_variable_symbols=item.site_variable_symbols,
                coverage_variable_symbols=item.coverage_variable_symbols,
                coverage_threshold=item.coverage_threshold,
            )
        )
    for item in source_meta.solution_description_metadata or []:
        raw_parts = [p.model_dump() if hasattr(p, "model_dump") else p for p in (item.parts or [])]
        db_session.add(
            SolutionDescriptionMetaData(
                metadata_id=new_meta.id,
                parts=raw_parts,
                separator=item.separator,
            )
        )


def _apply_soft_constraints(problem: Problem, mods: ProblemModification) -> Problem:
    for soft_spec in mods.soft_constraints or []:
        constraint = next(
            (c for c in (problem.constraints or []) if c.symbol == soft_spec.constraint_symbol),
            None,
        )
        if constraint is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Constraint '{soft_spec.constraint_symbol}' not found in the problem.",
            )
        try:
            problem, _ = add_soft_constraint(
                problem,
                constraint,
                symbol=soft_spec.violation_symbol,
                lte_violation_symbol=soft_spec.lte_violation_symbol,
                gte_violation_symbol=soft_spec.gte_violation_symbol,
            )
        except ProblemUtilsError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return problem


def _apply_uncertainty_measures(problem: Problem, mods: ProblemModification, db_session: Session) -> Problem:
    specs = mods.uncertainty_measures or []
    sm_ids = {spec.scenario_model_id for spec in specs}
    if len(sm_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="All uncertainty measures in a single request must reference the same scenario_model_id.",
        )
    sm_id = next(iter(sm_ids))
    scenario_model_db = db_session.get(ScenarioModelDB, sm_id)
    if scenario_model_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ScenarioModelDB with id={sm_id} not found.",
        )
    scenario_model = scenario_model_db.to_scenario_model(base_problem=problem)
    combined, symbol_maps = build_combined_scenario_problem(scenario_model)

    for spec in specs:
        if spec.measure_type == "conditional_value_at_risk" and spec.alpha is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="'alpha' is required for 'conditional_value_at_risk'.",
            )
        if spec.measure_type == "weighted_scenarios" and spec.leaf_weights is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="'leaf_weights' is required for 'weighted_scenarios'.",
            )
        try:
            if spec.measure_type == "expected_value":
                combined, _ = add_expected_value(
                    scenario_model,
                    spec.symbols,
                    prefix=spec.prefix or "E_",
                    combined=combined,
                    symbol_maps=symbol_maps,
                )
            elif spec.measure_type == "worst_case_robust":
                combined, _ = add_worst_case_robust(
                    scenario_model,
                    spec.symbols,
                    prefix=spec.prefix or "robust_",
                    combined=combined,
                    symbol_maps=symbol_maps,
                )
            elif spec.measure_type == "conditional_value_at_risk":
                combined, _ = add_conditional_value_at_risk(
                    scenario_model,
                    spec.symbols,
                    alpha=spec.alpha,
                    cvar_prefix=spec.prefix or "CVAR_",
                    combined=combined,
                    symbol_maps=symbol_maps,
                )
            elif spec.measure_type == "weighted_scenarios":
                combined, _ = add_weighted_scenarios(
                    scenario_model,
                    spec.symbols,
                    weights=spec.leaf_weights,
                    prefix=spec.prefix or "weighted_",
                    combined=combined,
                    symbol_maps=symbol_maps,
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to apply uncertainty measure '{spec.measure_type}': {e}",
            ) from e

    # Run the payoff table synchronously so the combined problem already has correct
    # ideal/nadir when it is saved to the database. Combined objectives are new symbols
    # with no bounds; we can't safely inherit from the originals.
    # If the payoff table fails (e.g. an unsupported problem structure), continue
    # without bounds — the background task will retry and record the error.
    try:
        solver = guess_best_solver(combined)
        estimated_ideal, estimated_nadir = payoff_table_method(combined, solver=solver)
        updated_objectives = [
            obj.model_copy(
                update={
                    "ideal": estimated_ideal.get(obj.symbol, obj.ideal),
                    "nadir": estimated_nadir.get(obj.symbol, obj.nadir),
                }
            )
            for obj in combined.objectives
        ]
        combined = combined.model_copy(update={"objectives": updated_objectives})
    except Exception:  # noqa: S110
        pass

    return combined


def _parse_and_merge_elements(
    problem: Problem,
    mods: ProblemModification,
    symbol_to_type: dict,
    symbols_to_remove: set[str],
) -> dict:
    """Parse mods elements, merge them into the existing problem lists, and filter removals.

    Returns a dict suitable for passing to ``problem.model_copy(update=...)``.
    """

    def _parse_variable(d: dict) -> Variable | TensorVariable:
        if "shape" in d:
            return TensorVariable.model_validate(d, by_name=True)
        return Variable.model_validate(d, by_name=True)

    def _parse_constant(d: dict) -> Constant | TensorConstant:
        if "shape" in d:
            return TensorConstant.model_validate(d, by_name=True)
        return Constant.model_validate(d, by_name=True)

    type_parsers = {
        "variables": _parse_variable,
        "constants": _parse_constant,
        "objectives": lambda d: Objective.model_validate(d, by_name=True),
        "constraints": lambda d: Constraint.model_validate(d, by_name=True),
        "extra_funcs": lambda d: ExtraFunction.model_validate(d, by_name=True),
        "scalarization_funcs": lambda d: ScalarizationFunction.model_validate(d, by_name=True),
    }
    mod_fields = [
        ("variables", mods.variables),
        ("constants", mods.constants),
        ("objectives", mods.objectives),
        ("constraints", mods.constraints),
        ("extra_funcs", mods.extra_funcs),
        ("scalarization_funcs", mods.scalarization_funcs),
    ]

    parsed_mods: dict[str, list] = {k: [] for k in type_parsers}
    for field_name, raw_list in mod_fields:
        if not raw_list:
            continue
        for raw in raw_list:
            raw_dict = raw if isinstance(raw, dict) else raw.model_dump()
            try:
                element = type_parsers[field_name](raw_dict)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Failed to parse '{field_name}' element: {e}",
                ) from e
            sym = element.symbol
            if sym in symbol_to_type and symbol_to_type[sym] != field_name:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Symbol '{sym}' already exists as type '{symbol_to_type[sym]}';"
                        f" cannot modify it as '{field_name}'."
                    ),
                )
            parsed_mods[field_name].append(element)

    def _merge(existing: list, new_elements: list) -> list:
        by_symbol = {e.symbol: e for e in existing}
        for elem in new_elements:
            by_symbol[elem.symbol] = elem
        return list(by_symbol.values())

    def _keep(e) -> bool:
        return e.symbol not in symbols_to_remove

    new_variables = [e for e in _merge(problem.variables, parsed_mods["variables"]) if _keep(e)]
    new_objectives = [e for e in _merge(problem.objectives, parsed_mods["objectives"]) if _keep(e)]
    new_constants = [e for e in _merge(problem.constants or [], parsed_mods["constants"]) if _keep(e)] or None
    new_constraints = [e for e in _merge(problem.constraints or [], parsed_mods["constraints"]) if _keep(e)] or None
    new_extra_funcs = [e for e in _merge(problem.extra_funcs or [], parsed_mods["extra_funcs"]) if _keep(e)] or None

    # Scalarization functions may have None symbols; only named ones are merged/removed by symbol
    existing_named_scal = {s.symbol: s for s in (problem.scalarization_funcs or []) if s.symbol is not None}
    existing_unnamed_scal = [s for s in (problem.scalarization_funcs or []) if s.symbol is None]
    for s in parsed_mods["scalarization_funcs"]:
        if s.symbol is not None:
            existing_named_scal[s.symbol] = s
        else:
            existing_unnamed_scal.append(s)
    new_scal_funcs = ([s for s in existing_named_scal.values() if _keep(s)] + existing_unnamed_scal) or None

    return {
        "variables": new_variables,
        "constants": new_constants,
        "objectives": new_objectives,
        "constraints": new_constraints,
        "extra_funcs": new_extra_funcs,
        "scalarization_funcs": new_scal_funcs,
    }


def apply_problem_modifications(problem: Problem, mods: ProblemModification, db_session: Session) -> Problem:
    """Apply a ProblemModification spec to a Problem and return the modified result.

    Operations are applied in this order:
    1. Validate ``remove`` symbols.
    2. Parse and type-check incoming element modifications.
    3. Merge additions/replacements into the existing element lists.
    4. Filter removed symbols.
    5. Rebuild the problem via ``model_copy``.
    6. Apply soft-constraint transformations.
    7. Expand and apply uncertainty-measure aggregates.

    Args:
        problem: the current Problem instance to modify.
        mods: the modification specification from the request.
        db_session: an active database session (needed for uncertainty-measure look-ups).

    Raises:
        HTTPException 404: a referenced ScenarioModelDB does not exist.
        HTTPException 422: any validation, parse, or conflict error.

    Returns:
        The modified Problem instance.
    """
    symbol_to_type = problem.get_symbol_type_map()

    symbols_to_remove: set[str] = set()
    for sym in mods.remove or []:
        if sym not in symbol_to_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Symbol '{sym}' does not exist in the problem and cannot be removed.",
            )
        symbols_to_remove.add(sym)

    updates = _parse_and_merge_elements(problem, mods, symbol_to_type, symbols_to_remove)
    try:
        modified_problem = problem.model_copy(update=updates)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    modified_problem = _apply_soft_constraints(modified_problem, mods)

    if mods.uncertainty_measures:
        modified_problem = _apply_uncertainty_measures(modified_problem, mods, db_session)

    return modified_problem


RequestType = (
    RPMSolveRequest
    | ENautilusStepRequest
    | CreateSessionRequest
    | NautilusNavigatorInitRequest
    | NautilusNavigatorNavigateRequest
)


def fetch_problem_with_role_check(user: User, problem_id: int, session: Session) -> ProblemDB | None:
    """Fetch a ProblemDB by id, bypassing ownership for analysts and admins.

    Args:
        user (User): the requesting user.
        problem_id (int): id of the problem to fetch.
        session (Session): the database session.

    Returns:
        ProblemDB | None: the matching problem, or None if not found.
    """
    if user.role in (UserRole.analyst, UserRole.admin):
        statement = select(ProblemDB).where(ProblemDB.id == problem_id)
        return session.exec(statement).first()

    # Primary access path for non-analyst/admin users: own problems.
    statement = select(ProblemDB).where(
        ProblemDB.user_id == user.id,
        ProblemDB.id == problem_id,
    )
    own_problem = session.exec(statement).first()
    if own_problem is not None:
        return own_problem

    # Secondary access path: problems attached to groups where the user is owner/member.
    group_statement = select(Group).where(Group.problem_id == problem_id)
    groups = session.exec(group_statement).all()
    for group in groups:
        user_ids = group.user_ids or []
        if user.id == group.owner_id or user.id in user_ids:
            return session.exec(select(ProblemDB).where(ProblemDB.id == problem_id)).first()

    return None


def fetch_interactive_session_with_role_check(user: User, session_id: int, session: Session) -> InteractiveSessionDB:
    """Fetch an InteractiveSessionDB by id, bypassing ownership for analysts and admins.

    Args:
        user (User): the requesting user.
        session_id (int): id of the interactive session to fetch.
        session (Session): the database session.

    Raises:
        HTTPException: when the session is not found (or not owned by the user for non-analysts).

    Returns:
        InteractiveSessionDB: the matching session.
    """
    if user.role in (UserRole.analyst, UserRole.admin):
        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.id == session_id)
    else:
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == session_id,
            InteractiveSessionDB.user_id == user.id,
        )
    result = session.exec(statement).first()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find interactive session with id={session_id}.",
        )
    return result


def fetch_interactive_session(
    user: User,
    session: Session,
    request: RequestType | None = None,
    session_id: int | None = None,
) -> InteractiveSessionDB | None:
    """Gets the desired instance of `InteractiveSessionDB`.

    Args:
        user (User): the user whose interactive sessions are to be queried.
        request (RequestType): the request with possibly information on which interactive session to query.
        session (Session): the database session (not to be confused with the interactive session) from
            which the interactive session should be queried.
        session_id (int): the id of a session

    Note:
        If no explicit `session_id` is given in `request`, this function will try to fetch the
        currently active interactive session for the `user`, e.g., with id `user.active_session_id`.
        If this is `None`, then the interactive session returned will be `None` as well.

    Raises:
        HTTPException: when an explicit interactive session is requested, but it is not found.

    Returns:
        InteractiveSessionDB | None: an interactive session DB model, or nothing.
    """
    # session_id param has highest priority
    actual_session_id = session_id or (getattr(request, "session_id", None) if request else None)

    if actual_session_id is not None:
        # specific interactive session id is given, try using that
        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.id == actual_session_id)
        interactive_session = session.exec(statement).first()

        if interactive_session is None:
            # Raise if explicitly requested interactive session cannot be found
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={actual_session_id}.",
            )
    else:
        if user.active_session_id is None:
            return None
        # actual_session_id is None
        # try to use active session instead

        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.id == user.active_session_id)
        interactive_session = session.exec(statement).first()

    # At this point interactive_session is either an instance of InteractiveSessionDB or None (which is fine)

    return interactive_session


def fetch_user_problem(user: User, request: RequestType, session: Session) -> ProblemDB | None:
    """Fetches a user's `ProblemDB` based on the id in the given request.

    Args:
        user (User): the user for which the problem is fetched.
        request (RequestType): request containing details of the problem to be fetched (`request.problem_id`).
        session (Session): the database session from which to fetch the problem.

    Raises:
        HTTPException: a problem with the given id (`request.problem_id`) could not be found (404).

    Returns:
        Problem: the instance of `ProblemDB` with the given id.
    """
    if request.problem_id is None:
        return None

    statement = select(ProblemDB).where(
        ProblemDB.user_id == user.id,
        ProblemDB.id == request.problem_id,
    )
    return session.exec(statement).first()


def fetch_parent_state(
    user: User,
    request: RequestType,
    session: Session,
    interactive_session: InteractiveSessionDB | None = None,
) -> StateDB | None:
    """Fetches the parent state, if an id is given, or if defined in the given interactive session.

    Determines the appropriate parent `StateDB` instance to associate with a new
    state or operation. It first checks whether the `request` explicitly
    provides a `parent_state_id`. If so, it attempts to retrieve the
    corresponding `StateDB` entry from the database. If no such id is provided,
    the function defaults to returning the most recently added state from the
    given `interactive_session`, if available. If neither source provides a
    parent state, `None` is returned.

    Args:
    user (User): the user for which the parent state is fetched.
    request (RequestType): request containing details about the parent state and optionally the
        interactive session.
    session (Session): the database session from which to fetch the parent state.
    interactive_session (InteractiveSessionDB | None, optional): the interactive session containing
        information about the parent state. Defaults to None.

    Raises:
    HTTPException: when `request.parent_state_id` is not `None` and a `StateDB` with this id cannot
        be found in the given database session.

    Returns:
        StateDB | None: if `request.parent_state_id` is given, returns the corresponding `StateDB`.
            If it is not given, returns the latest state defined in `interactive_session.states`.
            If both `request.parent_state_id` and `interactive_session` are `None`, then returns `None`.
    """
    if request.parent_state_id is None:
        # parent state is assumed to be the last sate added to the session.
        # if `interactive_session` is None, then parent state is set to None.
        return interactive_session.states[-1] if interactive_session and interactive_session.states else None

    # request.parent_state_id is not None
    statement = select(StateDB).where(StateDB.id == request.parent_state_id)
    parent_state = session.exec(statement).first()

    # this error is raised because if a parent_state_id is given, it is assumed that the
    # user wished to use that state explicitly as the parent.
    if parent_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find state with id={request.parent_state_id}",
        )

    return parent_state


def iter_states_of_kinds(
    problem_id: int,
    session_id: int | None,
    db_session: Session,
    kinds: tuple[StateKind, ...],
):
    """Yield resolved substates (newest first) for *problem_id*/*session_id* whose kind is in *kinds*."""
    statement = (
        select(StateDB)
        .where(StateDB.problem_id == problem_id, StateDB.session_id == session_id)
        .order_by(StateDB.id.desc())
    )
    for state_db in db_session.exec(statement).all():
        if state_db.base_state is not None and state_db.base_state.kind in kinds:
            yield state_db.state


class ContextField(StrEnum):
    """Enum class to specify context fields."""

    PROBLEM = "problem_db"
    INTERACTIVE_SESSION = "interactive_session"
    PARENT_STATE = "parent_state"


@dataclass(frozen=True)
class SessionContext:
    """A generic context to be used in various endpoints."""

    user: User
    db_session: Session
    problem_db: ProblemDB | None = None
    interactive_session: InteractiveSessionDB | None = None
    parent_state: StateDB | None = None


class SessionContextGuard:
    """FastAPI dependency that builds a SessionContext and validates required fields.

    Use ``.post`` for POST endpoints (accepts a request body),
    ``.get`` for GET endpoints (path/query params only), and
    ``.delete`` for DELETE endpoints (path/query params only).

    Calling the guard directly (via ``__call__``) is not allowed and will
    raise an error immediately.
    """

    def __init__(self, require: Iterable[ContextField] | None = None):
        """Init method for the SessionContextGuard class.

        Args:
            require (Iterable[ContextField] | None, optional): fields that the guard will check
                are included in the request. Defaults to None.
        """
        self.require = set(require or [])

    def __call__(self, *args, **kwargs):
        """Direct invocation is not allowed. Use .post, .get, or .delete instead."""
        raise RuntimeError(
            "SessionContextGuard must not be called directly. "
            "Use Depends(SessionContextGuard(...).post), "
            "Depends(SessionContextGuard(...).get), or "
            "Depends(SessionContextGuard(...).delete) instead."
        )

    def post(
        self,
        user: Annotated[User, Depends(get_current_user)],
        db_session: Annotated[Session, Depends(get_session)],
        request: RequestType | None = None,
        problem_id: int | None = None,
    ) -> SessionContext:
        """Dependency for POST endpoints. Accepts a request body (RequestType)."""
        problem_db = None
        interactive_session = None
        parent_state = None

        if request is not None:
            if hasattr(request, "problem_id") and request.problem_id is not None:
                problem_db = fetch_problem_with_role_check(user, request.problem_id, db_session)

            if problem_db is None and problem_id is not None:
                problem_db = fetch_problem_with_role_check(user, problem_id, db_session)

            if hasattr(request, "interactive_session_id") or hasattr(request, "problem_id"):
                interactive_session = fetch_interactive_session(user, db_session, request)

            if hasattr(request, "parent_state_id") or hasattr(request, "problem_id"):
                parent_state = fetch_parent_state(
                    user,
                    request,
                    db_session,
                    interactive_session=interactive_session,
                )
        elif problem_id is not None:
            problem_db = fetch_problem_with_role_check(user, problem_id, db_session)

        context = SessionContext(
            user=user,
            db_session=db_session,
            problem_db=problem_db,
            interactive_session=interactive_session,
            parent_state=parent_state,
        )

        self._validate(context)
        return context

    def get(
        self,
        user: Annotated[User, Depends(get_current_user)],
        db_session: Annotated[Session, Depends(get_session)],
        problem_id: int | None = None,
        session_id: int | None = None,
    ) -> SessionContext:
        """Dependency for GET endpoints. No request body — only path/query params."""
        problem_db = None
        interactive_session = None

        if problem_id is not None:
            problem_db = fetch_problem_with_role_check(user, problem_id, db_session)

        if session_id is not None or (problem_id is not None):
            interactive_session = fetch_interactive_session(
                user,
                db_session,
                session_id=session_id,
            )

        context = SessionContext(
            user=user,
            db_session=db_session,
            problem_db=problem_db,
            interactive_session=interactive_session,
        )

        self._validate(context)
        return context

    def delete(
        self,
        user: Annotated[User, Depends(get_current_user)],
        db_session: Annotated[Session, Depends(get_session)],
        problem_id: int | None = None,
        session_id: int | None = None,
    ) -> SessionContext:
        """Dependency for DELETE endpoints. No request body — delegates to .get logic."""
        return self.get(user=user, db_session=db_session, problem_id=problem_id, session_id=session_id)

    def _validate(self, context: SessionContext) -> None:
        """Ensure required fields exist."""
        for field in self.require:
            if getattr(context, field.value) is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field} context missing.",
                )


def filter_duplicates(solutions: list[SavedSolutionReference]) -> list[SavedSolutionReference]:
    """Filters out the duplicate values of objectives."""
    if len(solutions) < 2:  # noqa: PLR2004
        return solutions

    objective_values_list = [sol.objective_values for sol in solutions]
    objective_keys = list(objective_values_list[0])
    valuelists = [[dictionary[key] for key in objective_keys] for dictionary in objective_values_list]
    duplicate_indices = []
    for i in range(len(solutions) - 1):
        for j in range(i + 1, len(solutions)):
            if allclose(valuelists[i], valuelists[j]):  # TODO: "similarity tolerance" from problem metadata
                duplicate_indices.append(i)

    return [sol for i, sol in enumerate(solutions) if i not in duplicate_indices]


def collect_saved_solutions(user: User, problem_id: int, session: Session) -> list[SavedSolutionReference]:
    """Collects all saved solutions for the user and problem."""
    user_saved_solutions = session.exec(
        select(UserSavedSolutionDB).where(
            UserSavedSolutionDB.problem_id == problem_id, UserSavedSolutionDB.user_id == user.id
        )
    ).all()

    saved_solutions = [SavedSolutionReference(saved_solution=saved_solution) for saved_solution in user_saved_solutions]
    return filter_duplicates(saved_solutions)


def collect_all_solutions(user: User, problem_id: int, session: Session) -> list[SolutionReference]:
    """Collects all solutions for the user and problem."""
    statement = (
        select(StateDB)
        .where(StateDB.problem_id == problem_id, StateDB.session_id == user.active_session_id)
        .order_by(StateDB.id.desc())
    )
    states = session.exec(statement).all()
    all_solutions = []
    for state in states:
        for i in range(state.state.num_solutions):
            all_solutions.append(SolutionReference(state=state, solution_index=i))

    return filter_duplicates(all_solutions)
