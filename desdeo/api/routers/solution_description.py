"""Solution description router."""

from typing import Annotated

import sympy as sp
from fastapi import APIRouter, Depends
from sqlmodel import SQLModel, select

from desdeo.api.models import (
    NIMBUSFinalState,
    NIMBUSInitializationState,
    NIMBUSSaveState,
    ProblemMetaDataDB,
    SolutionInfo,
    StateDB,
)
from desdeo.api.models.problem import DescriptionPart, SolutionDescriptionMetaData
from desdeo.api.routers.utils import SessionContext, SessionContextGuard
from desdeo.problem.json_parser import MathParser

router = APIRouter(prefix="/solution-description")


class SolutionDescriptionRequest(SQLModel):
    """Request for a solution description."""

    problem_id: int
    solution: SolutionInfo


class SolutionDescriptionResponse(SQLModel):
    """Response containing a generated solution description."""

    available: bool
    description: str


def _flatten_solver_results(results) -> dict[str, float]:
    """Extract all symbol → scalar values from a SolverResults object."""
    fields = [
        "optimal_variables",
        "optimal_objectives",
        "extra_func_values",
        "constraint_values",
        "scalarization_values",
    ]
    values: dict[str, float] = {}
    for field in fields:
        d = getattr(results, field, None)
        for k, v in (d or {}).items():
            values[k] = float(v[0]) if isinstance(v, list) else float(v)
    return values


def _extract_result_values(actual_state, solution_index: int) -> dict[str, float] | None:
    """Extract a flat dict of symbol → scalar value from a state's solver results."""
    if type(actual_state) is NIMBUSSaveState:
        variables = actual_state.result_variable_values[0]
        values: dict[str, float] = {}
        for k, v in (variables or {}).items():
            values[k] = float(v[0]) if isinstance(v, list) else float(v)
        return values

    if type(actual_state) in [NIMBUSInitializationState, NIMBUSFinalState]:
        return _flatten_solver_results(actual_state.solver_results)

    if not hasattr(actual_state, "solver_results"):
        return None
    sr = actual_state.solver_results
    if isinstance(sr, list):
        if solution_index >= len(sr) or sr[solution_index] is None:
            return None
        results = sr[solution_index]
    else:
        results = sr
    if not hasattr(results, "optimal_variables"):
        return None
    return _flatten_solver_results(results)


def _evaluate_part(part: DescriptionPart, values: dict[str, float]) -> str:
    """Render a single DescriptionPart to a string."""
    if part.text is not None:
        return part.text

    if part.symbol is not None:
        raw = values.get(part.symbol)
        if raw is None:
            return f"[unknown symbol: {part.symbol}]"
        value = raw
    elif part.expression is not None:
        parser = MathParser(to_format="sympy")
        sym_expr = parser.parse(part.expression)
        # Build the substitution dict by parsing each symbol name through the same parser so that
        # SymPy reserved names (E → Euler's number, I → imaginary unit, etc.) are handled
        # consistently between the expression tree and the substitution keys.
        sym_values = {}
        for k, v in values.items():
            try:
                sym_key = parser.parse(k)
            except Exception:
                sym_key = sp.Symbol(k)
            sym_values[sym_key] = v
        value = float(sym_expr.subs(sym_values).evalf())
    else:
        return ""

    formatted = format(value, part.format_spec) if part.format_spec else str(value)
    suffix = part.suffix or ""
    if part.label:
        return f"{part.label}: {formatted}{suffix}"
    return f"{formatted}{suffix}"


@router.post("/get")
def get_solution_description(
    request: SolutionDescriptionRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard().post)],
) -> SolutionDescriptionResponse:
    """Generate a textual description of a solution based on problem-specific metadata.

    Args:
        request: the problem and solution to describe.
        context: current session context.

    Returns:
        SolutionDescriptionResponse with the generated description, or available=False if
        no description metadata exists for this problem.
    """
    session = context.db_session
    empty = SolutionDescriptionResponse(available=False, description="")

    state_row = session.exec(select(StateDB).where(StateDB.id == request.solution.state_id)).first()
    if state_row is None or not hasattr(state_row, "state"):
        return empty

    values = _extract_result_values(state_row.state, request.solution.solution_index)
    if values is None:
        return empty

    from_db_metadata = session.exec(
        select(ProblemMetaDataDB).where(ProblemMetaDataDB.problem_id == request.problem_id)
    ).first()
    if from_db_metadata is None:
        return empty

    desc_metadata_list: list[SolutionDescriptionMetaData] = [
        m for m in from_db_metadata.all_metadata if m.metadata_type == "solution_description_metadata"
    ]
    if not desc_metadata_list:
        return empty

    desc_metadata = desc_metadata_list[-1]

    parts_text = [
        _evaluate_part(DescriptionPart(**p) if isinstance(p, dict) else p, values) for p in desc_metadata.parts
    ]
    description = desc_metadata.separator.join(parts_text)

    return SolutionDescriptionResponse(available=True, description=description)
