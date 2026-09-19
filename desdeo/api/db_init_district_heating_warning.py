"""Register the district heating problem with disruptions spread over January and advance warnings.

Adds a NEW problem next to the one `db_init_district_heating.py` registers; nothing existing is
modified or deleted. Its scenarios come from the decision maker's `dh_scenarios_warning.py`
(loaded from `DH_DATA_DIR`'s parent, like the other DM modules), whose start hours and warnings
come from the DM's `scenario_timeline.py`. The problem description is generated from those values
when this script runs, so it always states the timing that was actually registered.

Each scenario's information hour is stored in `JinaMultiScenarioMetaData.information_hours`.
JINA (interactive multi-scenario) turns it into non-anticipativity constraints: before that hour,
the scenario's hourly decisions must equal the baseline's. JINA (interactive two-stage robustness)
does not read it.

The compound-disruption stress test, the precomputed regret pool and the single-scenario candidate
pool are not attached: they were built for the original scenario timing.

Run from `desdeo/api` (so `sqlite:///./test.db` is the server's database), with `DH_DATA_DIR` set:
    python -m desdeo.api.db_init_district_heating_warning
"""
# ruff: noqa: T201

from pathlib import Path

from sqlmodel import Session, SQLModel, select

from desdeo.api.config import DistrictHeatingDataConfig
from desdeo.api.db import engine
from desdeo.api.db_init_district_heating import (
    DEFAULT_AF_ABSOLUTE_FLOORS,
    DEFAULT_DOMAIN_THRESHOLDS,
    OBJ_RELABEL,
    STRATEGIC_VAR_COMPONENTS,
    STRATEGIC_VAR_LABELS,
    STRATEGIC_VAR_UNITS,
    _assert_round_trip,
    _refresh_cell_ranges,
)
from desdeo.api.models import ProblemDB, User, UserRole
from desdeo.api.models.problem import JinaMultiScenarioMetaData, ProblemMetaDataDB
from desdeo.api.models.scenario import ScenarioModelDB
from desdeo.api.routers.district_heating_combined_data import invalidate_combined_context
from desdeo.api.routers.district_heating_robust_data import invalidate_context
from desdeo.api.routers.district_heating_system_data import DistrictHeatingDataError

PROBLEM_NAME = "District heating (multi-scenario, disruptions with advance warnings)"


def _check_database() -> None:
    """Refuse to write anywhere but the server's own SQLite file when running in debug mode."""
    if engine.url.get_backend_name() != "sqlite":
        return
    db_path = Path(engine.url.database).resolve()
    expected = (Path(__file__).resolve().parent / "test.db").resolve()
    if db_path != expected:
        msg = f"Database resolves to {db_path}, not the server's {expected}. Run this from desdeo/api."
        raise RuntimeError(msg)


def _describe_timeline(dh_scenarios_warning) -> str:
    """The problem description, built from the DM's current start hours and warnings."""

    def when(hour: int) -> str:
        return f"{hour // 24 + 1} Jan {hour % 24:02d}:00"

    parts = []
    for name, start in sorted(dh_scenarios_warning.EVENT_START.items(), key=lambda kv: kv[1]):
        label = name.removesuffix("_january").replace("_", " ")
        warning = dh_scenarios_warning.WARNING_HOURS.get(name, 0)
        notice = f"announced {warning} h ahead" if warning else "sudden"
        parts.append(f"{label} from {when(start)} ({notice})")
    return (
        "District heating capacity-expansion problem under 8 January scenarios: "
        + "; ".join(parts)
        + ". EB1/EB2 outages remove only the existing unit, so new capacity acts as a backup; heat not "
        "boosted to supply temperature counts as unmet demand. Until a disruption is known, the "
        "operation is the same as in the baseline (JINA interactive multi-scenario). Six strategic "
        "capacity variables are shared across all scenarios."
    )


def _build_problem_and_scenario_model():
    from desdeo.api.routers.district_heating_compound import _dm_dir, _load_dm_module

    dm_dir = _dm_dir()
    dh_problem_vectorized = _load_dm_module("dh_problem_vectorized", dm_dir)
    base_data1 = _load_dm_module("base_data1", dm_dir)
    config = _load_dm_module("config", dm_dir)
    dh_scenarios_warning = _load_dm_module("dh_scenarios_warning", dm_dir)

    historical_el_buy, historical_el_sell = base_data1.load_electricity_price_spike_csv(config.PRICE_SPIKE_CSV)
    historical_demand = base_data1.load_demand_spike_csv(config.DEMAND_SPIKE_CSV)

    raw_problem = dh_problem_vectorized.build_dh_problem()
    relabelled_objectives = [
        o.model_copy(update=OBJ_RELABEL[o.symbol]) if o.symbol in OBJ_RELABEL else o for o in raw_problem.objectives
    ]
    problem = raw_problem.model_copy(
        update={
            "name": PROBLEM_NAME,
            "description": _describe_timeline(dh_scenarios_warning),
            "objectives": relabelled_objectives,
        }
    )

    scenario_model, _scenarios, info_hours = dh_scenarios_warning.build_warning_scenario_model(
        historical_el_buy, historical_el_sell, historical_demand, base_problem=problem
    )
    return problem, scenario_model, info_hours, dh_scenarios_warning.BASELINE


def main() -> None:
    if not DistrictHeatingDataConfig.data_dir:
        raise DistrictHeatingDataError("DH_DATA_DIR is not set — required to build the district heating problem.")
    _check_database()

    SQLModel.metadata.create_all(engine)  # additive: creates only missing tables

    with Session(engine) as session:
        if session.exec(select(ProblemDB).where(ProblemDB.name == PROBLEM_NAME)).first() is not None:
            raise RuntimeError(f"A problem named {PROBLEM_NAME!r} already exists; nothing was added.")

        user = session.exec(select(User).where(User.role.in_([UserRole.analyst, UserRole.admin]))).first()
        if user is None:
            raise RuntimeError("No analyst/admin user found in the database to own the new problem.")

        print("Building the district heating problem + warning scenario model (this takes a moment)...")
        problem, scenario_model, info_hours, baseline = _build_problem_and_scenario_model()
        print(f"Baseline scenario: {baseline}")
        for name, hour in sorted(info_hours.items(), key=lambda kv: kv[1]):
            print(f"  {name:<24} known from hour {hour:>3} (Jan {hour // 24 + 1}, {hour % 24:02d}:00)")

        problem_db = ProblemDB.from_problem(problem, user)
        session.add(problem_db)
        session.commit()
        session.refresh(problem_db)
        print(f"Problem persisted (id={problem_db.id}).")

        sm_db = ScenarioModelDB.from_scenario_model(scenario_model, user=user, base_problem_id=problem_db.id)
        session.add(sm_db)
        session.commit()
        session.refresh(sm_db)
        print(f"ScenarioModelDB persisted (id={sm_db.id}, base_problem_id={problem_db.id}).")

        metadata_db = ProblemMetaDataDB(problem_id=problem_db.id, problem=problem_db)
        session.add(metadata_db)
        session.commit()
        session.refresh(metadata_db)

        jina_metadata = JinaMultiScenarioMetaData(
            metadata_id=metadata_db.id,
            default_domain_thresholds=DEFAULT_DOMAIN_THRESHOLDS,
            default_af_absolute_floors=DEFAULT_AF_ABSOLUTE_FLOORS,
            design_tolerance=1.0,
            emphasis_factor=3.0,
            baseline_scenario=baseline,
            compound_scenario_hook=None,
            compound_reference_hook=None,
            regret_pool_source=None,
            strategic_var_labels=STRATEGIC_VAR_LABELS,
            strategic_var_components=STRATEGIC_VAR_COMPONENTS,
            strategic_var_units=STRATEGIC_VAR_UNITS,
            information_hours=info_hours,
        )
        session.add(jina_metadata)
        session.commit()
        print("JinaMultiScenarioMetaData persisted.")

        problem_id = problem_db.id

        session.expire_all()
        reloaded_problem_db = session.get(ProblemDB, problem_id)
        reloaded_sm_db = session.get(ScenarioModelDB, sm_db.id)
        _assert_round_trip(problem, scenario_model, reloaded_problem_db, reloaded_sm_db)

        reloaded_meta = (reloaded_problem_db.problem_metadata.jina_multiscenario_metadata or [])[0]
        assert reloaded_meta.information_hours == info_hours, "information_hours mismatch after persisting"
        assert reloaded_meta.baseline_scenario == baseline, "baseline_scenario mismatch after persisting"
        print("Round-trip assertion passed: information hours and baseline persisted.")

    invalidate_context(problem_id)
    invalidate_combined_context(problem_id)

    _refresh_cell_ranges(problem_id)

    print(f"\nDone. Select problem_id={problem_id} ({PROBLEM_NAME!r}) in JINA (interactive multi-scenario).")


if __name__ == "__main__":
    main()
