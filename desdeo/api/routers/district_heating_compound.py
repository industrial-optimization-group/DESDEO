"""District-heating-specific compound-disruption scenario builder.

The one existing implementation of the `jina_compound.py` hook contract. Ported from
`multi_scenario_combined_scenarios_analysis.ipynb`: builds all C(7,2) = 21 pairwise combinations
of the 7 non-baseline disruptions, using the decision maker's own `scenario_profiles1`/
`dh_problem_vectorized` modules (loaded dynamically from `DH_DATA_DIR`'s parent, same as the
district heating problem itself). Only ever imported when a problem's
`JinaMultiScenarioMetaData.compound_scenario_hook` actually points here — a generic problem with
no hook configured never touches this module or requires `DH_DATA_DIR` to be set.
"""

from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from itertools import combinations
from pathlib import Path

from desdeo.api.config import DistrictHeatingDataConfig
from desdeo.api.routers.district_heating_robust_data import JinaScenarioContext, JinaScenarioError
from desdeo.api.routers.district_heating_system_data import DistrictHeatingDataError
from desdeo.api.routers.jina_compound import CompoundScenarioSet

# Every pair among these 7 non-baseline disruptions, C(7,2) = 21 combined scenarios. Baseline is
# excluded (pairing anything with "no disruption" isn't a compound stress test).
DISRUPTION_ORDER = [
    "price_spike",
    "demand_spike",
    "DC_loss",
    "Bio_loss",
    "grid_outage",
    "EB1_outage",
    "EB2_outage",
]


def _dm_dir() -> Path:
    data_dir = DistrictHeatingDataConfig.data_dir
    if not data_dir:
        raise DistrictHeatingDataError("DH_DATA_DIR is not set.")
    return Path(data_dir).parent


def _load_dm_module(name: str, dm_dir: Path):
    """Load one of the DM's own modules by explicit file path.

    These modules import each other by bare name (`from base_data1 import ...`, `from config import ...`), some of
    them lazily inside function bodies — so `dm_dir` needs to stay on `sys.path` for the lifetime of the process,
    not just during this load.

    Critically, `uvicorn --app-dir=./desdeo/api/` (this project's own documented launch command)
    puts `desdeo/api/` on `sys.path`, which makes DESDEO's own `desdeo/api/config.py` importable
    under the bare name `config` too — so `dm_dir` must be *prepended*, not appended, or the DM's
    `base_data1.py` (`from config import CONSTANTS_CSV, ...`) silently resolves to the wrong
    `config` module. Confirmed nothing in `desdeo/` itself does a bare `import config`, so
    prepending can't shadow anything DESDEO actually relies on.
    """
    if str(dm_dir) not in sys.path:
        sys.path.insert(0, str(dm_dir))
    spec = importlib.util.spec_from_file_location(name, dm_dir / f"{name}.py")
    if spec is None or spec.loader is None:
        raise JinaScenarioError(f"Could not load DM module {name!r} from {dm_dir}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _disruption_params(base_data1, config) -> dict:
    historical_el_buy, _historical_el_sell = base_data1.load_electricity_price_spike_csv(config.PRICE_SPIKE_CSV)
    historical_demand = base_data1.load_demand_spike_csv(config.DEMAND_SPIKE_CSV)
    return {
        "price_spike": {"elec_price_spike_value": 1.0, "elec_price_spike_duration": len(historical_el_buy)},
        "demand_spike": {"demand_spike_value": 1.0, "demand_spike_duration": len(historical_demand)},
        "DC_loss": {"DC_loss_mult": 0.5, "DC_loss_duration": len(base_data1.BASE["D"])},
        "Bio_loss": {"bio_avail_mult": 0.0, "bio_avail_duration": 48},
        "grid_outage": {"grid_import_mult": 0.0, "grid_import_duration": 12},
        "EB1_outage": {"eb1_avail_mult": 0.0, "eb1_outage_duration": 48},
        "EB2_outage": {"eb2_avail_mult": 0.0, "eb2_outage_duration": 48},
    }


def _load_dm_modules_and_params():
    dm_dir = _dm_dir()
    dh_problem_vectorized = _load_dm_module("dh_problem_vectorized", dm_dir)
    base_data1 = _load_dm_module("base_data1", dm_dir)
    config = _load_dm_module("config", dm_dir)
    scenario_profiles1 = _load_dm_module("scenario_profiles1", dm_dir)

    historical_el_buy, historical_el_sell = base_data1.load_electricity_price_spike_csv(config.PRICE_SPIKE_CSV)
    historical_demand = base_data1.load_demand_spike_csv(config.DEMAND_SPIKE_CSV)
    disruption_params = _disruption_params(base_data1, config)

    return {
        "dh_problem_vectorized": dh_problem_vectorized,
        "scenario_profiles1": scenario_profiles1,
        "historical_el_buy": historical_el_buy,
        "historical_el_sell": historical_el_sell,
        "historical_demand": historical_demand,
        "disruption_params": disruption_params,
    }


@lru_cache(maxsize=1)
def _build_pairwise_disruption_scenarios_cached() -> tuple[list[str], dict]:
    """Build the 21 pairwise combined-disruption deterministic `Problem`s, cached.

    This step is comparatively fast (no payoff-table solve, just `Problem` construction), unlike the main robust
    context, so it's fine to keep it separate from that cache.
    """
    m = _load_dm_modules_and_params()
    scenario_profiles1, disruption_params = m["scenario_profiles1"], m["disruption_params"]

    combined_scenarios = []
    combo_names = []
    pair_components: dict[str, tuple[str, str]] = {}
    for a, b in combinations(DISRUPTION_ORDER, 2):
        name = f"{a}_plus_{b}"
        merged_params = {**disruption_params[a], **disruption_params[b]}
        sc = scenario_profiles1.build_january_disruption_scenario(
            params=merged_params,
            event_start="middle",
            historical_el_buy=m["historical_el_buy"],
            historical_el_sell=m["historical_el_sell"],
            historical_demand=m["historical_demand"],
            name=name,
        )
        combined_scenarios.append(sc)
        combo_names.append(name)
        pair_components[name] = (a, b)

    return combo_names, {
        "scenarios": combined_scenarios,
        "dh_problem_vectorized": m["dh_problem_vectorized"],
        "pair_components": pair_components,
    }


def build_pairwise_disruption_scenarios(ctx: JinaScenarioContext) -> CompoundScenarioSet:
    """The `compound_scenario_hook` implementation for the district heating problem.

    Builds each combined scenario's deterministic `Problem` on `ctx.problem` (the persisted base problem), matching
    the notebook's own `build_dh_scenario_model(combined_scenarios, base_problem=...)`.
    """
    combo_names, built = _build_pairwise_disruption_scenarios_cached()
    dh_problem_vectorized = built["dh_problem_vectorized"]
    combo_model = dh_problem_vectorized.build_dh_scenario_model(built["scenarios"], base_problem=ctx.problem)
    combo_problems = {name: combo_model.get_scenario_problem(name) for name in combo_names}
    return CompoundScenarioSet(
        names=combo_names,
        problems=combo_problems,
        description=(
            f"all {len(combo_names)} pairwise combinations of the {len(DISRUPTION_ORDER)} non-baseline disruptions"
        ),
        pair_components=built["pair_components"],
    )


@lru_cache(maxsize=1)
def _build_reference_scenarios_cached() -> tuple[list[str], dict]:
    """Build the 8 reference deterministic `Problem`s (baseline + each of the 7 single disruptions alone).

    Needed to compute super-additivity: how far a combined scenario's outcome runs beyond the sum of its two
    single-disruption effects.
    """
    m = _load_dm_modules_and_params()
    scenario_profiles1, disruption_params = m["scenario_profiles1"], m["disruption_params"]

    names = ["baseline", *DISRUPTION_ORDER]
    scenarios = [
        scenario_profiles1.build_january_disruption_scenario(
            params={},
            event_start="middle",
            historical_el_buy=m["historical_el_buy"],
            historical_el_sell=m["historical_el_sell"],
            historical_demand=m["historical_demand"],
            name="baseline",
        )
    ]
    for a in DISRUPTION_ORDER:
        scenarios.append(
            scenario_profiles1.build_january_disruption_scenario(
                params=disruption_params[a],
                event_start="middle",
                historical_el_buy=m["historical_el_buy"],
                historical_el_sell=m["historical_el_sell"],
                historical_demand=m["historical_demand"],
                name=a,
            )
        )

    return names, {"scenarios": scenarios, "dh_problem_vectorized": m["dh_problem_vectorized"]}


def build_reference_scenarios(ctx: JinaScenarioContext) -> CompoundScenarioSet:
    """The `compound_reference_hook` implementation for the district heating problem.

    Baseline + each single disruption alone, for `jina_compound.compute_superadditivity` to subtract against
    `build_pairwise_disruption_scenarios`'s combo results.
    """
    names, built = _build_reference_scenarios_cached()
    dh_problem_vectorized = built["dh_problem_vectorized"]
    ref_model = dh_problem_vectorized.build_dh_scenario_model(built["scenarios"], base_problem=ctx.problem)
    ref_problems = {name: ref_model.get_scenario_problem(name) for name in names}
    return CompoundScenarioSet(
        names=names,
        problems=ref_problems,
        description="baseline + each single disruption alone",
    )
