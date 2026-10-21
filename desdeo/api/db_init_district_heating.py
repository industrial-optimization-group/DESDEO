"""Migrate the district heating problem into the standard ProblemDB/ScenarioModelDB registry.

Until now, JINA multi-scenario built its Problem by dynamically importing the decision maker's
own `dh_problem_vectorized.py` at *request* time, bypassing DESDEO's normal problem registry
entirely (`problem_id` was always `None`). This script builds it *once* the same way (still using
the DM's own code — someone's Python has to build any problem, this one included) and persists it
as a normal `ProblemDB` + `ScenarioModelDB`, so it's selectable from the "Optimization Problems"
list and goes through the exact same generic code path
(`desdeo.api.routers.district_heating_robust_data.get_context`) as any other problem from now on.

Purely ADDITIVE — never drops or clears the database. Safe to run against an existing test.db
with real session data in it. Backfills existing JINA multi-scenario sessions' `StateDB.problem_id`
so their history doesn't go blank once lookups start filtering by problem_id.

Run from the repo root:
    .venv/Scripts/python.exe -m desdeo.api.db_init_district_heating
"""
# ruff: noqa: T201

from sqlmodel import Session, SQLModel, select

from desdeo.api.config import DistrictHeatingDataConfig
from desdeo.api.db import engine
from desdeo.api.models import ProblemDB, User, UserRole
from desdeo.api.models.generic_states import StateDB, StateKind
from desdeo.api.models.problem import JinaMultiScenarioMetaData, JinaPoolMetaData, ProblemMetaDataDB
from desdeo.api.models.problem import JinaMultiScenarioMetaData as _Meta
from desdeo.api.models.scenario import ScenarioModelDB
from desdeo.api.routers.district_heating_combined_data import store_cell_ranges
from desdeo.api.routers.district_heating_compound import _dm_dir, _load_dm_module
from desdeo.api.routers.district_heating_robust_data import invalidate_context
from desdeo.api.routers.district_heating_system_data import DistrictHeatingDataError, invalidate_pool_context
from desdeo.problem.schema import Problem

OBJ_RELABEL = {
    "obj1": {"name": "Operational Cost", "unit": "EUR"},
    "obj2": {"name": "Investment Cost", "unit": "EUR"},
    "obj3": {"name": "CO2 Emissions", "unit": "t"},
    "obj4": {"name": "Unmet Heat", "unit": "MWh"},
}

STRATEGIC_VAR_LABELS = {
    "S_new_TES": "New TES",
    "Q_new_EB1": "New EB1",
    "Q_new_BB": "New BB",
    "Q_new_CHP": "New CHP",
    "Q_new_EB2": "New EB2",
    "Q_new_HP": "New HP",
}
STRATEGIC_VAR_COMPONENTS = {
    "S_new_TES": "TES",
    "Q_new_EB1": "EB1",
    "Q_new_BB": "BB",
    "Q_new_CHP": "CHP",
    "Q_new_EB2": "EB2",
    "Q_new_HP": "HP",
}
STRATEGIC_VAR_UNITS = {
    "S_new_TES": "MWh",
    "Q_new_EB1": "MW",
    "Q_new_BB": "MW",
    "Q_new_CHP": "MW",
    "Q_new_EB2": "MW",
    "Q_new_HP": "MW",
}

DEFAULT_DOMAIN_THRESHOLDS = {"obj1": -35_000_000, "obj2": 200_000_000, "obj3": 200, "obj4": 500}
DEFAULT_AF_ABSOLUTE_FLOORS = {"obj1": -30_000_000, "obj2": 2_500_000, "obj3": 640.0, "obj4": 100.0}

# The_DM_session.ipynb's own 6 scalarizers only ever emphasized 3 of the 4 objectives (never
# obj2/Investment Cost) — explicit here so the generic "one emphasis variant per objective"
# default (which a new problem gets) doesn't silently grow district heating's scalarizer count.
POOL_OBJ_EMPHASIS_SYMBOLS = ["obj1", "obj3", "obj4"]
POOL_LAMBDA_OBJECTIVE = "obj1"  # matches the notebook's "AF_λ = U - λ·D on Operational Cost" copy


def _build_problem_and_scenario_model():
    """Build the district heating Problem and its ScenarioModel from the DM's own modules.

    Objectives are relabelled with real names and units. This is the same code the request-time path used to run on
    every first request, now run once here instead.
    """
    dm_dir = _dm_dir()
    dh_problem_vectorized = _load_dm_module("dh_problem_vectorized", dm_dir)
    base_data1 = _load_dm_module("base_data1", dm_dir)
    config = _load_dm_module("config", dm_dir)

    historical_el_buy, historical_el_sell = base_data1.load_electricity_price_spike_csv(config.PRICE_SPIKE_CSV)
    historical_demand = base_data1.load_demand_spike_csv(config.DEMAND_SPIKE_CSV)

    raw_problem = dh_problem_vectorized.build_dh_problem()

    relabelled_objectives = [
        o.model_copy(update=OBJ_RELABEL[o.symbol]) if o.symbol in OBJ_RELABEL else o for o in raw_problem.objectives
    ]
    problem = raw_problem.model_copy(
        update={
            "name": "District heating (multi-scenario, 8 January disruptions)",
            "description": (
                "District heating capacity-expansion problem under 8 January disruption "
                "scenarios (baseline, price spike, demand spike, DC/biomass/EB1/EB2 loss, grid "
                "outage). Six strategic (first-stage) capacity variables are shared across all "
                "scenarios; the rest is scenario-specific operational dispatch. Ported from the "
                "decision maker's own dh_problem_vectorized.py."
            ),
            "objectives": relabelled_objectives,
        }
    )

    scenario_model, _scenarios = dh_problem_vectorized.build_default_scenario_model(
        historical_el_buy=historical_el_buy,
        historical_el_sell=historical_el_sell,
        historical_demand=historical_demand,
        base_problem=problem,
    )
    return problem, scenario_model


def _assert_round_trip(problem: Problem, scenario_model, problem_db: ProblemDB, sm_db: ScenarioModelDB) -> None:
    """Re-read what was just persisted and check it matches the in-memory originals.

    Aborts loudly on mismatch — this is the regression gate for the persistence layer, not just a nice-to-have.
    """
    reloaded_problem = Problem.from_problemdb(problem_db)
    reloaded_sm = sm_db.to_scenario_model(reloaded_problem)

    orig_obj_symbols = [o.symbol for o in problem.objectives]
    reloaded_obj_symbols = [o.symbol for o in reloaded_problem.objectives]
    if not (orig_obj_symbols == reloaded_obj_symbols):
        raise RuntimeError(f"Objective symbol order mismatch: {orig_obj_symbols} != {reloaded_obj_symbols}")

    if not (reloaded_sm.anticipation_stop == scenario_model.anticipation_stop):
        raise RuntimeError(
            f"anticipation_stop mismatch: {scenario_model.anticipation_stop} != {reloaded_sm.anticipation_stop}"
        )

    orig_leaves = sorted(scenario_model.leaf_scenarios)
    reloaded_leaves = sorted(reloaded_sm.leaf_scenarios)
    if not (orig_leaves == reloaded_leaves):
        raise RuntimeError(f"leaf_scenarios mismatch: {orig_leaves} != {reloaded_leaves}")

    def _const_value(c):
        # Constant has `.value` (scalar); TensorConstant has `.values` (nested list).
        return c.value if hasattr(c, "value") else c.values

    for leaf in orig_leaves:
        orig_p = scenario_model.get_scenario_problem(leaf)
        reloaded_p = reloaded_sm.get_scenario_problem(leaf)
        orig_consts = {c.symbol: _const_value(c) for c in orig_p.constants}
        reloaded_consts = {c.symbol: _const_value(c) for c in reloaded_p.constants}
        if not (orig_consts.keys() == reloaded_consts.keys()):
            raise RuntimeError(
                f"Scenario {leaf!r} constant symbol set mismatch: {set(orig_consts) ^ set(reloaded_consts)} differ"
            )
        for sym, val in orig_consts.items():
            reloaded_val = reloaded_consts[sym]
            same = (val == reloaded_val) if not hasattr(val, "__len__") else list(val) == list(reloaded_val)
            if not (same):
                raise RuntimeError(f"Scenario {leaf!r} constant {sym!r} mismatch: {val!r} != {reloaded_val!r}")

    print("Round-trip assertion passed: persisted problem + scenario model match the originals.")


def add_pool_metadata(session: Session, problem_db: ProblemDB, metadata_db: ProblemMetaDataDB) -> JinaPoolMetaData:
    """Attach the `JinaPoolMetaData` row JINA single-scenario needs, unless the problem already has one.

    Idempotent — safe to call against an already-migrated problem.
    """
    existing = metadata_db.jina_pool_metadata or []
    if existing:
        print("JinaPoolMetaData already persisted; leaving it as-is.")
        return existing[0]

    if not DistrictHeatingDataConfig.data_dir:
        raise DistrictHeatingDataError(
            "DH_DATA_DIR is not set — required to attach JinaPoolMetaData (it points the pool "
            "method at the same pre-computed candidate-pool CSVs)."
        )

    pool_metadata = JinaPoolMetaData(
        metadata_id=metadata_db.id,
        data_dir=DistrictHeatingDataConfig.data_dir,
        strategic_var_symbols=list(STRATEGIC_VAR_LABELS.keys()),
        obj_emphasis_symbols=POOL_OBJ_EMPHASIS_SYMBOLS,
        strategic_var_labels=STRATEGIC_VAR_LABELS,
        strategic_var_components=STRATEGIC_VAR_COMPONENTS,
        strategic_var_units=STRATEGIC_VAR_UNITS,
        default_domain_thresholds=DEFAULT_DOMAIN_THRESHOLDS,
        default_af_absolute_floors=DEFAULT_AF_ABSOLUTE_FLOORS,
        lambda_objective=POOL_LAMBDA_OBJECTIVE,
    )
    session.add(pool_metadata)
    session.commit()
    print(f"JinaPoolMetaData persisted for problem_id={problem_db.id}.")
    return pool_metadata


def _backfill_sessions(session: Session, problem_id: int) -> int:
    """Point existing JINA StateDB rows that have no problem_id at the newly persisted problem.

    Any existing JINA StateDB row (either method) has problem_id=None, because the old request-time code never set
    it. Pointing it at the persisted problem keeps session history from going blank once lookups filter by
    problem_id.

    Point it at the newly-persisted problem so session history doesn't go blank once lookups filter by problem_id.
    """
    kinds = (
        StateKind.DISTRICT_HEATING_ROBUST_ITERATE,
        StateKind.DISTRICT_HEATING_ROBUST_WISHLIST,
        StateKind.DISTRICT_HEATING_ITERATE,
        StateKind.DISTRICT_HEATING_WISHLIST,
    )
    statement = select(StateDB).where(StateDB.problem_id.is_(None))
    count = 0
    for state_db in session.exec(statement).all():
        if state_db.base_state is not None and state_db.base_state.kind in kinds:
            state_db.problem_id = problem_id
            session.add(state_db)
            count += 1
    if count:
        session.commit()
    return count


def main() -> None:
    """Register the district heating problem, its scenario model and JINA metadata in the server database."""
    if not DistrictHeatingDataConfig.data_dir:
        raise DistrictHeatingDataError(
            "DH_DATA_DIR is not set — required to build the district heating problem's data."
        )

    SQLModel.metadata.create_all(engine)  # additive: creates only missing tables

    with Session(engine) as session:
        user = session.exec(select(User).where(User.role.in_([UserRole.analyst, UserRole.admin]))).first()
        if user is None:
            raise RuntimeError("No analyst/admin user found in the database to own the new problem.")

        print("Building the district heating problem + scenario model (this takes a moment)...")
        problem, scenario_model = _build_problem_and_scenario_model()

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
            baseline_scenario=None,  # falls back to the "baseline" name heuristic
            compound_scenario_hook="desdeo.api.routers.district_heating_compound:build_pairwise_disruption_scenarios",
            compound_reference_hook="desdeo.api.routers.district_heating_compound:build_reference_scenarios",
            regret_pool_source="district_heating_csv",
            strategic_var_labels=STRATEGIC_VAR_LABELS,
            strategic_var_components=STRATEGIC_VAR_COMPONENTS,
            strategic_var_units=STRATEGIC_VAR_UNITS,
        )
        session.add(jina_metadata)
        session.commit()
        print("JinaMultiScenarioMetaData persisted.")

        add_pool_metadata(session, problem_db, metadata_db)

        problem_id = problem_db.id

        # Re-fetch through a fresh query so relationships (problem_metadata, scenario_models) are
        # populated from the DB rather than reused from the in-session objects just built.
        session.expire_all()
        reloaded_problem_db = session.get(ProblemDB, problem_id)
        reloaded_sm_db = session.get(ScenarioModelDB, sm_db.id)
        _assert_round_trip(problem, scenario_model, reloaded_problem_db, reloaded_sm_db)

        reloaded_pool_meta = (reloaded_problem_db.problem_metadata.jina_pool_metadata or [])[0]
        if not (reloaded_pool_meta.data_dir == DistrictHeatingDataConfig.data_dir):
            raise RuntimeError("JinaPoolMetaData data_dir mismatch")
        if not (reloaded_pool_meta.strategic_var_symbols == list(STRATEGIC_VAR_LABELS.keys())):
            raise RuntimeError("JinaPoolMetaData strategic_var_symbols mismatch")
        print("Round-trip assertion passed: persisted pool metadata matches what was written.")

        backfilled = _backfill_sessions(session, problem_id)
        print(f"Backfilled problem_id on {backfilled} existing session state row(s).")

    invalidate_context(problem_id)
    invalidate_pool_context(problem_id)

    _refresh_cell_ranges(problem_id)

    print(
        f"\nDone. Select problem_id={problem_id} in the UI to use JINA multi-scenario or "
        "JINA single-scenario with the district heating problem."
    )


def _refresh_cell_ranges(problem_id: int) -> None:
    """Precompute the combined method's per-cell attainable ranges and store them.

    This is the slow half of that method's first load - one payoff table per scenario - and it
    depends only on the problem and its scenario model, not on anything a decision maker does. Run
    here, once, it is a wait for whoever sets the problem up instead of a wait for every decision
    maker who opens the page.

    Failure is reported but not fatal: the ranges are a cache, and the method recomputes them at
    request time whenever they are absent or incomplete. A problem that is set up but slow to open
    beats a setup script that refuses to finish.
    """
    print("\nPrecomputing per-cell attainable ranges (one payoff table per scenario)...")
    try:
        count = store_cell_ranges(problem_id)
    except Exception as e:
        print(f"  WARNING: could not precompute cell ranges ({type(e).__name__}: {e}).")
        print("  The method still works - it will compute them on first load instead.")
        return
    print(f"  Stored ranges for {count} cell(s). The combined method will not re-solve for them.")


def refresh_cell_ranges_only() -> None:
    """Recompute and store the cell ranges for every problem that already has a JINA metadata row.

    For when the problem or its scenario model changed and the stored ranges no longer describe
    it. Cheaper than re-running the whole init, and safe to run at any time: the method validates
    what it reads and recomputes anything that does not fit.
    """
    with Session(engine) as session:
        rows = session.exec(select(_Meta)).all()
        problem_ids = sorted({row.metadata_instance.problem_id for row in rows if row.metadata_instance is not None})

    if not problem_ids:
        print("No problems have JINA multi-scenario metadata; nothing to refresh.")
        return

    for pid in problem_ids:
        print(f"\nProblem {pid}:")
        _refresh_cell_ranges(pid)


if __name__ == "__main__":
    import sys

    if "--refresh-cell-ranges" in sys.argv:
        refresh_cell_ranges_only()
    else:
        main()
