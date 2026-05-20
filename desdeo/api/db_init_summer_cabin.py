"""Initialize the database with the summer cabin EV problem and its solution description metadata.

Includes everything from db_init.py and adds:
- summer_cabin_battery_robust_ev_problem with stripped objectives
  (only E_f_1, f_2, E_f_3 kept as objectives; all others demoted to extra functions)
- SolutionDescriptionMetaData for that problem

Run from desdeo/api/:
    python db_init_summer_cabin.py
"""
# ruff: noqa: T201

import warnings

from sqlalchemy_utils import database_exists
from sqlmodel import Session, SQLModel

from desdeo.api.config import ServerConfig, SettingsConfig
from desdeo.api.db import engine
from desdeo.api.models import ProblemDB, User, UserRole
from desdeo.api.models.problem import DescriptionPart, ProblemMetaDataDB, SolutionDescriptionMetaData
from desdeo.api.models.scenario import ScenarioModelDB
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.schema import ExtraFunction, Objective
from desdeo.problem.testproblems import dtlz2, river_pollution_problem, simple_knapsack
from desdeo.problem.testproblems.summer_cabin_electricity import (
    summer_cabin_battery_problem_split_scenario,
    summer_cabin_battery_robust_ev_problem,
)


def objective_to_extra_function(obj: Objective) -> ExtraFunction:
    """Convert an Objective to an ExtraFunction, keeping the same symbol."""
    return ExtraFunction(
        name=obj.name,
        symbol=obj.symbol,
        func=obj.func,
        is_linear=obj.is_linear,
        is_convex=obj.is_convex,
        is_twice_differentiable=obj.is_twice_differentiable,
    )


def build_summer_cabin_problem_full():
    """Build the summer cabin problem with all objectives kept intact."""
    print("Building summer_cabin_battery_robust_ev_problem full (this may take a moment)...")
    problem = summer_cabin_battery_robust_ev_problem()
    return problem.model_copy(
        update={
            "name": "Summer cabin energy management full",
            "description": (
                "Robust multi-objective energy management for a summer cabin with battery storage, "
                "solar panels, and an optional EV charger. "
                "All original objectives are retained. "
                "Scenario tree: 4 leaves covering grid outages in segments 2 and/or 3."
            ),
        }
    )


def build_summer_cabin_problem():
    """Build the summer cabin problem with demoted objectives."""
    print("Building summer_cabin_battery_robust_ev_problem (this may take a moment)...")
    problem = summer_cabin_battery_robust_ev_problem()

    keep = {"E_f_1", "f_2", "E_f_3"}
    rename = {
        "E_f_1": "Expected electricity cost /€",
        "f_2": "Investment cost /€",
        "E_f_3": "Expected outage duration /h",
    }
    new_objectives = [
        o.model_copy(update={"name": rename[o.symbol]}) if o.symbol in rename else o
        for o in problem.objectives
        if o.symbol in keep
    ]
    demoted = [objective_to_extra_function(o) for o in problem.objectives if o.symbol not in keep]
    existing_extra = list(problem.extra_funcs or [])

    return problem.model_copy(
        update={
            "name": "Summer cabin energy management (robust EV)",
            "description": (
                "Robust multi-objective energy management for a summer cabin with battery storage, "
                "solar panels, and an optional EV charger. "
                "Objectives: expected electricity cost (E_f_1), investment cost (f_2), "
                "expected unserved hours (E_f_3). "
                "Scenario tree: 4 leaves covering grid outages in segments 2 and/or 3."
            ),
            "objectives": new_objectives,
            "extra_funcs": existing_extra + demoted,
        }
    )


DESCRIPTION_PARTS = [
    DescriptionPart(text="Investment decisions:"),
    DescriptionPart(label="  Battery installed", symbol="y", format_spec=".0f"),
    DescriptionPart(label="  Battery capacity", symbol="E", format_spec=".1f", suffix=" kWh"),
    DescriptionPart(label="  Solar panels", symbol="n", format_spec=".0f"),
    DescriptionPart(text="Investment cost breakdown:"),
    DescriptionPart(
        label="  Battery fixed cost",
        expression=["Multiply", 2000, "y"],
        format_spec=".0f",
        suffix=" €",
    ),
    DescriptionPart(
        label="  Battery capacity cost",
        expression=["Multiply", 310, "E"],
        format_spec=".0f",
        suffix=" €",
    ),
    DescriptionPart(
        label="  Solar panel cost",
        expression=["Multiply", 200, "n"],
        format_spec=".0f",
        suffix=" €",
    ),
    DescriptionPart(label="  Total investment cost", symbol="E_f_2", format_spec=".0f", suffix=" €"),
    DescriptionPart(text="Expected performance:"),
    DescriptionPart(label="  Expected electricity cost", symbol="E_f_1", format_spec=".2f", suffix=" €"),
    DescriptionPart(label="  Expected unserved hours", symbol="E_f_3", format_spec=".2f", suffix=" h"),
    DescriptionPart(text="Worst-case performance:"),
    DescriptionPart(label="  Worst-case electricity cost", symbol="robust_f_1", format_spec=".2f", suffix=" €"),
    DescriptionPart(label="  Worst-case investment cost", symbol="robust_f_2", format_spec=".0f", suffix=" €"),
    DescriptionPart(label="  Worst-case unserved hours", symbol="robust_f_3", format_spec=".1f", suffix=" h"),
]


if __name__ == "__main__":
    if SettingsConfig.debug:
        print("Creating database tables.")
        if not database_exists(engine.url):
            SQLModel.metadata.create_all(engine)
        else:
            warnings.warn("Database already exists. Clearing it.", stacklevel=1)
            SQLModel.metadata.reflect(bind=engine)
            SQLModel.metadata.drop_all(bind=engine)
            SQLModel.metadata.create_all(engine)
        print("Database tables created.")

        with Session(engine) as session:
            user_analyst = User(
                username=ServerConfig.test_user_analyst_name,
                password_hash=get_password_hash(ServerConfig.test_user_analyst_password),
                role=UserRole.analyst,
                group="test",
            )
            session.add(user_analyst)
            session.commit()
            session.refresh(user_analyst)

            # Standard test problems from db_init.py
            for problem in [dtlz2(10, 3), simple_knapsack(), river_pollution_problem()]:
                session.add(ProblemDB.from_problem(problem, user_analyst))
            session.commit()
            print("Standard test problems added.")

            # Summer cabin problem with all objectives (unstripped)
            cabin_full_problem = build_summer_cabin_problem_full()
            cabin_full_db = ProblemDB.from_problem(cabin_full_problem, user_analyst)
            session.add(cabin_full_db)
            session.commit()
            session.refresh(cabin_full_db)
            print(f"Summer cabin full problem added (id={cabin_full_db.id}).")

            # Summer cabin problem with stripped objectives
            cabin_problem = build_summer_cabin_problem()
            cabin_db = ProblemDB.from_problem(cabin_problem, user_analyst)
            session.add(cabin_db)
            session.commit()
            session.refresh(cabin_db)
            print(f"Summer cabin problem added (id={cabin_db.id}).")

            # Solution description metadata for full problem
            metadata_full_db = ProblemMetaDataDB(problem_id=cabin_full_db.id, problem=cabin_full_db)
            session.add(metadata_full_db)
            session.commit()
            session.refresh(metadata_full_db)

            desc_metadata_full = SolutionDescriptionMetaData(
                metadata_id=metadata_full_db.id,
                parts=[p.model_dump() for p in DESCRIPTION_PARTS],
                separator="\n",
            )
            session.add(desc_metadata_full)
            session.commit()
            print("Solution description metadata added for full problem.")

            # Solution description metadata for stripped problem
            metadata_db = ProblemMetaDataDB(problem_id=cabin_db.id, problem=cabin_db)
            session.add(metadata_db)
            session.commit()
            session.refresh(metadata_db)

            desc_metadata = SolutionDescriptionMetaData(
                metadata_id=metadata_db.id,
                parts=[p.model_dump() for p in DESCRIPTION_PARTS],
                separator="\n",
            )
            session.add(desc_metadata)
            session.commit()
            print("Solution description metadata added for stripped problem.")

            # Base summer cabin problem with its scenario model (for testing scenario detection in CUMULUS)
            print("Building summer_cabin_battery_problem_split_scenario (this may take a moment)...")
            scenario_model = summer_cabin_battery_problem_split_scenario()
            base_problem = scenario_model.base_problem.model_copy(
                update={
                    "name": "Summer cabin energy management (with scenarios)",
                    "description": (
                        "Base summer cabin battery problem with an associated 4-leaf scenario model "
                        "covering grid outages in segments 2 and/or 3. "
                        "Use CUMULUS to optionally build a combined scenario problem with uncertainty measures."
                    ),
                }
            )
            cabin_scenario_base_db = ProblemDB.from_problem(base_problem, user_analyst)
            session.add(cabin_scenario_base_db)
            session.commit()
            session.refresh(cabin_scenario_base_db)
            print(f"Summer cabin base problem added (id={cabin_scenario_base_db.id}).")

            scenario_model_db = ScenarioModelDB.from_scenario_model(
                scenario_model, user=user_analyst, base_problem_id=cabin_scenario_base_db.id
            )
            session.add(scenario_model_db)
            session.commit()
            session.refresh(scenario_model_db)
            print(
                f"ScenarioModelDB added (id={scenario_model_db.id}) linked to problem id={cabin_scenario_base_db.id}."
            )

            metadata_scenario_db = ProblemMetaDataDB(
                problem_id=cabin_scenario_base_db.id, problem=cabin_scenario_base_db
            )
            session.add(metadata_scenario_db)
            session.commit()
            session.refresh(metadata_scenario_db)

            desc_metadata_scenario = SolutionDescriptionMetaData(
                metadata_id=metadata_scenario_db.id,
                parts=[p.model_dump() for p in DESCRIPTION_PARTS],
                separator="\n",
            )
            session.add(desc_metadata_scenario)
            session.commit()

        print("Done.")

    else:
        pass
