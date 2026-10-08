"""Data/scoring layer for the JINA single-scenario pool-matching interactive method.

Generic: works with any `ProblemDB` that has an attached `JinaPoolMetaData` row naming a
`data_dir` (pre-computed candidate-pool CSVs) and `strategic_var_symbols`. District heating was
the first problem this served, ported from the decision maker's own `the_DM_session.ipynb`
notebook (Shavazipour, Kwakkel & Miettinen, 2025) as-is — it is no longer special-cased here. See
`desdeo/api/db_init_district_heating.py` for how it (and any future problem) gets registered.

Everything here reads pre-computed candidate/scenario data from CSV files under a per-problem
`data_dir` and performs lookups/argmin scoring over it. Nothing here re-solves or re-optimizes
anything, though a `desdeo.problem.Problem` is still read (never solved) for objective/variable
metadata (names, units, bounds) — the pool CSVs' own columns are the actual data.
"""

from __future__ import annotations

import json
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from sqlmodel import Session

from desdeo.api.db import engine
from desdeo.api.models.problem import JinaPoolMetaData, ProblemDB
from desdeo.problem.schema import Problem

# Data-completeness check (not a Pareto filter): only designs with a feasible
# re-evaluation in every scenario are eligible for matching.
REQUIRE_FULL_COVERAGE = True


# An objective counts for antifragility only if some design has an upside above this.
_AF_UPSIDE_TOL = 1e-9


# Spreads smaller than this are treated as zero (normalize by 1 instead).
_MIN_SPREAD = 1e-9


class DistrictHeatingDataError(RuntimeError):
    """Raised when a configured data directory or its expected files are missing/unreadable."""


class JinaPoolError(RuntimeError):
    """Raised when a problem can't be used with the JINA single-scenario method.

    No pool metadata attached, no `data_dir`, or no `strategic_var_symbols` declared.
    """


# --------------------------------------------------------------------------------------------
# Context: everything derived from one problem_id, built once and cached.
# --------------------------------------------------------------------------------------------


@dataclass
class ObjectiveMeta:
    """Display metadata for one objective."""

    symbol: str
    name: str
    unit: str | None
    maximize: bool
    label: str


@dataclass
class StrategicVarMeta:
    """Display metadata for one strategic (first-stage) variable."""

    symbol: str
    name: str
    label: str
    component: str
    unit: str | None
    axis_max: float | None


@dataclass
class ScalarizerDef:
    """One scalarizer of the candidate pool: its family, augmentation rho and optional weights."""

    name: str
    family: str
    rho: float
    label: str
    weights: dict[str, float] | None = None
    emphasize: str | None = None  # objective symbol emphasized (generic_asf variants only), for meta display


@dataclass
class JinaPoolSettings:
    """Resolved per-problem settings from `JinaPoolMetaData`."""

    data_dir: str | None = None
    strategic_var_symbols: list[str] | None = None
    obj_emphasis_symbols: list[str] | None = None
    strategic_var_labels: dict[str, str] = field(default_factory=dict)
    strategic_var_components: dict[str, str] = field(default_factory=dict)
    strategic_var_units: dict[str, str] = field(default_factory=dict)
    default_domain_thresholds: dict[str, float] | None = None
    default_af_absolute_floors: dict[str, float] | None = None
    lambda_objective: str | None = None


@dataclass
class JinaPoolContext:
    """Everything needed to run the JINA single-scenario pool-matching method against one problem.

    Objective/strategic-variable metadata and scalarizer definitions, all derived from the problem's own `Problem` +
    `JinaPoolMetaData`. Does not hold the loaded pool itself (that's cached separately, keyed the same way, since
    loading is a slower/rarer operation).
    """

    problem_id: int
    obj_symbols: list[str]
    obj_meta: dict[str, ObjectiveMeta]
    strategic_symbols: list[str]
    strategic_meta: dict[str, StrategicVarMeta]
    scalarizer_defs: list[ScalarizerDef]
    data_dir: str
    lambda_objective: str | None
    settings: JinaPoolSettings


def _resolve_settings(problem_db: ProblemDB) -> JinaPoolSettings:
    meta_row: JinaPoolMetaData | None = None
    if problem_db.problem_metadata is not None:
        rows = problem_db.problem_metadata.jina_pool_metadata or []
        meta_row = rows[0] if rows else None

    if meta_row is None:
        return JinaPoolSettings()

    return JinaPoolSettings(
        data_dir=meta_row.data_dir,
        strategic_var_symbols=meta_row.strategic_var_symbols,
        obj_emphasis_symbols=meta_row.obj_emphasis_symbols,
        strategic_var_labels=meta_row.strategic_var_labels or {},
        strategic_var_components=meta_row.strategic_var_components or {},
        strategic_var_units=meta_row.strategic_var_units or {},
        default_domain_thresholds=meta_row.default_domain_thresholds,
        default_af_absolute_floors=meta_row.default_af_absolute_floors,
        lambda_objective=meta_row.lambda_objective,
    )


_context_cache: dict[int, JinaPoolContext] = {}
_context_locks: defaultdict[int, threading.Lock] = defaultdict(threading.Lock)


def get_pool_context(problem_id: int) -> JinaPoolContext:
    """Get (building and caching if needed) the `JinaPoolContext` for a problem."""
    if problem_id in _context_cache:
        return _context_cache[problem_id]

    with _context_locks[problem_id]:
        if problem_id in _context_cache:  # someone else finished building while we waited
            return _context_cache[problem_id]
        ctx = _build_pool_context(problem_id)
        _context_cache[problem_id] = ctx
        return ctx


def invalidate_pool_context(problem_id: int) -> None:
    """Drop a cached context (and any cached pool) — e.g. after re-seeding a problem's metadata."""
    _context_cache.pop(problem_id, None)
    _pool_cache.pop(problem_id, None)


def _build_pool_context(problem_id: int) -> JinaPoolContext:
    with Session(engine) as session:
        problem_db = session.get(ProblemDB, problem_id)
        if problem_db is None:
            raise JinaPoolError(f"Problem {problem_id} not found.")

        settings = _resolve_settings(problem_db)
        if not settings.data_dir:
            raise JinaPoolError(
                f"Problem {problem_id} ({problem_db.name!r}) has no attached pool metadata (or "
                "no data_dir set) — JINA single-scenario needs a JinaPoolMetaData row linked to "
                "it with data_dir pointing at its pre-computed candidate-pool CSVs. See "
                "desdeo/api/db_init_district_heating.py for how to build and attach one."
            )
        if not settings.strategic_var_symbols:
            raise JinaPoolError(
                f"Problem {problem_id} ({problem_db.name!r})'s pool metadata declares no "
                "strategic_var_symbols — JINA single-scenario needs at least one."
            )

        problem = Problem.from_problemdb(problem_db)
        obj_symbols = [o.symbol for o in problem.objectives]
        obj_by_symbol = {o.symbol: o for o in problem.objectives}
        obj_meta: dict[str, ObjectiveMeta] = {}
        for sym in obj_symbols:
            o = obj_by_symbol[sym]
            label = f"{o.name} ({o.unit})" if o.unit else o.name
            obj_meta[sym] = ObjectiveMeta(symbol=sym, name=o.name, unit=o.unit, maximize=o.maximize, label=label)

        var_by_symbol = {v.symbol: v for v in problem.variables}
        missing = [s for s in settings.strategic_var_symbols if s not in var_by_symbol]
        if missing:
            raise JinaPoolError(
                f"Problem {problem_id} ({problem_db.name!r})'s pool metadata names "
                f"strategic_var_symbols not present on the problem: {missing}."
            )
        strategic_symbols = [s for s in settings.strategic_var_symbols if s in var_by_symbol]
        strategic_meta: dict[str, StrategicVarMeta] = {}
        for sym in strategic_symbols:
            v = var_by_symbol[sym]
            label = settings.strategic_var_labels.get(sym, v.name)
            component = settings.strategic_var_components.get(sym, sym)
            unit = settings.strategic_var_units.get(sym)
            axis_max = float(v.upperbound) if v.upperbound is not None else None
            strategic_meta[sym] = StrategicVarMeta(
                symbol=sym, name=v.name, label=label, component=component, unit=unit, axis_max=axis_max
            )

        # 1 AASF + one generic-ASF emphasis variant per symbol in obj_emphasis_symbols (default:
        # all objectives) + GUESS + STOM — verbatim scalarizer families from the_DM_session.ipynb,
        # generalized from a fixed 6 (district heating's own notebook only ever emphasized 3 of
        # its 4 objectives; its seed sets obj_emphasis_symbols explicitly to reproduce that exact
        # set instead of defaulting to all 4).
        emphasis_symbols = settings.obj_emphasis_symbols if settings.obj_emphasis_symbols is not None else obj_symbols
        scalarizer_defs = [ScalarizerDef(name="aasf_diff_rho1e3", family="aasf", rho=1e-3, label="AASF")]
        for sym in emphasis_symbols:
            weights = {o: (3.0 if o == sym else 1.0) for o in obj_symbols}
            scalarizer_defs.append(
                ScalarizerDef(
                    name=f"generic_asf_{sym}",
                    family="generic_asf",
                    rho=1e-3,
                    weights=weights,
                    label=f"Emphasize {obj_meta[sym].label}",
                    emphasize=sym,
                )
            )
        scalarizer_defs.append(ScalarizerDef(name="guess_diff_tight", family="guess", rho=1e-3, label="GUESS"))
        scalarizer_defs.append(ScalarizerDef(name="stom", family="stom", rho=1e-3, label="STOM"))

        return JinaPoolContext(
            problem_id=problem_id,
            obj_symbols=obj_symbols,
            obj_meta=obj_meta,
            strategic_symbols=strategic_symbols,
            strategic_meta=strategic_meta,
            scalarizer_defs=scalarizer_defs,
            data_dir=settings.data_dir,
            lambda_objective=settings.lambda_objective,
            settings=settings,
        )


# --------------------------------------------------------------------------------------------
# Candidate pool loading
# --------------------------------------------------------------------------------------------


@dataclass
class CandidatePool:
    """The cached, read-only candidate pool, exactly as `the_DM_session.ipynb` builds it."""

    pool_transfer: pd.DataFrame
    candidate_ids: set[int]
    all_scenarios: list[str]
    ideal_sc: dict[tuple[str, str], float] = field(default_factory=dict)
    nadir_sc: dict[tuple[str, str], float] = field(default_factory=dict)
    global_ideal: dict[str, float] = field(default_factory=dict)
    global_nadir: dict[str, float] = field(default_factory=dict)


@dataclass
class MatchedSolution:
    """One matched candidate design, mirroring a `solutions_this_round` entry in the notebook."""

    design_id: int
    solution_number: int
    matched_by: list[str]
    n_scenarios: int
    rows: list[dict]
    worst_case: dict[str, float]
    best_case: dict[str, float]


def _deduplicate_strategic(df: pd.DataFrame, strategic_symbols: list[str]) -> pd.DataFrame:
    """Deduplicate candidate designs by strategic capacity variables (1.0 tolerance)."""
    seen: list[np.ndarray] = []
    unique_rows = []
    for _, row in df.iterrows():
        try:
            vals = np.array([float(row[sym]) for sym in strategic_symbols])
        except (KeyError, ValueError):
            continue
        if np.any(np.isnan(vals)):
            continue
        if not any(np.max(np.abs(vals - s)) < 1.0 for s in seen):
            seen.append(vals)
            unique_rows.append(row)
    return pd.DataFrame(unique_rows).reset_index(drop=True)


_pool_cache: dict[int, CandidatePool] = {}


def load_candidate_pool(ctx: JinaPoolContext) -> CandidatePool:
    """Load and cache the candidate pool for one problem's context.

    Ported as-is from cells 4/6/8/10 of the_DM_session.ipynb (just parametrized by `ctx` instead of module globals).
    Cached per `problem_id` (not by `ctx` identity — `JinaPoolContext` isn't hashable, holding plain `dict`s),
    invalidated together with the context via `invalidate_pool_context`.
    """
    if ctx.problem_id in _pool_cache:
        return _pool_cache[ctx.problem_id]

    data_dir = Path(ctx.data_dir)
    if not data_dir.exists():
        raise DistrictHeatingDataError(f"data_dir={ctx.data_dir!r} does not exist.")

    obj_cols = ctx.obj_symbols
    strategic_symbols = ctx.strategic_symbols

    summary_csv = data_dir / "summary.csv"
    transfer_csv = data_dir / "pairwise_transfer_matrix_long.csv"
    design_id_lookup_path = data_dir / "design_id_lookup.csv"

    if not summary_csv.exists() or not transfer_csv.exists():
        raise DistrictHeatingDataError(
            f"Missing summary.csv and/or pairwise_transfer_matrix_long.csv under {data_dir}."
        )

    summary = pd.read_csv(summary_csv)
    summary.columns = summary.columns.str.strip()
    summary = summary.dropna(subset=obj_cols).reset_index(drop=True)

    unique_df = _deduplicate_strategic(summary, strategic_symbols)
    unique_df["design_id"] = unique_df.index.astype(int)

    if design_id_lookup_path.exists():
        design_id_lookup = pd.read_csv(design_id_lookup_path)
        canon = unique_df.merge(
            design_id_lookup,
            left_on=["scenario", "ref_id", "scalarizer"],
            right_on=["source_design_scenario", "reference_id", "scalarizer"],
            how="left",
            suffixes=("", "_canon"),
        )
        if "design_id_canon" in canon.columns and canon["design_id_canon"].notna().any():
            unique_df["design_id"] = canon["design_id_canon"].fillna(unique_df["design_id"]).astype(int)

    try:
        transfer_df = pd.read_csv(transfer_csv, sep=";", decimal=",", encoding="utf-8-sig")
    except Exception:
        transfer_df = pd.read_csv(transfer_csv)
    transfer_df.columns = transfer_df.columns.str.strip()

    transfer_ok = transfer_df[transfer_df["status"] == "ok"].copy()
    all_scenarios = sorted(transfer_ok["target_operation_scenario"].unique())

    key_map = unique_df[["scenario", "ref_id", "scalarizer", "design_id"]].rename(
        columns={"scenario": "source_design_scenario", "ref_id": "reference_id"}
    )
    transfer_candidates = transfer_ok.merge(
        key_map, on=["source_design_scenario", "reference_id", "scalarizer"], how="inner"
    )

    candidate_ids = set(unique_df["design_id"])
    if REQUIRE_FULL_COVERAGE:
        n_sc = len(all_scenarios)
        coverage = transfer_candidates.groupby("design_id")["target_operation_scenario"].nunique()
        full_coverage_ids = set(coverage[coverage == n_sc].index)
        candidate_ids = candidate_ids & full_coverage_ids

    pool_transfer = transfer_candidates[transfer_candidates["design_id"].isin(candidate_ids)].copy()

    ideal_sc: dict[tuple[str, str], float] = {}
    nadir_sc: dict[tuple[str, str], float] = {}
    for obj in obj_cols:
        grp = pool_transfer.groupby("target_operation_scenario")[obj]
        for sc, val in grp.min().items():
            ideal_sc[(obj, sc)] = float(val)
        for sc, val in grp.max().items():
            nadir_sc[(obj, sc)] = float(val)

    global_ideal = {obj: float(pool_transfer[obj].min()) for obj in obj_cols}
    global_nadir = {obj: float(pool_transfer[obj].max()) for obj in obj_cols}

    pool = CandidatePool(
        pool_transfer=pool_transfer,
        candidate_ids=candidate_ids,
        all_scenarios=all_scenarios,
        ideal_sc=ideal_sc,
        nadir_sc=nadir_sc,
        global_ideal=global_ideal,
        global_nadir=global_nadir,
    )
    _pool_cache[ctx.problem_id] = pool
    return pool


# --------------------------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------------------------


def _safe_spread(spread: float) -> float:
    return spread if abs(spread) > _MIN_SPREAD else 1.0


def _aasf_score(
    pool: CandidatePool, design_rows: pd.DataFrame, g: dict[str, float], rho: float, obj_cols: list[str]
) -> float:
    terms = []
    for _, row in design_rows.iterrows():
        sc = row["target_operation_scenario"]
        for obj in obj_cols:
            spread = _safe_spread(pool.nadir_sc[(obj, sc)] - pool.ideal_sc[(obj, sc)])
            terms.append((float(row[obj]) - g[obj]) / spread)
    arr = np.array(terms)
    return float(np.max(arr) + rho * np.sum(arr))


def _generic_asf_score(
    pool: CandidatePool,
    design_rows: pd.DataFrame,
    g: dict[str, float],
    rho: float,
    weights: dict[str, float],
    obj_cols: list[str],
) -> float:
    g_shifted = {}
    for obj in obj_cols:
        w = max(float(weights.get(obj, 1.0)), 1e-12)
        g_shifted[obj] = pool.global_ideal[obj] + (g[obj] - pool.global_ideal[obj]) / w
    return _aasf_score(pool, design_rows, g_shifted, rho, obj_cols)


def _guess_score(
    pool: CandidatePool, design_rows: pd.DataFrame, g: dict[str, float], rho: float, obj_cols: list[str]
) -> float:
    terms = []
    for _, row in design_rows.iterrows():
        sc = row["target_operation_scenario"]
        for obj in obj_cols:
            denom = abs(pool.nadir_sc[(obj, sc)] - g[obj])
            denom = max(1e-09, denom)
            terms.append((1.0 / denom) * float(row[obj]))
    arr = np.array(terms)
    return float(np.max(arr) + rho * np.sum(arr))


def _stom_score(
    pool: CandidatePool, design_rows: pd.DataFrame, g: dict[str, float], rho: float, obj_cols: list[str]
) -> float:
    terms = []
    aug_terms = []
    for _, row in design_rows.iterrows():
        sc = row["target_operation_scenario"]
        for obj in obj_cols:
            denom = abs(g[obj] - pool.ideal_sc[(obj, sc)])
            denom = max(1e-09, denom)
            w_iq = 1.0 / denom
            gap = abs(float(row[obj]) - pool.ideal_sc[(obj, sc)])
            terms.append(w_iq * gap)
            aug_terms.append(w_iq * float(row[obj]))
    return float(np.max(np.array(terms)) + rho * np.sum(aug_terms))


def score_design(
    pool: CandidatePool,
    design_rows: pd.DataFrame,
    g: dict[str, float],
    scalarizer_def: ScalarizerDef,
    obj_cols: list[str],
) -> float:
    """Dispatch to the scalarizer family named in `scalarizer_def`. Lower score = better match."""
    fam = scalarizer_def.family
    if fam == "aasf":
        return _aasf_score(pool, design_rows, g, scalarizer_def.rho, obj_cols)
    if fam == "generic_asf":
        return _generic_asf_score(pool, design_rows, g, scalarizer_def.rho, scalarizer_def.weights or {}, obj_cols)
    if fam == "guess":
        return _guess_score(pool, design_rows, g, scalarizer_def.rho, obj_cols)
    if fam == "stom":
        return _stom_score(pool, design_rows, g, scalarizer_def.rho, obj_cols)
    raise ValueError(f"Unknown scalarizer family: {fam}")


def reference_point_from_percent(
    pool: CandidatePool, percent: dict[str, float], obj_cols: list[str]
) -> dict[str, float]:
    """0-100 'closeness to ideal' per objective (100 = global ideal, 0 = global nadir)."""
    out = {}
    for obj in obj_cols:
        pct = percent.get(obj, 50.0)
        frac = max(0.0, min(100.0, float(pct))) / 100.0
        out[obj] = pool.global_nadir[obj] + frac * (pool.global_ideal[obj] - pool.global_nadir[obj])
    return out


def reference_point_from_raw(values: dict[str, float], obj_cols: list[str]) -> dict[str, float]:
    """DM-given exact raw values for each objective, in its own units."""
    missing = [o for o in obj_cols if o not in values]
    if missing:
        raise ValueError(f"Missing objectives: {missing}. Must provide all of {obj_cols}")
    return {obj: float(values[obj]) for obj in obj_cols}


def midpoint_reference_point(pool: CandidatePool, obj_cols: list[str]) -> dict[str, float]:
    """Reference point halfway between the pool's ideal and nadir for each objective."""
    return {obj: 0.5 * (pool.global_ideal[obj] + pool.global_nadir[obj]) for obj in obj_cols}


def run_iteration(
    pool: CandidatePool,
    g: dict[str, float],
    already_shown_ids: set[int],
    solution_number_map: dict[int, int],
    obj_cols: list[str],
    scalarizer_defs: list[ScalarizerDef],
    max_solutions: int | None = None,
) -> list[MatchedSolution]:
    """Port of `run_iteration` from the_DM_session.ipynb (minus notebook I/O and plotting).

    Each scalarizer independently picks its best-matching, not-yet-shown design. Designs matched
    in an earlier round are never matched again (`already_shown_ids`), so each iteration surfaces
    genuinely new candidates. `already_shown_ids` and `solution_number_map` are mutated in place,
    mirroring the module-level state the notebook keeps across cells.
    """
    available_ids = [d for d in pool.candidate_ids if d not in already_shown_ids]
    if not available_ids:
        return []

    matches: dict[int, list[str]] = {}
    scores: dict[tuple[int, str], float] = {}
    for sdef in scalarizer_defs:
        best_id, best_score = None, float("inf")
        for design_id in available_ids:
            rows = pool.pool_transfer[pool.pool_transfer["design_id"] == design_id]
            s = score_design(pool, rows, g, sdef, obj_cols)
            if s < best_score:
                best_score, best_id = s, design_id
        if best_id is None:
            continue
        matches.setdefault(best_id, []).append(sdef.name)
        scores[(best_id, sdef.name)] = best_score

    if max_solutions is not None and len(matches) > max_solutions:
        design_best_score = {
            did: min(scores.get((did, sname), float("inf")) for sname in snames) for did, snames in matches.items()
        }
        top_ids = sorted(design_best_score, key=design_best_score.get)[:max_solutions]
        matches = {did: matches[did] for did in top_ids}

    next_number = max(solution_number_map.values(), default=0) + 1
    for d in matches:
        if d not in solution_number_map:
            solution_number_map[d] = next_number
            next_number += 1

    overlap = set(matches.keys()) & already_shown_ids
    if overlap:
        raise RuntimeError(
            f"Design(s) {overlap} were matched again after already being shown earlier; this should be impossible."
        )
    already_shown_ids.update(matches.keys())

    solutions: list[MatchedSolution] = []
    for design_id, scalarizer_names in matches.items():
        rows = pool.pool_transfer[pool.pool_transfer["design_id"] == design_id]
        worst_case = {obj: float(rows[obj].max()) for obj in obj_cols}
        best_case = {obj: float(rows[obj].min()) for obj in obj_cols}
        row_records = rows[["target_operation_scenario", *obj_cols]].to_dict("records")
        solutions.append(
            MatchedSolution(
                design_id=int(design_id),
                solution_number=solution_number_map[design_id],
                matched_by=scalarizer_names,
                n_scenarios=int(rows["target_operation_scenario"].nunique()),
                rows=row_records,
                worst_case=worst_case,
                best_case=best_case,
            )
        )
    return solutions


# --------------------------------------------------------------------------------------------
# Robustness + antifragility metrics — pool-schema-agnostic, unchanged from the original port.
# --------------------------------------------------------------------------------------------


def compute_robustness_metrics(
    transfer_df: pd.DataFrame,
    objectives_to_minimize: list[str],
    thresholds: dict[str, float] | None = None,
    normalize_regret: bool = True,
) -> dict[str, pd.DataFrame]:
    """Port of `robustness_metrics.compute_robustness_metrics`, verbatim (Shavazipour et al., Eq. 2/3).

    Max regret and, if `thresholds` given, domain criterion, from a pairwise transfer matrix.
    """
    df = transfer_df.copy()

    best_per_scenario = (
        df.groupby("target_operation_scenario")[objectives_to_minimize]
        .min()
        .rename(columns={obj: f"{obj}_best" for obj in objectives_to_minimize})
    )
    df = df.merge(best_per_scenario, on="target_operation_scenario", how="left")

    if normalize_regret:
        worst_per_scenario = (
            df.groupby("target_operation_scenario")[objectives_to_minimize]
            .max()
            .rename(columns={obj: f"{obj}_worst" for obj in objectives_to_minimize})
        )
        df = df.merge(worst_per_scenario, on="target_operation_scenario", how="left")

    for obj in objectives_to_minimize:
        raw_gap = df[obj] - df[f"{obj}_best"]
        if normalize_regret:
            spread = df[f"{obj}_worst"] - df[f"{obj}_best"]
            df[f"{obj}_regret"] = np.where(spread > 0, raw_gap / spread, 0.0)
        else:
            df[f"{obj}_regret"] = raw_gap

    id_cols = ["source_design_scenario", "reference_id", "scalarizer"]
    regret_cols = [f"{obj}_regret" for obj in objectives_to_minimize]
    max_regret_df = df.groupby(id_cols)[regret_cols].max().reset_index()
    max_regret_df.columns = id_cols + objectives_to_minimize
    max_regret_df["mean_normalized_regret"] = max_regret_df[objectives_to_minimize].mean(axis=1)

    result = {"max_regret": max_regret_df}

    if thresholds is not None:
        domain_rows = []
        for key, grp in df.groupby(id_cols):
            row = dict(zip(id_cols, key, strict=True))
            for obj in objectives_to_minimize:
                if obj in thresholds:
                    row[obj] = (grp[obj] <= thresholds[obj]).sum()
                else:
                    row[obj] = np.nan
            domain_rows.append(row)
        domain_df = pd.DataFrame(domain_rows)
        thresholded_objs = [o for o in objectives_to_minimize if o in thresholds]
        domain_df["mean_domain_criterion"] = domain_df[thresholded_objs].mean(axis=1)
        result["domain_criterion"] = domain_df

    return result


def compute_antifragility_metrics(  # noqa: C901  # metric definitions kept together
    transfer_df: pd.DataFrame,
    objectives_to_minimize: list[str],
    baseline_scenario: str,
    id_cols: tuple[str, ...] = ("source_design_scenario", "reference_id", "scalarizer"),
    upside: str = "max",
    absolute_floors: dict[str, float] | None = None,
    loss_floors: dict[str, float] | None = None,
    eps: float = 1e-9,
) -> dict[str, pd.DataFrame]:
    """Port of `antifragility_metrics.compute_antifragility_metrics`, verbatim.

    Upside-downside antifragility index: for each design and objective, every disrupted
    scenario gives a signed deviation from the design's own baseline performance
    (normalized by that scenario's ideal-nadir spread, same basis as `compute_robustness_metrics`).
    D = worst loss, U = best gain, AF = (U - D) / (U + D + eps) in [-1, 1].
    """
    id_cols = list(id_cols)
    df = transfer_df.copy()
    if "status" in df.columns:
        df = df[df["status"] == "ok"].copy()

    scen_col = "target_operation_scenario"
    if baseline_scenario not in set(df[scen_col].unique()):
        raise ValueError(f"Baseline scenario '{baseline_scenario}' not found in {scen_col}.")

    best_per_scenario = (
        df.groupby(scen_col)[objectives_to_minimize]
        .min()
        .rename(columns={o: f"{o}_best" for o in objectives_to_minimize})
    )
    worst_per_scenario = (
        df.groupby(scen_col)[objectives_to_minimize]
        .max()
        .rename(columns={o: f"{o}_worst" for o in objectives_to_minimize})
    )
    spread = worst_per_scenario.values - best_per_scenario.values
    spread_df = pd.DataFrame(spread, index=best_per_scenario.index, columns=[f"{o}_R" for o in objectives_to_minimize])

    base = (
        df[df[scen_col] == baseline_scenario]
        .set_index(id_cols)[objectives_to_minimize]
        .rename(columns={o: f"{o}_base" for o in objectives_to_minimize})
    )
    if base.index.has_duplicates:
        raise ValueError("Duplicate baseline rows for at least one design id triple.")

    dis = df[df[scen_col] != baseline_scenario].copy()
    dis = dis.join(base, on=id_cols, how="inner")
    dis = dis.join(spread_df, on=scen_col)

    dev_frames = []
    for o in objectives_to_minimize:
        d_raw = dis[f"{o}_base"] - dis[o]
        r = dis[f"{o}_R"].replace(0, np.nan)
        d = (d_raw / r).fillna(0.0)
        frame = dis[[*id_cols, scen_col]].copy()
        frame["objective"] = o
        frame["d"] = d.to_numpy()
        frame["d_raw"] = d_raw.to_numpy()
        frame["value"] = dis[o].to_numpy()
        dev_frames.append(frame)
    deviations = pd.concat(dev_frames, ignore_index=True)

    if loss_floors or absolute_floors:
        tol = 1e-9
        dv = deviations["d"].to_numpy()
        cls = np.full(len(deviations), "untouched", dtype=object)
        cls[dv > tol] = "gain"
        cls[dv < -tol] = "bounded_loss"
        frag = np.zeros(len(deviations), dtype=bool)
        for o in objectives_to_minimize:
            m = (deviations["objective"] == o).to_numpy()
            if absolute_floors and o in absolute_floors:
                frag |= m & (deviations["value"].to_numpy() > absolute_floors[o])
            if loss_floors and o in loss_floors:
                frag |= m & (-deviations["d_raw"].to_numpy() > loss_floors[o])
        cls[frag] = "fragile"
        deviations["event_class"] = cls

    def _summarize(grp: pd.DataFrame) -> pd.Series:
        out = {}
        for o in objectives_to_minimize:
            g = grp[grp["objective"] == o]
            d = g["d"].to_numpy()
            d_raw = g["d_raw"].to_numpy()
            scen = g[scen_col].to_numpy()

            losses = np.maximum(-d, 0.0)
            gains = np.maximum(d, 0.0)

            tol = 1e-9
            out[f"{o}_n_loss"] = int((d < -tol).sum())
            out[f"{o}_n_gain"] = int((d > tol).sum())

            d_val = losses.max() if len(losses) else 0.0
            u_val = (gains.mean() if upside == "mean" else gains.max()) if len(gains) else 0.0

            out[f"{o}_U"] = u_val
            out[f"{o}_D"] = d_val
            out[f"{o}_AF"] = (u_val - d_val) / (u_val + d_val + eps)

            if len(d):
                i_loss = int(np.argmin(d))
                i_gain = int(np.argmax(d))
                _dr = -d_raw[i_loss]
                out[f"{o}_D_raw"] = float(_dr) if _dr > 0 else 0.0
                _ur = d_raw[i_gain]
                out[f"{o}_U_raw"] = float(_ur) if _ur > 0 else 0.0
                out[f"{o}_worst_loss_scenario"] = str(scen[i_loss]) if d[i_loss] < 0 else None
                out[f"{o}_best_gain_scenario"] = str(scen[i_gain]) if d[i_gain] > 0 else None
            else:
                out[f"{o}_D_raw"] = 0.0
                out[f"{o}_U_raw"] = 0.0
                out[f"{o}_worst_loss_scenario"] = None
                out[f"{o}_best_gain_scenario"] = None
        return pd.Series(out)

    summary = deviations.groupby(id_cols, dropna=False).apply(_summarize, include_groups=False).reset_index()

    floor_objs = (set(loss_floors or {}) | set(absolute_floors or {})) & set(objectives_to_minimize)
    if floor_objs:
        if absolute_floors:
            worst_out = (
                df.groupby(id_cols)[objectives_to_minimize]
                .max()
                .rename(columns={o: f"{o}_worst_outcome" for o in objectives_to_minimize})
            )
            summary = summary.merge(worst_out, on=id_cols, how="left")
        for o in sorted(floor_objs):
            fragile = np.zeros(len(summary), dtype=bool)
            if loss_floors and o in loss_floors:
                fragile |= (summary[f"{o}_D_raw"] > loss_floors[o]).to_numpy()
            if absolute_floors and o in absolute_floors:
                fragile |= (summary[f"{o}_worst_outcome"] > absolute_floors[o]).to_numpy()
            summary[f"{o}_taleb_class"] = np.where(
                fragile, "fragile", np.where(summary[f"{o}_n_gain"] >= 1, "antifragile", "robust")
            )

    return {"deviations": deviations, "summary": summary}


def list_strategic_designs(pool: CandidatePool, strategic_symbols: list[str], obj_cols: list[str]) -> list[dict]:
    """Every design in the candidate pool.

    Strategic capacities, the scenario it was originally optimized for, and its full performance breakdown. Port of
    the design table built in `Vis_strategic_decisions.ipynb`. Purely a read/reshape of the already-loaded
    `pool.pool_transfer` (which carries the `fixed_*` capacity columns straight from
    `pairwise_transfer_matrix_long.csv`) — no new computation.
    """
    df = pool.pool_transfer
    rows = []
    for design_id, group in df.groupby("design_id"):
        first = group.iloc[0]
        strategic_vals = {sym: float(first[f"fixed_{sym}"]) for sym in strategic_symbols}
        breakdown = [
            {"scenario": r["target_operation_scenario"], **{obj: float(r[obj]) for obj in obj_cols}}
            for _, r in group.sort_values("target_operation_scenario").iterrows()
        ]
        rows.append(
            {
                "design_id": int(design_id),
                "source_design_scenario": str(first["source_design_scenario"]),
                "reference_id": int(first["reference_id"]),
                "scalarizer": str(first["scalarizer"]),
                "strategic_vals": strategic_vals,
                "breakdown": breakdown,
            }
        )
    rows.sort(key=lambda r: r["design_id"])
    return rows


def compute_wish_list_analysis(
    pool: CandidatePool,
    wish_list_ids: list[int],
    obj_cols: list[str],
    domain_thresholds: dict[str, float] | None = None,
    af_absolute_floors: dict[str, float] | None = None,
) -> dict:
    """Robustness + antifragility analysis for the current wish list.

    Computed exactly as `stage_2c_analysis.ipynb` does (cells 4, 14): max regret over the full pool, domain
    criterion over the wish list, antifragility over the full pool (for stable normalization) filtered down to the
    wish list for display.

    `domain_thresholds`/`af_absolute_floors` are the DM-facing robustness criteria the
    notebook has the DM hand-edit as constants before re-running; here they're caller-supplied,
    defaulting to the resolved per-problem settings.
    """
    domain_thresholds = domain_thresholds if domain_thresholds is not None else {}
    af_absolute_floors = af_absolute_floors if af_absolute_floors is not None else {}

    wish_design_ids = sorted(set(wish_list_ids))
    pt = pool.pool_transfer

    full_clean = pd.DataFrame(
        {
            "source_design_scenario": "pool",
            "reference_id": pt["design_id"].to_numpy(),
            "scalarizer": "n/a",
            "target_operation_scenario": pt["target_operation_scenario"].to_numpy(),
        }
    )
    for obj in obj_cols:
        full_clean[obj] = pt[obj].to_numpy()

    wish_clean = full_clean[full_clean["reference_id"].isin(wish_design_ids)].copy()

    robustness = compute_robustness_metrics(full_clean, obj_cols, thresholds=domain_thresholds)
    max_regret_df = robustness["max_regret"].rename(columns={"reference_id": "design_id"})
    max_regret_df = max_regret_df[max_regret_df["design_id"].isin(wish_design_ids)]

    domain_df = pd.DataFrame()
    if wish_design_ids:
        wish_robustness = compute_robustness_metrics(wish_clean, obj_cols, thresholds=domain_thresholds)
        domain_df = wish_robustness["domain_criterion"].rename(columns={"reference_id": "design_id"})

    baseline_scenario = next((s for s in pool.all_scenarios if "baseline" in s.lower()), pool.all_scenarios[0])
    af_pool = compute_antifragility_metrics(
        full_clean, obj_cols, baseline_scenario=baseline_scenario, absolute_floors=af_absolute_floors
    )
    af_all = af_pool["summary"].rename(columns={"reference_id": "design_id"})
    af_dev_all = af_pool["deviations"].rename(columns={"reference_id": "design_id"})

    af_objectives = [o for o in obj_cols if (af_all[f"{o}_U"] > _AF_UPSIDE_TOL).any()]

    af_wish = af_all[af_all["design_id"].isin(wish_design_ids)].copy()
    for o in af_objectives:
        af_wish[f"{o}_AF_pctile"] = af_wish[f"{o}_AF"].apply(lambda v, obj=o: 100.0 * (af_all[f"{obj}_AF"] < v).mean())
    af_dev_wish = af_dev_all[af_dev_all["design_id"].isin(wish_design_ids)].copy()

    return {
        "wish_list": wish_design_ids,
        "max_regret": _records(max_regret_df),
        "domain_criterion": _records(domain_df),
        "antifragility_summary": _records(af_wish),
        "antifragility_deviations": _records(af_dev_wish),
        "af_objectives": af_objectives,
        "baseline_scenario": baseline_scenario,
        "domain_thresholds": domain_thresholds,
        "af_absolute_floors": af_absolute_floors,
    }


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe list of dicts (NaN -> None, numpy scalars -> Python scalars)."""
    if df.empty:
        return []
    return json.loads(df.to_json(orient="records"))
