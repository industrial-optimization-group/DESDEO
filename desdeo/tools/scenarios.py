"""Tools for constructing and solving scenario-based optimization problems."""

from typing import TYPE_CHECKING, Any, NamedTuple

from desdeo.problem.infix_parser import InfixExpressionParser
from desdeo.problem.schema import (
    Constant,
    ExtraFunction,
    Objective,
    Problem,
    ScalarizationFunction,
    TensorConstant,
    TensorVariable,
    Variable,
)

if TYPE_CHECKING:
    from desdeo.problem.scenario import ScenarioModel
    from desdeo.tools.generics import SolverResults

_parser = InfixExpressionParser()


def find_base_elem(problem: "Problem", sym: str):
    """Return the first matching element from objectives, extra_funcs, scalarization_funcs, or constraints."""
    for elems in [problem.objectives, problem.extra_funcs, problem.scalarization_funcs, problem.constraints]:
        elem = next((e for e in (elems or []) if e.symbol == sym), None)
        if elem is not None:
            return elem
    return None


def _longest_common_name(names: "list[str]", fallback: str) -> str:
    """Return the longest common substring across all names, stripped of edge separators.

    Falls back to *fallback* when the list is empty or no non-empty common substring exists.
    """
    if not names:
        return fallback
    shortest = min(names, key=len)
    for length in range(len(shortest), 0, -1):
        for start in range(len(shortest) - length + 1):
            candidate = shortest[start : start + length]
            if all(candidate in name for name in names):
                stripped = candidate.strip("_- .")
                if stripped:
                    return stripped
    return fallback


def _pool_names_for(
    scenario_model: "ScenarioModel",
    found_type: str,
    sym: str,
    per_leaf: "dict[str, str]",
) -> "list[str]":
    """Collect distinct pool-element names for *sym* across the leaves in *per_leaf*."""
    pool: tuple = getattr(scenario_model, found_type, ())
    seen: set[int] = set()
    names: list[str] = []
    for leaf_name in per_leaf:
        scenario = scenario_model.scenarios.get(leaf_name)
        if scenario is None:
            continue
        elem_map: dict[str, int] = getattr(scenario, found_type, {})
        if sym in elem_map:
            idx = elem_map[sym]
            if idx not in seen and idx < len(pool):
                seen.add(idx)
                name = getattr(pool[idx], "name", None)
                if name:
                    names.append(name)
    return names


class _ElemResolution(NamedTuple):
    found_type: str
    per_leaf: "dict[str, str]"
    elem_list: list
    ref_elem: Any
    is_linear: bool
    is_convex: bool
    is_twice_diff: bool
    maximize: bool
    elem_name: str
    elem_desc: "str | None"


def resolve_elem(
    sym: str,
    symbol_maps: "dict[str, dict[str, dict[str, str]]]",
    combined: "Problem",
    scenario_model: "ScenarioModel",
) -> _ElemResolution:
    """Resolve per-symbol metadata needed by aggregation functions.

    Looks up the element type and per-leaf symbol map, retrieves the reference
    element from the combined problem for technical properties, and the original
    element from the base problem for name and description.

    Raises:
        ValueError: if sym is not found in symbol_maps.
    """
    found_type = None
    per_leaf = None
    for elem_type, smap in symbol_maps.items():
        if sym in smap:
            found_type = elem_type
            per_leaf = smap[sym]
            break
    if per_leaf is None:
        raise ValueError(f"Symbol '{sym}' not found in the combined problem.")

    elem_list = list(
        {
            "objectives": combined.objectives,
            "scalarization_funcs": combined.scalarization_funcs,
            "extra_funcs": combined.extra_funcs,
            "constraints": combined.constraints,
        }.get(found_type)
        or []
    )
    first_leaf_sym = per_leaf[next(iter(per_leaf))]
    ref_elem = next((e for e in elem_list if e.symbol == first_leaf_sym), None)

    base_elem = find_base_elem(scenario_model.base_problem, sym)
    return _ElemResolution(
        found_type=found_type,
        per_leaf=per_leaf,
        elem_list=elem_list,
        ref_elem=ref_elem,
        is_linear=getattr(ref_elem, "is_linear", False),
        is_convex=getattr(ref_elem, "is_convex", False),
        is_twice_diff=getattr(ref_elem, "is_twice_differentiable", False),
        maximize=getattr(ref_elem, "maximize", False),
        elem_name=base_elem.name
        if base_elem is not None
        else _longest_common_name(_pool_names_for(scenario_model, found_type, sym, per_leaf), sym),
        elem_desc=getattr(base_elem, "description", None) if base_elem is not None else None,
    )


def append_aggregated_elem(
    found_type: str,
    new_objectives: list,
    new_scal_funcs: list,
    new_extra_funcs: list,
    *,
    name: str,
    symbol: str,
    func: Any,
    description: "str | None" = None,
    maximize: bool = False,
    is_linear: bool = False,
    is_convex: bool = False,
    is_twice_differentiable: bool = False,
) -> None:
    """Append a new aggregated element to the appropriate list based on found_type.

    Appends an Objective if found_type is 'objectives', a ScalarizationFunction if
    'scalarization_funcs', and an ExtraFunction for everything else.
    ``description`` and ``maximize`` are only used for objectives.
    """
    if found_type == "objectives":
        new_objectives.append(
            Objective(
                name=name,
                description=description,
                symbol=symbol,
                func=func,
                maximize=maximize,
                is_linear=is_linear,
                is_convex=is_convex,
                is_twice_differentiable=is_twice_differentiable,
            )
        )
    elif found_type == "scalarization_funcs":
        new_scal_funcs.append(
            ScalarizationFunction(
                name=name,
                symbol=symbol,
                func=func,
                is_linear=is_linear,
                is_convex=is_convex,
                is_twice_differentiable=is_twice_differentiable,
            )
        )
    else:
        new_extra_funcs.append(
            ExtraFunction(
                name=name,
                symbol=symbol,
                func=func,
                is_linear=is_linear,
                is_convex=is_convex,
                is_twice_differentiable=is_twice_differentiable,
            )
        )


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
               node name as prefix.
    - None  -> fully independent per leaf; symbol gets the leaf name as prefix.
    """
    for node in _path_from_root(leaf, parent_map):
        if var_sym in anticipation_stop.get(node, []):
            return var_sym if node == "ROOT" else f"{node}_{var_sym}"
    return f"{leaf}_{var_sym}"


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
        leaf: {sym: _new_variable_symbol(sym, leaf, scenario_model.anticipation_stop, parent_map) for sym in var_syms}
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
        leaf: {c.symbol: c for c in (scenario_problems[leaf].constants or [])} for leaf in leaf_scenarios
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
                    new_sym = f"{leaf}_{sym}"
                    const_maps[leaf][sym] = new_sym
                    combined_constants[new_sym] = const_per_leaf[leaf][sym].model_copy(update={"symbol": new_sym})

    return const_maps, combined_constants


def _combine_elements(
    leaf_scenarios: list[str],
    scenario_problems: dict[str, Problem],
    var_maps: dict[str, dict[str, str]],
    const_maps: dict[str, dict[str, str]],
    get_list: callable,
    make_update: callable,
    extra_leaf_maps: "dict[str, dict[str, str]] | None" = None,
) -> tuple[list | None, dict[str, dict[str, str]]]:
    """Build a combined list for one element type across all leaf scenarios.

    Elements whose renamed func string is identical across every leaf that
    carries them are kept as a single shared element (original symbol).
    All others get a per-leaf prefix ``leaf_symbol``.

    Args:
        leaf_scenarios: ordered list of leaf scenario names.
        scenario_problems: pre-computed {leaf -> Problem} mapping.
        var_maps: per-leaf variable rename maps {leaf -> {orig_sym -> new_sym}}.
        const_maps: per-leaf constant rename maps {leaf -> {orig_sym -> new_sym}}.
        get_list: callable(Problem) -> list | None of elements.
        make_update: callable(elem, new_func, leaf) -> dict for model_copy.
            ``leaf`` is the scenario name for per-leaf elements, or ``None`` for shared ones.
            ``new_sym`` is derived inside as ``f"{leaf}_{elem.symbol}"`` or ``elem.symbol``.
        extra_leaf_maps: optional additional per-leaf rename maps merged into
            the leaf_map before renaming expressions.  Useful for passing
            objective-symbol renames (including ``_min`` versions) when
            processing scalarization functions and constraints.

    Returns:
        A tuple of (combined list or None, symbol map).  The symbol map has the
        original symbol as key and a {leaf -> new_symbol} dict as value.  Leaves
        that do not carry an element keep the original symbol as their value.
    """
    combined: list = []
    seen: set[str] = set()
    symbol_map: dict[str, dict[str, str]] = {}

    all_syms: set[str] = {elem.symbol for leaf in leaf_scenarios for elem in (get_list(scenario_problems[leaf]) or [])}

    for sym in all_syms:
        renamed: dict[str, str] = {}
        for leaf in leaf_scenarios:
            match = next(
                (e for e in (get_list(scenario_problems[leaf]) or []) if e.symbol == sym),
                None,
            )
            if match is None:
                continue
            leaf_map = {
                **var_maps[leaf],
                **const_maps[leaf],
                **(extra_leaf_maps[leaf] if extra_leaf_maps else {}),
            }
            renamed[leaf] = _rename_symbols(match.func, leaf_map)

        is_shared = len({str(v) for v in renamed.values()}) == 1 and len(renamed) == len(leaf_scenarios)

        if is_shared:
            first_leaf = next(iter(renamed))
            symbol_map[sym] = dict.fromkeys(leaf_scenarios, sym)
            entries = [(sym, first_leaf, renamed[first_leaf], None)]
        else:
            symbol_map[sym] = {leaf: f"{leaf}_{sym}" if leaf in renamed else sym for leaf in leaf_scenarios}
            entries = [(f"{leaf}_{sym}", leaf, new_func, leaf) for leaf, new_func in renamed.items()]

        for new_sym, src_leaf, new_func, name_leaf in entries:
            if new_sym not in seen:
                seen.add(new_sym)
                elem = next(e for e in (get_list(scenario_problems[src_leaf]) or []) if e.symbol == sym)
                combined.append(elem.model_copy(update=make_update(elem, new_func, name_leaf)))

    return combined or None, symbol_map


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
    solver_callable: callable,
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
    solver_callable: callable,
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


def build_combined_scenario_problem(
    scenario_model: "ScenarioModel",
) -> tuple[Problem, dict[str, dict[str, dict[str, str]]]]:
    """Build a single Problem that encodes all leaf scenarios simultaneously.

    Decision variables are duplicated once per leaf scenario unless a variable
    appears in anticipation_stop for an ancestor node, in which case all leaves
    under that node share one copy.  Every objective, constraint, extra function,
    and scalarization function is also duplicated per leaf, with all variable and
    scenario-specific constant references rewritten to their renamed counterparts.

    Elements whose renamed func string is identical across all leaves that carry
    them are kept as a single shared element (no per-leaf prefix).

    Args:
        scenario_model: the model to expand into a combined Problem.

    Returns:
        A tuple of:
        - A single Problem suitable for passing directly to a solver.
        - A symbol map ``{element_type: {original_symbol: {leaf: new_symbol}}}``.
            Element types are ``"variables"``, ``"constants"``, ``"objectives"``,
            ``"constraints"``, ``"extra_funcs"``, and ``"scalarization_funcs"``.
            Leaves that do not carry a given element retain the original symbol.

    Raises:
        ValueError: if the model contains no leaf scenarios.
    """
    leaf_scenarios: list[str] = list(scenario_model.leaf_scenarios)

    if not leaf_scenarios:
        raise ValueError("ScenarioModel has no leaf scenarios to combine.")

    parent_map = _build_parent_map(scenario_model.scenario_tree)

    scenario_problems: dict[str, Problem] = {leaf: scenario_model.get_scenario_problem(leaf) for leaf in leaf_scenarios}

    var_maps, combined_variables = _build_variable_maps(scenario_model, leaf_scenarios, parent_map, scenario_problems)
    const_maps, combined_constants = _build_constant_maps(leaf_scenarios, scenario_problems)

    def _name_update(elem, new_func, leaf):
        new_sym = elem.symbol if leaf is None else f"{leaf}_{elem.symbol}"
        update = {"symbol": new_sym, "func": new_func}
        if leaf is not None:
            update["name"] = f"{elem.name} ({leaf})"
        if isinstance(elem, Objective):
            update["ideal"] = None
            update["nadir"] = None
        return update

    def _combine(get_list, extra_maps=None):
        return _combine_elements(
            leaf_scenarios, scenario_problems, var_maps, const_maps, get_list, _name_update, extra_maps
        )

    objectives_list, objectives_map = _combine(lambda p: p.objectives)

    # Build per-leaf rename maps for objective symbols (and their _min versions).
    obj_extra_maps: dict[str, dict[str, str]] = {
        leaf: {
            name: new_sym
            for orig, per_leaf in objectives_map.items()
            for name, new_sym in (
                [(orig, per_leaf[leaf]), (f"{orig}_min", f"{per_leaf[leaf]}_min")] if per_leaf[leaf] != orig else []
            )
        }
        for leaf in leaf_scenarios
    }

    # Extra functions reference only variables/constants (and possibly objectives).
    extra_funcs_list, extra_funcs_map = _combine(lambda p: p.extra_funcs, obj_extra_maps)

    # Build per-leaf rename maps for extra function symbols.
    # Constraints and scalarization functions may reference extra functions by symbol.
    ef_extra_maps: dict[str, dict[str, str]] = {
        leaf: {orig: per_leaf[leaf] for orig, per_leaf in extra_funcs_map.items() if per_leaf[leaf] != orig}
        for leaf in leaf_scenarios
    }

    # Combined extra maps: objective + extra_func renames for constraints and scal funcs.
    combined_extra_maps: dict[str, dict[str, str]] = {
        leaf: {**obj_extra_maps[leaf], **ef_extra_maps[leaf]} for leaf in leaf_scenarios
    }

    constraints_list, constraints_map = _combine(lambda p: p.constraints, combined_extra_maps)
    scalarization_funcs_list, scalarization_funcs_map = _combine(lambda p: p.scalarization_funcs, combined_extra_maps)

    # Variable symbol map: original_sym -> {leaf -> new_sym}
    variables_map: dict[str, dict[str, str]] = {
        sym: {leaf: var_maps[leaf][sym] for leaf in leaf_scenarios}
        for sym in {v.symbol for v in scenario_model.base_problem.variables}
    }

    # Constant symbol map: original_sym -> {leaf -> new_sym}, defaulting to original
    all_const_syms: set[str] = {sym for lm in const_maps.values() for sym in lm}
    constants_map: dict[str, dict[str, str]] = {
        sym: {leaf: const_maps[leaf].get(sym, sym) for leaf in leaf_scenarios} for sym in all_const_syms
    }

    symbol_maps: dict[str, dict[str, dict[str, str]]] = {
        "variables": variables_map,
        "constants": constants_map,
        "objectives": objectives_map,
        "constraints": constraints_map,
        "extra_funcs": extra_funcs_map,
        "scalarization_funcs": scalarization_funcs_map,
    }

    problem = Problem(
        name=f"{scenario_model.base_problem.name} (combined)",
        description=(
            f"Combined scenario problem from {len(leaf_scenarios)} leaf scenarios: " + ", ".join(leaf_scenarios)
        ),
        constants=list(combined_constants.values()) or None,
        variables=list(combined_variables.values()),
        objectives=objectives_list,
        constraints=constraints_list,
        extra_funcs=extra_funcs_list,
        scalarization_funcs=scalarization_funcs_list,
    )

    return problem, symbol_maps


def build_scenario_symbol_maps(
    problem: "Problem",
    scenario_model: "ScenarioModel",
) -> "dict[str, dict[str, dict[str, str]]]":
    """Derive element symbol maps from an already-built combined scenario problem.

    A lightweight alternative to calling :func:`build_combined_scenario_problem`
    when the combined problem is already available.  Infers the per-leaf symbol
    for each base element by checking whether ``{leaf}_{orig}`` exists among the
    combined problem's element symbols.

    Covers ``objectives``, ``extra_funcs``, ``constraints``, and
    ``scalarization_funcs``; variables are excluded because their naming depends
    on ``anticipation_stop`` and cannot be inferred from symbol presence alone.

    Args:
        problem: the combined scenario problem (as returned by
            :func:`build_combined_scenario_problem` or after appending
            aggregation elements).
        scenario_model: the scenario model used to build ``problem``.

    Returns:
        Symbol maps dict with keys ``"objectives"``, ``"extra_funcs"``,
        ``"constraints"``, and ``"scalarization_funcs"``, compatible with
        the same-named keys from :func:`build_combined_scenario_problem`.
    """
    leaf_scenarios = list(scenario_model.leaf_scenarios)
    base = scenario_model.base_problem

    def _map(base_elems, combined_elems):
        combined_syms = {e.symbol for e in (combined_elems or [])}
        return {
            elem.symbol: {
                leaf: f"{leaf}_{elem.symbol}" if f"{leaf}_{elem.symbol}" in combined_syms else elem.symbol
                for leaf in leaf_scenarios
            }
            for elem in (base_elems or [])
        }

    return {
        "objectives": _map(base.objectives, problem.objectives),
        "extra_funcs": _map(base.extra_funcs, problem.extra_funcs),
        "constraints": _map(base.constraints, problem.constraints),
        "scalarization_funcs": _map(base.scalarization_funcs, problem.scalarization_funcs),
    }
