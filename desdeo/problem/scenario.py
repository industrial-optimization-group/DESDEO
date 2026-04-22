from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from desdeo.problem import Constant, Constraint, ExtraFunction, Objective, Problem, ScalarizationFunction, Variable


class Scenario(BaseModel):
    """References elements from the ScenarioModel pools that apply to a specific scenario."""

    constants: list[str] = Field(default=[], description="Symbols of constants from the pool to apply.")
    variables: list[str] = Field(default=[], description="Symbols of variables from the pool to apply.")
    objectives: list[str] = Field(default=[], description="Symbols of objectives from the pool to apply.")
    constraints: list[str] = Field(
        default=[],
        description="Symbols of constraints from the pool to apply.",
    )
    extra_funcs: list[str] = Field(
        default=[],
        description="Symbols of extra functions from the pool to apply.",
    )
    scalarization_funcs: list[str] = Field(
        default=[],
        description="Symbols of scalarization functions from the pool to apply.",
    )


class ScenarioModel(BaseModel):
    """Base class for scenario models using Pydantic."""

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
        """Convert a flat list of scenario names to {'ROOT': [...]}."""
        if isinstance(v, list):
            return {"ROOT": v, **{name: [] for name in v}}
        return v

    base_problem: "Problem" = Field(description="The base Problem instance that is modified for different scenarios.")

    constants: list["Constant"] = Field(
        default=[],
        description="Pool of Constant replacements available to scenarios.",
    )
    variables: list["Variable"] = Field(
        default=[],
        description="Pool of Variable replacements available to scenarios.",
    )
    objectives: list["Objective"] = Field(
        default=[],
        description="Pool of Objective replacements available to scenarios.",
    )
    constraints: list["Constraint"] = Field(
        default=[],
        description="Pool of Constraint replacements available to scenarios.",
    )
    extra_funcs: list["ExtraFunction"] = Field(
        default=[],
        description="Pool of ExtraFunction replacements available to scenarios.",
    )
    scalarization_funcs: list["ScalarizationFunction"] = Field(
        default=[],
        description="Pool of ScalarizationFunction replacements available to scenarios.",
    )

    scenarios: dict[str, "Scenario"] = Field(
        default={},
        description="A dictionary mapping scenario names to ScenarioDelta instances, "
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

        for node, symbols in v.items():
            if node not in valid_nodes:
                raise ValueError(f"anticipation_stop key '{node}' not found in scenario_tree.")
            for symbol in symbols:
                if symbol not in valid_variables:
                    raise ValueError(
                        f"Variable symbol '{symbol}' in anticipation_stop['{node}'] "
                        "not found in base_problem variables."
                    )
        return v

    def get_scenario_problem(self, scenario_name: str) -> "Problem":
        """Return a modified copy of base_problem with the elements defined in the named scenario applied."""
        if scenario_name not in self.scenarios:
            raise ValueError(f"Scenario '{scenario_name}' not found.")

        scenario = self.scenarios[scenario_name]

        def apply(base_list, pool, updated_symbols):
            if not updated_symbols:
                return base_list
            replacements = {s: pool[s] for s in updated_symbols}
            if base_list is None:
                return list(replacements.values())
            result = [replacements.get(e.symbol, e) for e in base_list]
            existing = {e.symbol for e in base_list}
            result += [replacements[s] for s in updated_symbols if s not in existing]
            return result

        constant_pool = {c.symbol: c for c in self.constants}
        variable_pool = {v.symbol: v for v in self.variables}
        objective_pool = {o.symbol: o for o in self.objectives}
        constraint_pool = {c.symbol: c for c in self.constraints}
        extra_func_pool = {e.symbol: e for e in self.extra_funcs}
        scalarization_pool = {s.symbol: s for s in self.scalarization_funcs}

        updates = {}
        if scenario.constants:
            updates["constants"] = apply(self.base_problem.constants, constant_pool, scenario.constants)
        if scenario.variables:
            updates["variables"] = apply(self.base_problem.variables, variable_pool, scenario.variables)
        if scenario.objectives:
            updates["objectives"] = apply(self.base_problem.objectives, objective_pool, scenario.objectives)
        if scenario.constraints:
            updates["constraints"] = apply(self.base_problem.constraints, constraint_pool, scenario.constraints)
        if scenario.extra_funcs:
            updates["extra_funcs"] = apply(self.base_problem.extra_funcs, extra_func_pool, scenario.extra_funcs)
        if scenario.scalarization_funcs:
            updates["scalarization_funcs"] = apply(
                self.base_problem.scalarization_funcs, scalarization_pool, scenario.scalarization_funcs
            )

        return self.base_problem.model_copy(update=updates)

    @field_validator("scenarios", mode="after")
    @classmethod
    def validate_scenarios(cls, v, info):
        """Validate that scenario names exist in scenario_tree and that all referenced symbols exist in the pools."""
        data = info.data
        valid_scenarios = set(data.get("scenario_tree", {}).keys())

        pool_symbols = {
            "constants": {c.symbol for c in data.get("constants", [])},
            "constraints": {c.symbol for c in data.get("constraints", [])},
            "variables": {var.symbol for var in data.get("variables", [])},
            "objectives": {o.symbol for o in data.get("objectives", [])},
            "extra_funcs": {e.symbol for e in data.get("extra_funcs", [])},
            "scalarization_funcs": {s.symbol for s in data.get("scalarization_funcs", [])},
        }

        for scenario_name, delta in v.items():
            if scenario_name not in valid_scenarios:
                raise ValueError(f"Scenario '{scenario_name}' not found in scenario_tree.")
            for field, symbols in pool_symbols.items():
                for symbol in getattr(delta, field):
                    if symbol not in symbols:
                        raise ValueError(
                            f"Symbol '{symbol}' in scenario '{scenario_name}.{field}' not found in {field} pool."
                        )
        return v
