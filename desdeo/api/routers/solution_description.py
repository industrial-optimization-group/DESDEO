"""Solution description router."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import SQLModel, select

from desdeo.api.models import (
    NIMBUSFinalState,
    NIMBUSInitializationState,
    NIMBUSSaveState,
    ProblemDB,
    ProblemMetaDataDB,
    SolutionInfo,
    StateDB,
)
from desdeo.api.models.problem import DescriptionPart, SolutionDescriptionMetaData
from desdeo.api.routers.utils import SessionContext, SessionContextGuard
from desdeo.problem.json_parser import MathParser
from desdeo.problem.schema import Problem

router = APIRouter(prefix="/solution-description")


class SolutionDescriptionRequest(SQLModel):
    """Request for a solution description."""

    problem_id: int
    solution: SolutionInfo


class UpdateSolutionDescriptionMetaDataRequest(SQLModel):
    """Request to update the solution description metadata for a problem."""

    problem_id: int
    parts: list[DescriptionPart]
    separator: str = "\n"


class SolutionDescriptionResponse(SQLModel):
    """Response containing a generated solution description."""

    available: bool
    description: str


def _flatten_value(key: str, value, values: dict[str, float]) -> None:
    """Add one symbol → scalar entry to *values*, expanding tensors into indexed symbols.

    A list value is a tensor: its elements are also exposed as ``key_1``, ``key_2``, ...
    following DESDEO's 1-based tensor element naming, and nested lists recurse into
    ``key_1_2`` and so on. This lets a description part aggregate over a tensor, e.g.
    ``["Max", ...]`` over the hours of a schedule. The bare ``key`` keeps mapping to the
    first element, which is what a scalar wrapped in a single-element list needs.
    """
    if isinstance(value, list):
        for index, element in enumerate(value, start=1):
            _flatten_value(f"{key}_{index}", element, values)
        if value and not isinstance(value[0], list):
            values[key] = float(value[0])
    else:
        values[key] = float(value)


def _mathjson_list_to_nested(value):
    """Strip the ``"List"`` heads a stored tensor constant's values are wrapped in."""
    if isinstance(value, list) and value and value[0] == "List":
        return [_mathjson_list_to_nested(element) for element in value[1:]]
    return value


def _constant_values(problem_db: ProblemDB) -> dict[str, float]:
    """Extract symbol → value for a problem's constants, tensors expanded element by element.

    Constants are part of the problem rather than of a solution, so the solver results do not
    carry them, but a description often needs them: reporting the cost of an hour means
    multiplying that hour's decision by that hour's price.
    """
    values: dict[str, float] = {}
    for constant in problem_db.constants:
        _flatten_value(constant.symbol, constant.value, values)
    for constant in problem_db.tensor_constants:
        _flatten_value(constant.symbol, _mathjson_list_to_nested(constant.values), values)
    return values


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
            _flatten_value(k, v, values)
    return values


def _extract_result_values(actual_state, solution_index: int) -> dict[str, float] | None:
    """Extract a flat dict of symbol → scalar value from a state's solver results."""
    if type(actual_state) is NIMBUSSaveState:
        variables = actual_state.result_variable_values[0]
        values: dict[str, float] = {}
        for k, v in (variables or {}).items():
            _flatten_value(k, v, values)
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


def _substitute_values(expression, values: dict[str, float]):
    """Replace every known symbol in a MathJSON expression with its value.

    Walks the expression tree and swaps each string that names a symbol in *values* for the
    corresponding number. The head of each list is the operator and is left alone, so an
    operator can never be mistaken for a symbol. Symbols without a value are left in place
    for the parser to turn into SymPy symbols, as before.
    """
    if isinstance(expression, str):
        return values.get(expression, expression)
    if isinstance(expression, list) and expression:
        return [expression[0], *(_substitute_values(item, values) for item in expression[1:])]
    return expression


def _symbol_names(expression) -> set[str]:
    """Collect the names of every symbol in a MathJSON expression.

    Mirrors the walk in :func:`_substitute_values`: the head of each list is the operator
    and is not a symbol.
    """
    if isinstance(expression, str):
        return {expression}
    if isinstance(expression, list) and expression:
        return set().union(*(_symbol_names(item) for item in expression[1:]), set())
    return set()


def _tensor_element_symbols(symbol: str, shape: list[int]) -> list[str]:
    """List the element symbols of a tensor, e.g. ``x`` of shape ``[2, 3]`` gives ``x_1_1``..``x_2_3``."""
    symbols = [symbol]
    for dimension in shape:
        symbols = [f"{s}_{i}" for s in symbols for i in range(1, dimension + 1)]
    return symbols


def _known_symbols(problem: Problem) -> set[str]:
    """List every symbol a description part of *problem* may refer to.

    These are the symbols of the solver results — variables, objectives, constraints, extra
    functions and scalarizations — plus the problem's constants, with tensors contributing one
    symbol per element, matching how :func:`_flatten_value` names them.
    """
    symbols: set[str] = set()
    for field in ("constants", "variables", "objectives", "constraints", "extra_funcs", "scalarization_funcs"):
        for item in getattr(problem, field, None) or []:
            symbols.add(item.symbol)
            if getattr(item, "shape", None):
                symbols.update(_tensor_element_symbols(item.symbol, item.shape))
    return symbols


def validate_description_parts(parts: list[DescriptionPart], problem: Problem | None = None) -> None:
    """Check that description parts can be rendered, raising ValueError describing the first problem.

    An expression must parse, and every symbol a part refers to must be one the rendering will
    have a value for: a symbol of *problem* or one SymPy resolves on its own, such as E. A
    symbol without a value leaves the expression symbolic at render time, where it cannot be
    turned into a number. Symbols are only checked when *problem* is given.

    Args:
        parts: the description parts to check.
        problem: the problem the description belongs to, if known.

    Raises:
        ValueError: if a part cannot be rendered, with a message naming what is wrong.
    """
    known_symbols = _known_symbols(problem) if problem is not None else None
    where = f"problem {problem.name!r}" if problem is not None else "the problem"
    parser = MathParser(to_format="sympy")

    for part in parts:
        if part.symbol is not None and known_symbols is not None and part.symbol not in known_symbols:
            raise ValueError(f"Description part refers to '{part.symbol}', which is not a symbol of {where}.")

        if part.expression is None:
            continue

        # Validate the expression the same way it will later be evaluated: with the symbols
        # replaced by numbers. This checks what parsing can check — the operators and the
        # structure — without parsing a large expression symbolically, which is slow.
        placeholders = dict.fromkeys(_symbol_names(part.expression), 1.0)
        try:
            parser.parse(_substitute_values(part.expression, placeholders))
        except Exception as e:
            raise ValueError(f"Invalid expression in description part: {e}") from e

        if known_symbols is None:
            continue
        unknown = sorted(
            name
            for name in _symbol_names(part.expression) - known_symbols
            if getattr(parser.parse(name), "free_symbols", None)
        )
        if unknown:
            raise ValueError(
                f"Description part refers to {', '.join(repr(u) for u in unknown)}, "
                f"which are not symbols of {where}."
            )


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
        # The known symbols are substituted into the MathJSON tree before it is parsed, so
        # SymPy only ever sees numbers. Parsing a large expression symbolically and then
        # substituting is prohibitively slow (tens of seconds for a part that aggregates over
        # a few hundred tensor elements, as SymPy tries to simplify the symbolic tree), while
        # this is instant and gives the same value. It also sidesteps SymPy's reserved names
        # (E → Euler's number, I → imaginary unit): a symbol with a value never reaches SymPy.
        value = float(MathParser(to_format="sympy").parse(_substitute_values(part.expression, values)).evalf())
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

    # The problem's constants are available to the description too. The solution's own values
    # take precedence, so a symbol that is both never loses its solved value.
    problem_db = session.exec(select(ProblemDB).where(ProblemDB.id == request.problem_id)).first()
    if problem_db is not None:
        values = _constant_values(problem_db) | values

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


@router.post("/update_metadata")
def update_solution_description_metadata(
    request: UpdateSolutionDescriptionMetaDataRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard().post)],
) -> SolutionDescriptionMetaData:
    """Add a new solution description metadata instance for a problem.

    Validates that all expressions in the parts are parseable and only refer to symbols the
    problem's solutions provide, then appends the new metadata to the database. The most
    recent entry is used when generating descriptions, so this effectively updates what
    description is produced.

    Args:
        request: the problem id and new description metadata.
        context: current session context.

    Returns:
        The newly created SolutionDescriptionMetaData instance.
    """
    session = context.db_session

    problem_db = session.exec(select(ProblemDB).where(ProblemDB.id == request.problem_id)).first()
    try:
        validate_description_parts(
            request.parts, Problem.from_problemdb(problem_db) if problem_db is not None else None
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    problem_metadata = session.exec(
        select(ProblemMetaDataDB).where(ProblemMetaDataDB.problem_id == request.problem_id)
    ).first()
    if problem_metadata is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No metadata record found for problem {request.problem_id}.",
        )

    new_metadata = SolutionDescriptionMetaData(
        metadata_id=problem_metadata.id,
        parts=[p.model_dump(exclude_none=True) for p in request.parts],
        separator=request.separator,
        metadata_instance=problem_metadata,
    )
    session.add(new_metadata)
    session.commit()
    session.refresh(new_metadata)

    return new_metadata
