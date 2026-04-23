"""Tools for constructing and solving scenario-based optimization problems."""

from typing import TYPE_CHECKING

from desdeo.problem.infix_parser import InfixExpressionParser
from desdeo.problem.schema import Constant, Problem, TensorConstant, TensorVariable, Variable

if TYPE_CHECKING:
    from desdeo.problem.scenario import ScenarioModel
    from desdeo.tools.generics import SolverResults

_parser = InfixExpressionParser()

# All operator names that must not be treated as variable/constant symbols,
# covering both infix keys and MathJSON values for every operator class.
_RESERVED: frozenset[str] = frozenset(
    set(InfixExpressionParser.UNARY_OPERATORS.keys())
    | set(InfixExpressionParser.UNARY_OPERATORS.values())
    | set(InfixExpressionParser.VARIADIC_OPERATORS.keys())
    | set(InfixExpressionParser.VARIADIC_OPERATORS.values())
    | set(InfixExpressionParser.BINARY_OPERATORS.values())
    | {"At", "Negate"}
)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _extract_symbols(expr: str) -> set[str]:
    """Return all variable/constant symbols referenced in a func string.

    Uses the infix parser to produce a MathJSON AST, then walks it to collect
    all string leaves that are not operator keywords.
    """
    parsed = _parser.parse(expr)
    symbols: set[str] = set()
    _walk_mathjson(parsed, symbols)
    return symbols


def _walk_mathjson(node, symbols: set[str]) -> None:
    """Recursively collect non-operator string leaves from a MathJSON node."""
    if isinstance(node, str):
        if node not in _RESERVED:
            symbols.add(node)
    elif isinstance(node, list):
        for child in node:
            _walk_mathjson(child, symbols)


def _rename_symbols(expr: str | list, symbol_map: dict[str, str]) -> list:
    """Rename symbols in a MathJSON expression (list) or infix string.

    Walks the MathJSON tree and substitutes every string leaf that is not a
    known operator keyword.  If ``expr`` is a plain infix string it is first
    parsed to MathJSON, then the renaming is applied.

    The returned value is always a MathJSON list, which Pydantic's
    ``parse_infix_to_func`` validator accepts directly without re-parsing.
    """
    if isinstance(expr, str):
        expr = _parser.parse(expr)
    return _rename_in_mathjson(expr, symbol_map)


def _rename_in_mathjson(node, symbol_map: dict[str, str]):
    """Recursively rename symbol strings in a MathJSON node."""
    if isinstance(node, str):
        return node if node in _RESERVED else symbol_map.get(node, node)
    if isinstance(node, list):
        return [_rename_in_mathjson(child, symbol_map) for child in node]
    return node  # int / float


def _build_parent_map(scenario_tree: dict[str, list[str]]) -> dict[str, str]:
    """Return a mapping from each node to its parent node."""
    parent: dict[str, str] = {}
    for node, children in scenario_tree.items():
        for child in children:
            parent[child] = node
    return parent


def _path_from_root(node: str, parent_map: dict[str, str]) -> list[str]:
    """Return the path [ROOT, ..., node] inclusive of both ends."""
    path: list[str] = []
    current: str | None = node
    while current is not None:
        path.append(current)
        current = parent_map.get(current)
    path.reverse()
    return path


def _new_variable_symbol(
    var_sym: str,
    leaf: str,
    anticipation_stop: dict[str, list[str]],
    parent_map: dict[str, str],
) -> str:
    """Return the combined-problem symbol for a variable in a given leaf scenario.

    Walks from ROOT toward the leaf.  The first (highest) ancestor where the
    variable appears in anticipation_stop determines sharing:

    - ROOT  -> all scenarios share one copy; original symbol is kept.
    - Other -> all leaves under that node share one copy; symbol gets that
               node name as suffix.
    - None  -> fully independent per leaf; symbol gets the leaf name as suffix.
    """
    for node in _path_from_root(leaf, parent_map):
        if var_sym in anticipation_stop.get(node, []):
            return var_sym if node == "ROOT" else f"{var_sym}_{node}"
    return f"{var_sym}_{leaf}"


def _build_variable_maps(
    scenario_model: "ScenarioModel",
    leaf_scenarios: list[str],
    parent_map: dict[str, str],
    scenario_problems: dict[str, Problem],
) -> tuple[dict[str, dict[str, str]], dict[str, Variable | TensorVariable]]:
    """Build per-leaf variable rename maps and the combined variable dict.

    Returns:
        var_maps: {leaf -> {original_sym -> new_sym}}
        combined_variables: {new_sym -> Variable | TensorVariable}
    """
    var_syms = {v.symbol for v in scenario_model.base_problem.variables}

    var_maps: dict[str, dict[str, str]] = {
        leaf: {
            sym: _new_variable_symbol(sym, leaf, scenario_model.anticipation_stop, parent_map)
            for sym in var_syms
        }
        for leaf in leaf_scenarios
    }

    combined_variables: dict[str, Variable | TensorVariable] = {}
    for leaf in leaf_scenarios:
        for var in scenario_problems[leaf].variables:
            new_sym = var_maps[leaf].get(var.symbol, var.symbol)
            if new_sym not in combined_variables:
                combined_variables[new_sym] = var.model_copy(
                    update={"symbol": new_sym, "name": f"{var.name} ({new_sym})"}
                )

    return var_maps, combined_variables


def _build_constant_maps(
    leaf_scenarios: list[str],
    scenario_problems: dict[str, Problem],
) -> tuple[dict[str, dict[str, str]], dict[str, Constant | TensorConstant]]:
    """Build per-leaf constant rename maps and the combined constant dict.

    Constants whose value is the same in every leaf keep their original symbol.
    Constants that differ across leaves are renamed to ``symbol_leaf``.

    Returns:
        const_maps: {leaf -> {original_sym -> new_sym}}
        combined_constants: {new_sym -> Constant | TensorConstant}
    """
    const_per_leaf: dict[str, dict[str, Constant | TensorConstant]] = {
        leaf: {c.symbol: c for c in (scenario_problems[leaf].constants or [])}
        for leaf in leaf_scenarios
    }
    all_const_syms: set[str] = {sym for lc in const_per_leaf.values() for sym in lc}

    const_maps: dict[str, dict[str, str]] = {leaf: {} for leaf in leaf_scenarios}
    combined_constants: dict[str, Constant | TensorConstant] = {}

    for sym in all_const_syms:
        values = {
            leaf: const_per_leaf[leaf][sym].value
            for leaf in leaf_scenarios
            if sym in const_per_leaf[leaf] and hasattr(const_per_leaf[leaf][sym], "value")
        }
        if len(set(values.values())) <= 1:
            for leaf in leaf_scenarios:
                const_maps[leaf][sym] = sym
            first = next(
                (const_per_leaf[leaf][sym] for leaf in leaf_scenarios if sym in const_per_leaf[leaf]),
                None,
            )
            if first is not None:
                combined_constants[sym] = first
        else:
            for leaf in leaf_scenarios:
                if sym in const_per_leaf[leaf]:
                    new_sym = f"{sym}_{leaf}"
                    const_maps[leaf][sym] = new_sym
                    combined_constants[new_sym] = const_per_leaf[leaf][sym].model_copy(
                        update={"symbol": new_sym}
                    )

    return const_maps, combined_constants


def _combine_elements(
    leaf_scenarios: list[str],
    scenario_problems: dict[str, Problem],
    var_maps: dict[str, dict[str, str]],
    const_maps: dict[str, dict[str, str]],
    get_list,
    make_update,
) -> list | None:
    """Build a combined list for one element type across all leaf scenarios.

    Elements whose renamed func string is identical across every leaf that
    carries them are kept as a single shared element (original symbol).
    All others get a per-leaf suffix ``symbol_leaf``.

    Args:
        leaf_scenarios: ordered list of leaf scenario names.
        scenario_problems: pre-computed {leaf -> Problem} mapping.
        var_maps: per-leaf variable rename maps {leaf -> {orig_sym -> new_sym}}.
        const_maps: per-leaf constant rename maps {leaf -> {orig_sym -> new_sym}}.
        get_list: callable(Problem) -> list | None of elements.
        make_update: callable(elem, new_sym, new_func) -> dict for model_copy.

    Returns:
        Combined list, or None if empty.
    """
    combined: list = []
    seen: set[str] = set()

    all_syms: set[str] = {
        elem.symbol
        for leaf in leaf_scenarios
        for elem in (get_list(scenario_problems[leaf]) or [])
    }

    for sym in all_syms:
        renamed: dict[str, str] = {}
        for leaf in leaf_scenarios:
            match = next(
                (e for e in (get_list(scenario_problems[leaf]) or []) if e.symbol == sym),
                None,
            )
            if match is None:
                continue
            symbol_map = {**var_maps[leaf], **const_maps[leaf]}
            renamed[leaf] = _rename_symbols(match.func, symbol_map)

        is_shared = (
            len({str(v) for v in renamed.values()}) == 1 and len(renamed) == len(leaf_scenarios)
        )

        if is_shared:
            new_sym = sym
            if new_sym not in seen:
                seen.add(new_sym)
                first_leaf = next(iter(renamed))
                elem = next(e for e in (get_list(scenario_problems[first_leaf]) or []) if e.symbol == sym)
                combined.append(elem.model_copy(update=make_update(elem, new_sym, renamed[first_leaf])))
        else:
            for leaf, new_func in renamed.items():
                new_sym = f"{sym}_{leaf}"
                if new_sym not in seen:
                    seen.add(new_sym)
                    elem = next(e for e in (get_list(scenario_problems[leaf]) or []) if e.symbol == sym)
                    combined.append(elem.model_copy(update=make_update(elem, new_sym, new_func)))

    return combined or None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_scenario_problem(scenario_model: "ScenarioModel", scenario_name: str) -> Problem:
    """Build a concrete Problem for a single named scenario.

    Applies the scenario's pool overrides and additions to the base problem
    and returns the resulting Problem instance ready to be passed to a solver.

    Args:
        scenario_model: the ScenarioModel containing the base problem and pools.
        scenario_name: the key identifying which scenario to construct.

    Returns:
        A Problem instance with the scenario's elements applied.

    Raises:
        ValueError: if scenario_name is not found in the model.
    """
    return scenario_model.get_scenario_problem(scenario_name)


def solve_scenario(
    scenario_model: "ScenarioModel",
    scenario_name: str,
    solver_callable,
    solver_options: dict | None = None,
) -> "SolverResults":
    """Solve a single scenario.

    Constructs the scenario problem and passes it to the provided solver.

    Args:
        scenario_model: the ScenarioModel containing the base problem and pools.
        scenario_name: the key identifying which scenario to solve.
        solver_callable: a callable that accepts a Problem (and optional options dict)
            and returns a SolverResults instance.
        solver_options: optional dict of keyword arguments forwarded to solver_callable.

    Returns:
        SolverResults from the solver.
    """
    problem = build_scenario_problem(scenario_model, scenario_name)
    options = solver_options or {}
    return solver_callable(problem, **options)


def solve_all_scenarios(
    scenario_model: "ScenarioModel",
    solver_callable,
    solver_options: dict | None = None,
) -> dict[str, "SolverResults"]:
    """Solve every leaf scenario in the model independently.

    Leaf scenarios are nodes in the scenario tree with no children.

    Args:
        scenario_model: the ScenarioModel to solve.
        solver_callable: a callable that accepts a Problem (and optional options dict)
            and returns a SolverResults instance.
        solver_options: optional dict of keyword arguments forwarded to solver_callable.

    Returns:
        A dict mapping each leaf scenario name to its SolverResults.
    """
    return {
        name: solve_scenario(scenario_model, name, solver_callable, solver_options)
        for name in scenario_model.leaf_scenarios
    }


def build_combined_scenario_problem(scenario_model: "ScenarioModel") -> Problem:
    """Build a single Problem that encodes all leaf scenarios simultaneously.

    Decision variables are duplicated once per leaf scenario unless a variable
    appears in anticipation_stop for an ancestor node, in which case all leaves
    under that node share one copy.  Every objective, constraint, extra function,
    and scalarization function is also duplicated per leaf, with all variable and
    scenario-specific constant references rewritten to their renamed counterparts.

    Elements whose renamed func string is identical across all leaves that carry
    them are kept as a single shared element (no per-leaf suffix).

    Uses the infix parser to extract symbol references from func strings, and
    word-boundary regex substitution to perform renaming.

    Args:
        scenario_model: the model to expand into a combined Problem.

    Returns:
        A single Problem suitable for passing directly to a solver.

    Raises:
        ValueError: if the model contains no leaf scenarios.
    """
    leaf_scenarios: list[str] = list(scenario_model.leaf_scenarios)

    if not leaf_scenarios:
        raise ValueError("ScenarioModel has no leaf scenarios to combine.")

    parent_map = _build_parent_map(scenario_model.scenario_tree)

    scenario_problems: dict[str, Problem] = {
        leaf: scenario_model.get_scenario_problem(leaf) for leaf in leaf_scenarios
    }

    var_maps, combined_variables = _build_variable_maps(
        scenario_model, leaf_scenarios, parent_map, scenario_problems
    )
    const_maps, combined_constants = _build_constant_maps(leaf_scenarios, scenario_problems)

    def _name_update(elem, new_sym, new_func):
        return {"symbol": new_sym, "name": f"{elem.name} ({new_sym})", "func": new_func}

    def _combine(get_list):
        return _combine_elements(leaf_scenarios, scenario_problems, var_maps, const_maps, get_list, _name_update)

    return Problem(
        name=f"{scenario_model.base_problem.name} (combined)",
        description=(
            f"Combined scenario problem from {len(leaf_scenarios)} leaf scenarios: "
            + ", ".join(leaf_scenarios)
        ),
        constants=list(combined_constants.values()) or None,
        variables=list(combined_variables.values()),
        objectives=_combine(lambda p: p.objectives),
        constraints=_combine(lambda p: p.constraints),
        extra_funcs=_combine(lambda p: p.extra_funcs),
        scalarization_funcs=_combine(lambda p: p.scalarization_funcs),
    )
