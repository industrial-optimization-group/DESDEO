"""Generic helpers for fixing a subset of a Problem's variables and re-evaluating it.

Used by multi-stage / here-and-now-vs-recourse workflows: given a deterministic `Problem` and a
chosen value for some of its variables (typically the "strategic"/first-stage ones), produce a
new `Problem` with those values pinned via equality constraints, then re-evaluate it.

Two re-evaluations are offered, and the choice between them is a modelling decision, not a
performance one:

- `payoff_ideal_or_none` solves each objective independently and returns the fixed-design
  problem's **ideal point**. Each of its values comes from a different setting of the remaining
  (recourse) variables, so the vector it returns is generally not attainable by any single
  recourse decision — it is a per-objective bound.
- `asf_at_reference_point` solves **once**, against a decision maker's reference point, and
  returns the objective vector of one actually-achievable recourse decision. This is what
  "how does this design perform in this scenario" means when the answer has to be a plan.

Ported from a decision maker's own `pairwise_matrix_pipeline.py` (`fix_strategic_design`,
`solve_single_objectives`) — already formulation-agnostic (they operate purely on the `Problem`
schema, no domain-specific logic), just living in a project-specific module.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from desdeo.problem.schema import Constraint, ConstraintTypeEnum, Problem
from desdeo.tools.utils import payoff_table_method

if TYPE_CHECKING:
    from collections.abc import Callable

    from desdeo.tools.generics import SolverResults


def _safe_symbol(text: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", str(text))


def fix_variables(problem: Problem, values: dict[str, float], label: str) -> Problem:
    """Return a copy of `problem` with the given variables fixed to `values`.

    Adds one equality constraint per symbol (`{sym} - (value) == 0`) as an infix string, which
    DESDEO parses regardless of whether the rest of the problem's constraints are infix strings
    or MathJSON lists.

    Args:
        problem: the deterministic `Problem` to fix variables in.
        values: `{symbol: value}` for the variables to fix.
        label: a short, unique tag used in the new constraints'/problem's names (sanitized to a
            safe symbol suffix).

    Returns:
        A new `Problem` with the extra fixing constraints, carrying over `problem`'s ideal/nadir
        if it has them.
    """
    safe_lbl = _safe_symbol(label)
    new_constraints = [
        *problem.constraints,
        *(
            Constraint(
                name=f"fix {sym} [{label}]",
                symbol=f"fix_{_safe_symbol(sym)}_{safe_lbl}",
                func=f"{sym} - ({float(value)})",
                cons_type=ConstraintTypeEnum.EQ,
                is_linear=True,
            )
            for sym, value in values.items()
        ),
    ]
    p_fixed = Problem(
        name=f"{problem.name} | {safe_lbl}",
        description=problem.description,
        variables=list(problem.variables),
        constants=list(problem.constants),
        objectives=list(problem.objectives),
        constraints=new_constraints,
    )
    try:
        ideal = problem.get_ideal_point()
        nadir = problem.get_nadir_point()
        if ideal is not None and nadir is not None:
            p_fixed = p_fixed.update_ideal_and_nadir(ideal, nadir)
    except Exception:  # noqa: BLE001
        pass
    return p_fixed


def payoff_ideal_or_none(
    problem: Problem,
    solver: "Callable[[Problem], SolverResults] | type",
    objective_symbols: list[str],
) -> tuple[dict[str, float | None], str]:
    """Solve one single-objective LP per objective on a fixed-variable problem.

    `payoff_table_method` minimizes each objective independently and returns the ideal point —
    i.e. the best each objective can achieve given the fixed variable values (e.g. a fixed
    first-stage design under one scenario). A design fixed into a scenario it genuinely cannot
    operate under makes the LP infeasible; `payoff_table_method` doesn't raise on that, the
    underlying solvers report `SolverResults(success=False, ...)` with every objective set to
    NaN, and `payoff_table_method` reads `optimal_objectives` without checking `success` — so
    that's caught here explicitly, rather than reported as `"ok"` with silent NaNs.

    Returns:
        (`{objective_symbol: value}` or all-`None` on failure, `"ok"` or a status/error string).
    """
    try:
        ideal, _ = payoff_table_method(problem=problem, solver=solver)
    except Exception as e:  # noqa: BLE001
        return {obj: None for obj in objective_symbols}, str(e)

    values = {obj: float(ideal[obj]) for obj in objective_symbols}
    if any(v != v for v in values.values()):  # NaN != NaN
        msg = (
            "infeasible (the underlying solve did not reach optimality -- these fixed variable "
            "values likely cannot operate feasibly under this scenario)"
        )
        return {obj: None for obj in objective_symbols}, msg
    return values, "ok"


def asf_weights_from_ideal_nadir(
    ideal: dict[str, float],
    nadir: dict[str, float],
    objective_symbols: list[str],
) -> dict[str, float]:
    """`|nadir - ideal|` per objective, the standard ASF normalization.

    Pass a *global* ideal/nadir (one shared range per objective) rather than each fixed-design
    problem's own when the point of the exercise is to compare many (design, scenario) pairs:
    a per-pair normalization silently puts every row on a different scale. A degenerate range
    falls back to 1.0, since the ASF requires strictly positive weights.
    """
    weights = {}
    for obj in objective_symbols:
        span = abs(float(nadir[obj]) - float(ideal[obj]))
        weights[obj] = span if span > 0 else 1.0
    return weights


def asf_at_reference_point(
    problem: Problem,
    solver: "Callable[[Problem], SolverResults] | type",
    objective_symbols: list[str],
    reference_point: dict[str, float],
    weights: dict[str, float],
    label: str = "eval",
    rho: float = 1e-3,
) -> tuple[dict[str, float | None], str]:
    """Solve one achievement-scalarizing-function problem on a fixed-variable problem.

    Returns the objective vector of the single achievable solution the ASF selects for
    `reference_point` — the alternative to `payoff_ideal_or_none`, whose four independent solves
    return an ideal point no one recourse decision attains. See this module's docstring.

    Args:
        problem: the problem with the first-stage variables already fixed (`fix_variables`).
        solver: solver factory, called as `solver(scalarized_problem)`.
        objective_symbols: which objectives to read back off the solution.
        reference_point: aspiration level per objective symbol, in raw units. Only objectives
            listed here are scalarized, so it should normally cover `objective_symbols`.
        weights: strictly positive per-objective normalization, e.g. from
            `asf_weights_from_ideal_nadir`. Passed explicitly rather than defaulted from the
            problem's own ideal/nadir, which a fixed-design scenario problem often lacks.
        label: short unique tag for the added scalarization function's symbol.
        rho: augmentation coefficient.

    Returns:
        (`{objective_symbol: value}` or all-`None` on failure, `"ok"` or a status/error string).
    """
    from desdeo.tools.partial_scalarization import add_asf_partial_diff

    try:
        scalarized, target = add_asf_partial_diff(
            problem,
            f"ASF_{_safe_symbol(label)}",
            reference_point,
            weights=weights,
            weights_aug=weights,
            rho=rho,
        )
        result = solver(scalarized).solve(target)
    except Exception as e:  # noqa: BLE001
        return {obj: None for obj in objective_symbols}, str(e)

    # A solver result carries `success`, so unlike the payoff-table path infeasibility is
    # reported directly rather than inferred from NaNs. Both are still checked: a solver can
    # report success and still hand back NaNs.
    if not result.success:
        return {obj: None for obj in objective_symbols}, (
            f"infeasible (ASF solve did not reach optimality -- these fixed variable values "
            f"likely cannot operate feasibly under this scenario): {result.message}"
        )

    values = {obj: float(result.optimal_objectives[obj]) for obj in objective_symbols}
    if any(v != v for v in values.values()):  # NaN != NaN
        return {obj: None for obj in objective_symbols}, "infeasible (ASF solve returned NaN objectives)"
    return values, "ok"
