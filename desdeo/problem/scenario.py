"""Scenario model for representing and constructing scenario-based optimization problems."""

import math
from functools import cached_property
from types import MappingProxyType
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from desdeo.problem import (
        Constant,
        Constraint,
        ExtraFunction,
        Objective,
        Problem,
        ScalarizationFunction,
        TensorConstant,
        TensorVariable,
        Variable,
    )


class Scenario(BaseModel):
    """References elements from the ScenarioModel pools that apply to a specific scenario.

    Each field maps a target symbol to a pool index.  The symbol identifies which element in
    the base problem to replace (for existing symbols) or the label of a new element to add
    (for symbols not present in the base problem).  The index is the position of the replacement
    or addition in the corresponding ScenarioModel pool list.

    Using an index rather than a symbol allows multiple pool entries to share the same symbol
    (e.g. the same constant at different values across scenarios) without ambiguity.
    """

    model_config = ConfigDict(frozen=True)

    constants: dict[str, int] = Field(
        default={},
        description="Maps target symbol to pool index for constants (scalar or tensor).",
    )
    variables: dict[str, int] = Field(
        default={},
        description="Maps target symbol to pool index for variables (scalar or tensor).",
    )
    objectives: dict[str, int] = Field(
        default={},
        description="Maps target symbol to pool index for objectives.",
    )
    constraints: dict[str, int] = Field(
        default={},
        description="Maps target symbol to pool index for constraints.",
    )
    extra_funcs: dict[str, int] = Field(
        default={},
        description="Maps target symbol to pool index for extra functions.",
    )
    scalarization_funcs: dict[str, int] = Field(
        default={},
        description="Maps target symbol to pool index for scalarization functions.",
    )


class ScenarioModel(BaseModel):
    """Base class for scenario models using Pydantic."""

    model_config = ConfigDict(frozen=True)

    scenario_tree: dict[str, list[str]] = Field(
        description="A dictionary describing the scenario structure for the problem. "
        "Keys are scenario names, values are lists of child scenario names. "
        "Must contain root of the tree with key 'ROOT' and value being a list of top-level scenario names. "
        "A plain list of scenario names is also accepted and is automatically converted to {'ROOT': [...]}.",
        default={"ROOT": ["scenario_0"]},
    )

    @field_validator("scenario_tree", mode="before")
    @classmethod
    def coerce_list_to_tree(cls, v):
        """Normalise the scenario tree input.

        - A flat list of names is converted to ``{'ROOT': [...], name: [], ...}``.
        - A dict may omit leaf nodes (nodes that appear as children but have no
          own entry).  Missing entries are auto-inserted with an empty child list.
        """
        if isinstance(v, list):
            return {"ROOT": v, **{name: [] for name in v}}
        if isinstance(v, dict):
            all_children = {child for children in v.values() for child in children}
            missing_leaves = all_children - set(v)
            if missing_leaves:
                return {**v, **{name: [] for name in missing_leaves}}
        return v

    @field_validator("scenario_tree", mode="after")
    @classmethod
    def validate_tree_structure(cls, v):
        """Verify that scenario_tree is a valid rooted tree with ROOT as the universal ancestor."""
        if "ROOT" not in v:
            raise ValueError("scenario_tree must contain a 'ROOT' key.")

        child_counts: dict[str, int] = {}
        for children in v.values():
            for child in children:
                child_counts[child] = child_counts.get(child, 0) + 1

        if "ROOT" in child_counts:
            raise ValueError("'ROOT' must not appear as a child of any node.")
        multi_parent = [n for n, c in child_counts.items() if c > 1]
        if multi_parent:
            raise ValueError(f"Nodes have more than one parent (not a tree): {sorted(multi_parent)}.")

        visited: set[str] = set()
        stack = ["ROOT"]
        while stack:
            node = stack.pop()
            visited.add(node)
            stack.extend(v.get(node, []))
        unreachable = set(v) - visited
        if unreachable:
            raise ValueError(f"Nodes not reachable from ROOT: {sorted(unreachable)}.")

        return v

    scenario_probabilities: dict[str, float] = Field(
        default={},
        description="Maps each scenario tree node to its probability. ROOT is always included with probability 1.0. "
        "For every node, the probabilities of its children must sum to the node's own probability.",
    )

    @field_validator("scenario_probabilities", mode="before")
    @classmethod
    def coerce_none_probabilities(cls, v):
        """Coerce None to an empty dict so probability validation can be skipped."""
        return v if v is not None else {}

    @field_validator("scenario_probabilities", mode="after")
    @classmethod
    def validate_scenario_probabilities(cls, v, info):
        """Auto-inject ROOT=1.0 and verify child probabilities sum to their parent's probability."""
        if not v:
            return v

        tree: dict[str, list[str]] = info.data.get("scenario_tree", {})

        v.setdefault("ROOT", 1.0)

        for key in v:
            if key not in tree:
                raise ValueError(f"scenario_probabilities key '{key}' not found in scenario_tree.")

        for parent, children in tree.items():
            if not children:
                continue
            if not any(c in v for c in children):
                continue
            parent_prob = v.get(parent)
            if parent_prob is None:
                raise ValueError(f"Probability for node '{parent}' is missing.")
            missing = [c for c in children if c not in v]
            if missing:
                raise ValueError(f"Probabilities missing for children of '{parent}': {missing}.")
            child_sum = sum(v[c] for c in children)
            if not math.isclose(child_sum, parent_prob, rel_tol=1e-9):
                raise ValueError(f"Probabilities of children of '{parent}' sum to {child_sum}, expected {parent_prob}.")
        return v

    base_problem: "Problem" = Field(description="The base Problem instance that is modified for different scenarios.")

    constants: tuple["Constant | TensorConstant", ...] = Field(
        default=(),
        description="Pool of Constant and TensorConstant replacements available to scenarios.",
    )
    variables: tuple["Variable | TensorVariable", ...] = Field(
        default=(),
        description="Pool of Variable and TensorVariable replacements available to scenarios.",
    )
    objectives: tuple["Objective", ...] = Field(
        default=(),
        description="Pool of Objective replacements available to scenarios.",
    )
    constraints: tuple["Constraint", ...] = Field(
        default=(),
        description="Pool of Constraint replacements available to scenarios.",
    )
    extra_funcs: tuple["ExtraFunction", ...] = Field(
        default=(),
        description="Pool of ExtraFunction replacements available to scenarios.",
    )
    scalarization_funcs: tuple["ScalarizationFunction", ...] = Field(
        default=(),
        description="Pool of ScalarizationFunction replacements available to scenarios.",
    )

    scenarios: dict[str, "Scenario"] = Field(
        default={},
        description="A dictionary mapping scenario names to Scenario instances, "
        "which define which elements from the pools apply to each scenario.",
    )

    anticipation_stop: dict[str, list[str]] = Field(
        default={},
        description="Maps a scenario tree node name to a list of variable symbols that enforce "
        "non-anticipativity at that node: the listed variables must take the same value across "
        "all descendant scenarios of that node.",
    )

    @field_validator("anticipation_stop", mode="after")
    @classmethod
    def validate_anticipation_stop(cls, v, info):
        """Validate that anticipation_stop keys exist in scenario_tree and values are valid variable symbols."""
        data = info.data
        valid_nodes = set(data.get("scenario_tree", {}).keys())
        base_problem = data.get("base_problem")
        valid_variables = (
            {var.symbol for var in base_problem.variables} if base_problem and base_problem.variables else set()
        )
        # Pool variables (added to scenarios) are also valid anticipation targets.
        valid_variables |= {var.symbol for var in data.get("variables", ())}

        for node, symbols in v.items():
            if node not in valid_nodes:
                raise ValueError(f"anticipation_stop key '{node}' not found in scenario_tree.")
            for symbol in symbols:
                if symbol not in valid_variables:
                    raise ValueError(
                        f"Variable symbol '{symbol}' in anticipation_stop['{node}'] "
                        "not found in base_problem variables or the variable pool."
                    )
        return v

    def with_base_problem(self, problem: "Problem | None" = None, validate: bool = False, **updates) -> "ScenarioModel":
        """Return a new ScenarioModel with the base_problem updated.

        By default uses model_copy, so validators are NOT re-run. Pass
        ``validate=True`` to reconstruct via model_validate, which re-runs all
        field validators (including anticipation_stop checks). Only safe when the
        update cannot remove variables or scenario-tree nodes that validators
        reference.

        Args:
            problem: if provided, replaces the base_problem entirely.
            validate: if True, reconstruct with model_validate so all validators
                run, which is somewhat slower. Defaults to False.
            **updates: keyword arguments forwarded to Problem.model_copy(update=...)
                to partially update the existing base_problem. Ignored when
                ``problem`` is given.

        Returns:
            A new ScenarioModel with the modified base_problem.
        """
        new_base = problem if problem is not None else self.base_problem.model_copy(update=updates)
        if validate:
            return type(self).model_validate(self.model_dump() | {"base_problem": new_base})
        return self.model_copy(update={"base_problem": new_base})

    @cached_property
    def leaf_scenarios(self) -> MappingProxyType[str, float]:
        """Return a read-only mapping from each leaf scenario name to its probability.

        Leaf scenarios are nodes in the scenario tree with no children that also
        appear in the scenarios dict.  If scenario_probabilities is empty, equal
        weights (1/n) are assigned to each leaf.
        """
        leaves = [
            n for n, children in self.scenario_tree.items() if n != "ROOT" and not children and n in self.scenarios
        ]
        if self.scenario_probabilities:
            return MappingProxyType({leaf: self.scenario_probabilities[leaf] for leaf in leaves})
        equal = 1.0 / len(leaves) if leaves else 0.0
        return MappingProxyType(dict.fromkeys(leaves, equal))

    def get_scenario_problem(self, scenario_name: str) -> "Problem":
        """Return a modified copy of base_problem with the elements defined in the named scenario applied."""
        if scenario_name not in self.scenarios:
            raise ValueError(f"Scenario '{scenario_name}' not found.")

        scenario = self.scenarios[scenario_name]

        def apply(base_list, pool_list, symbol_to_idx):
            if not symbol_to_idx:
                return base_list
            base_list = base_list or []
            base_symbols = {e.symbol for e in base_list}
            result = [pool_list[symbol_to_idx[e.symbol]] if e.symbol in symbol_to_idx else e for e in base_list]
            result += [pool_list[idx] for sym, idx in symbol_to_idx.items() if sym not in base_symbols]
            return result

        updates = {}
        if scenario.constants:
            updates["constants"] = apply(self.base_problem.constants, self.constants, scenario.constants)
        if scenario.variables:
            updates["variables"] = apply(self.base_problem.variables, self.variables, scenario.variables)
        if scenario.objectives:
            updates["objectives"] = apply(self.base_problem.objectives, self.objectives, scenario.objectives)
        if scenario.constraints:
            updates["constraints"] = apply(self.base_problem.constraints, self.constraints, scenario.constraints)
        if scenario.extra_funcs:
            updates["extra_funcs"] = apply(self.base_problem.extra_funcs, self.extra_funcs, scenario.extra_funcs)
        if scenario.scalarization_funcs:
            updates["scalarization_funcs"] = apply(
                self.base_problem.scalarization_funcs, self.scalarization_funcs, scenario.scalarization_funcs
            )

        return self.base_problem.model_copy(update=updates)

    @field_validator("scenarios", mode="after")
    @classmethod
    def validate_scenarios(cls, v, info):
        """Validate that scenario names exist in scenario_tree and that all indices are in bounds."""
        data = info.data
        valid_scenarios = set(data.get("scenario_tree", {}).keys())

        pool_lengths = {
            "constants": len(data.get("constants", [])),
            "variables": len(data.get("variables", [])),
            "objectives": len(data.get("objectives", [])),
            "constraints": len(data.get("constraints", [])),
            "extra_funcs": len(data.get("extra_funcs", [])),
            "scalarization_funcs": len(data.get("scalarization_funcs", [])),
        }

        for scenario_name, scenario in v.items():
            if scenario_name not in valid_scenarios:
                raise ValueError(f"Scenario '{scenario_name}' not found in scenario_tree.")
            for field, length in pool_lengths.items():
                for symbol, idx in getattr(scenario, field).items():
                    if idx < 0 or idx >= length:
                        raise ValueError(
                            f"Index {idx} for symbol '{symbol}' in scenario '{scenario_name}.{field}' "
                            f"is out of bounds (pool length {length})."
                        )
        return v
