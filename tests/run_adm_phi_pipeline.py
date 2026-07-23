"""tests/run_adm_phi_pipeline.py — ADM + PHI experimental pipeline (class-based)."""
import json
from pathlib import Path
from dataclasses import dataclass, field
import numpy as np
from desdeo.adm.ADMAfsar import ADMAfsar
from desdeo.adm.ADMChen import ADMChen
from desdeo.tools.indicators_unary import phi
from desdeo.emo.options.algorithms import rvea_options, nsga3_options
from desdeo.emo.options.templates import emo_constructor, ReferencePointOptions


def _serialize(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.integer, np.floating)):
        return float(x)
    return x


def _to_array(x, n_obj):
    """Normalize ideal/nadir/preference points that may come as dict or array into a flat np.ndarray."""
    if isinstance(x, dict):
        return np.array(list(x.values()), dtype=float)
    if x is None:
        return np.zeros(n_obj) if n_obj else np.array([])
    return np.asarray(x, dtype=float)


def _to_preference_dict(pref, problem) -> dict:
    """Convert a preference that may come as array or dict into the dict format expected by ReferencePointOptions."""
    if isinstance(pref, dict):
        return pref
    arr = np.asarray(pref, dtype=float).flatten()
    symbols = [obj.symbol for obj in problem.objectives]
    return dict(zip(symbols, arr.tolist()))


def _extract_objectives(result, n_obj: int, problem=None) -> np.ndarray:
    """Extract the objective-space front from an EMOResult.
    In DESDEO 2.0, EMOResult exposes `optimal_outputs`, whose exact internal
    type/shape can vary: a polars DataFrame, a list of per-solution dicts
    keyed by objective symbol, a single dict of column-wise arrays, or a
    plain 2D array. This resolves to a (n_solutions, n_obj) array strictly
    ordered by the problem's objective symbols, preferring the "_min"
    (minimization-normalized) columns when present, since those are the
    ones consistent with what the ADM/indicators expect. If the symbols
    cannot be matched, it raises a clear error showing the real
    columns/keys instead of silently grabbing extra columns (e.g.
    constraint values mixed in with objectives).
    """
    if not hasattr(result, "optimal_outputs"):
        available = list(type(result).model_fields.keys())
        raise AttributeError(
            "EMOResult has no 'optimal_outputs' field. Available fields: " + str(available)
        )
    raw = result.optimal_outputs
    symbols = [obj.symbol for obj in problem.objectives] if problem is not None else None
    if hasattr(raw, "columns") and hasattr(raw, "to_numpy"):
        cols = list(raw.columns)
        if symbols is not None:
            min_cols = [s + "_min" for s in symbols]
            if all(c in cols for c in min_cols):
                return raw.select(min_cols).to_numpy().astype(float)
            if all(s in cols for s in symbols):
                return raw.select(symbols).to_numpy().astype(float)
        raise KeyError(
            "Could not match problem objective symbols to DataFrame columns. "
            "Expected symbols: " + str(symbols) + ". Actual columns: " + str(cols)
        )
    if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], dict):
        keys = list(raw[0].keys())
        if symbols is not None:
            min_keys = [s + "_min" for s in symbols]
            if all(k in keys for k in min_keys):
                return np.array([[row[k] for k in min_keys] for row in raw], dtype=float)
            if all(s in keys for s in symbols):
                return np.array([[row[s] for s in symbols] for row in raw], dtype=float)
            raise KeyError(
                "Could not match problem objective symbols to optimal_outputs keys. "
                "Expected symbols: " + str(symbols) + ". "
                "Actual keys in optimal_outputs[0]: " + str(keys)
            )
        if len(keys) == n_obj:
            return np.array([list(row.values()) for row in raw], dtype=float)
        raise ValueError(
            "optimal_outputs entries have " + str(len(keys)) + " keys (" + str(keys) + "), "
            "but the problem has " + str(n_obj) + " objectives. Pass `problem` to _extract_objectives "
            "to resolve the correct keys."
        )
    if isinstance(raw, dict):
        keys = list(raw.keys())
        if symbols is not None:
            min_keys = [s + "_min" for s in symbols]
            if all(k in keys for k in min_keys):
                return np.column_stack([np.asarray(raw[k], dtype=float) for k in min_keys])
            if all(s in keys for s in symbols):
                return np.column_stack([np.asarray(raw[s], dtype=float) for s in symbols])
        if len(keys) == n_obj:
            return np.column_stack([np.asarray(v, dtype=float) for v in raw.values()])
        raise KeyError(
            "Could not match problem objective symbols to optimal_outputs keys. "
            "Expected symbols: " + str(symbols) + ". Actual keys: " + str(keys)
        )
    arr = np.asarray(raw, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(-1, n_obj)
    if arr.ndim != 2 or arr.shape[1] != n_obj:
        raise ValueError(
            "Extracted objective array has shape " + str(arr.shape) + ", expected (*, " + str(n_obj) + "). "
            "Raw type: " + str(type(raw))
        )
    return arr


@dataclass
class MethodFrontResult:
    """Holds the objective-space front produced by one method in one iteration,
    plus the per-generation history of fronts collected along the way."""
    method_name: str
    solution_ids: list
    objectives: np.ndarray
    generation_fronts: list  # list[np.ndarray], one entry per completed generation checkpoint


ALGORITHM_OPTION_BUILDERS = {
    "iRVEA": rvea_options,
    "iNSGA-III": nsga3_options,
}


class RealAlgorithmRunner:
    """Runs a real DESDEO EA (via emo_constructor) for one interactive iteration.
    To obtain a genuine per-generation trajectory (rather than duplicating the
    final result), the algorithm is re-run from scratch at each generation
    checkpoint g = 1..generations_per_iteration, keeping the same seed so the
    run is reproducible. Only the front from the final checkpoint (g ==
    generations_per_iteration) is used to seed the next ADM interaction; all
    checkpoints are kept to compute a real per-generation PHI/HV trajectory.
    """

    def __init__(self, method_name: str, problem, generations_per_iteration: int, seed: int):
        self.method_name = method_name
        self.problem = problem
        self.generations_per_iteration = generations_per_iteration
        self.seed = seed

    def _run_for_generations(self, n_generations: int, preference_dict: dict) -> np.ndarray:
        options = ALGORITHM_OPTION_BUILDERS[self.method_name]()
        options.template.seed = self.seed
        options.template.termination.max_generations = n_generations
        options.preference = ReferencePointOptions(preference=preference_dict)
        run_fn, extras = emo_constructor(options, self.problem)
        result = run_fn()
        return _extract_objectives(result, len(self.problem.objectives), self.problem)

    def run_iteration(self, iteration: int, preference_dict: dict) -> MethodFrontResult:
        generation_fronts = []
        objectives = None
        for g in range(1, self.generations_per_iteration + 1):
            objectives = self._run_for_generations(g, preference_dict)
            generation_fronts.append(objectives)
        solution_ids = [f"it{iteration}_{self.method_name}_{j + 1}" for j in range(len(objectives))]
        return MethodFrontResult(
            method_name=self.method_name,
            solution_ids=solution_ids,
            objectives=objectives,
            generation_fronts=generation_fronts,
        )


@dataclass
class IterationRecord:
    """Structured result for a single ADM iteration."""
    iteration: int
    phase: str
    composite_front: list
    preference_information: dict
    hypervolume_by_method: dict
    reference_vector_assignments: list
    max_assigned_vector: dict
    phi_per_method: dict = field(default_factory=dict)


class ExperimentPipeline:
    """Runs the full ADM-driven interactive optimization experiment and computes PHI."""

    def __init__(
        self,
        problem,
        methods: list,
        learning_iterations: int,
        decision_iterations: int,
        generations_per_iteration: int,
        seed: int,
        adm_name: str = "afsar",
        number_of_vectors: int = 20,
        nadir_margin: float = 0.05,
    ):
        self.problem = problem
        self.methods = methods
        self.learning_iterations = learning_iterations
        self.decision_iterations = decision_iterations
        self.generations_per_iteration = generations_per_iteration
        self.seed = seed
        self.number_of_vectors = number_of_vectors
        self.nadir_margin = nadir_margin
        self.rng = np.random.default_rng(seed)
        np.random.seed(seed)
        self.n_obj = len(problem.objectives)
        self.adm = self._build_adm(adm_name)

        # reference_vectors is read from the ADM's public property
        # (reference_vectors_), exposed specifically so the pipeline (and any
        # notebook/UI) can show the ADM's internal vectors, instead of using a
        # getattr fallback to np.eye(n_obj).
        self.reference_vectors = self.adm.reference_vectors_

        # The ADM (e.g. ADMAfsar) computes and stores the true ideal/nadir on
        # its problem copy via payoff_table_method. Read them from the
        # problem itself (source of truth) instead of guessing/falling back.
        self.ideal = _to_array(self.adm.problem.get_ideal_point(), self.n_obj)
        self.nadir = _to_array(self.adm.problem.get_nadir_point(), self.n_obj)
        if self.nadir.size == 0 or np.allclose(self.nadir, self.ideal):
            self.nadir = np.ones(self.n_obj)

        # CHANGE 1: ADMAfsar keeps its own `true_ideal` / `true_nadir`
        # attributes (populated by payoff_table_method as plain dicts, e.g.
        # {"f1": 0.02, "f2": 0.15, ...}), and its internal `_asf_score`
        # helper feeds them straight into np.asarray(..., dtype=float)
        # without converting them first. That mismatch is exactly what
        # raised "TypeError: float() argument must be a string or a real
        # number, not 'dict'" inside ADMAfsar._asf_score. Overwriting these
        # two attributes on the ADM instance with the already-normalized
        # array versions (self.ideal / self.nadir) fixes this at the source,
        # without needing to edit ADMAfsar.py itself.
        if hasattr(self.adm, "true_ideal"):
            self.adm.true_ideal = self.ideal
        if hasattr(self.adm, "true_nadir"):
            self.adm.true_nadir = self.nadir

        self.phi_calculator = phi(ideal=self.ideal)
        self.runners = [
            RealAlgorithmRunner(name, problem, generations_per_iteration, seed)
            for name in methods
        ]
        self.iteration_records: list[IterationRecord] = []
        self.phi_learning_values: list[float] = []
        self.phi_decision_values: list[float] = []

    def _build_adm(self, adm_name: str):
        if adm_name.lower() == "afsar":
            # number_of_vectors is an explicit constructor argument of
            # ExperimentPipeline (default 20) instead of a placeholder.
            return ADMAfsar(
                self.problem,
                self.learning_iterations,
                self.decision_iterations,
                number_of_vectors=self.number_of_vectors,
            )
        if adm_name.lower() == "chen":
            pareto_front = self.rng.random((20, self.n_obj))
            return ADMChen(
                self.problem, self.learning_iterations, self.decision_iterations, pareto_front=pareto_front
            )
        raise ValueError("Unsupported ADM")

    def _sync_nadir_to_adm(self) -> None:
        """CHANGE 4: propagates self.nadir back onto the ADM instance
        (true_nadir), whenever self.nadir is expanded.

        CHANGES 2 and 3 kept self.nadir valid for the pipeline's own PHI
        computation, but never told the ADM about it. ADMAfsar._asf_score
        keeps reading its OWN self.adm.true_nadir (only set once, at
        __init__, via CHANGE 1) when scoring candidate reference vectors
        for the next preference. Since that stale, too-small nadir never
        got updated, ADMAfsar.get_next_preference kept generating
        increasingly extreme RPs iteration after iteration (confirmed
        empirically: RP components reaching ~3.13 while our nadir was only
        ~2.2). Each time, CHANGE 3 expanded self.nadir to cover that RP,
        but the ADM used its still-stale nadir to produce an EVEN MORE
        extreme RP next time -- an unbounded feedback loop that made
        final_nadir blow up to ~100 and left phi pinned near a constant
        -0.9954 instead of varying meaningfully.

        Calling this right after any nadir expansion closes that loop: the
        ADM always scores against the same up-to-date nadir the pipeline
        uses for PHI, so RPs stop drifting to extreme values.
        """
        if hasattr(self.adm, "true_nadir"):
            self.adm.true_nadir = self.nadir

    def _expand_nadir(self, points: np.ndarray) -> None:
        """Shared helper: expands self.nadir so it keeps dominating every
        point in `points` (shape (*, n_obj)), applying nadir_margin on top
        of the observed max whenever the current nadir is exceeded. Also
        keeps the ADM's own nadir copy in sync (CHANGE 4) so it never
        scores preferences against a stale, smaller nadir."""
        if points.size == 0:
            return
        observed_max = points.reshape(-1, self.n_obj).max(axis=0)
        if np.any(observed_max > self.nadir):
            self.nadir = np.maximum(self.nadir, observed_max * (1.0 + self.nadir_margin))
            self._sync_nadir_to_adm()

    def _update_nadir_from_observations(self, method_fronts: list) -> None:
        """CHANGE 2: expands self.nadir on the fly whenever any observed
        objective vector (final front or any per-generation checkpoint)
        exceeds the current nadir estimate.

        ADMAfsar.payoff_table_method only approximates the nadir via
        single-objective optimizations run BEFORE the interactive process
        starts. Because iRVEA/iNSGA-III explore regions guided by changing
        reference points, they can (and do) produce objective values that
        exceed that initial estimate. Any hypervolume computed against a
        nadir that does not dominate the front is ill-defined, and this is
        what originally caused the systematic degenerate phi == -1.0
        (std == 0.0) results in indicators_unary.phi.RP_nondom_cal /
        RP_dom_cal.

        A `nadir_margin` (default 5%) is added on top of the observed max
        so the nadir keeps dominating slightly beyond what's been seen so
        far, instead of sitting exactly on the boundary.
        """
        all_fronts = [mf.objectives for mf in method_fronts] + [
            gen_front for mf in method_fronts for gen_front in mf.generation_fronts
        ]
        if not all_fronts:
            return
        self._expand_nadir(np.vstack(all_fronts))

    def _update_nadir_from_preference(self, pref_array: np.ndarray) -> None:
        """CHANGE 3: expands self.nadir so it also dominates the reference
        point (RP) generated by the ADM, since ADMAfsar.get_next_preference
        can generate a RP whose components exceed the current nadir. This
        is combined with CHANGE 4 (_sync_nadir_to_adm, called inside
        _expand_nadir) so that expanding the nadir here also immediately
        feeds back into the ADM's own scoring, preventing runaway RP
        growth across iterations.
        """
        self._expand_nadir(pref_array.reshape(1, -1))

    def _phi_for_front(self, front: np.ndarray, pref_array: np.ndarray) -> tuple[float, float, float]:
        """Computes (positive, negative, phi) for a single front against the current reference point."""
        pos, total, neg, _rp = self.phi_calculator.get_phi(front, pref_array, self.nadir)
        phi_value = total - neg
        return float(pos), float(neg), float(phi_value)

    def _build_assignments_from_adm(self, all_solution_ids: list) -> tuple[list, dict]:
        """Builds the per-vector assignment report using the ADM's own internal
        assignment state (assigned_vectors_), instead of recomputing the
        cosine-similarity assignment separately via ReferenceVectorAssigner.

        NOTE: self.adm.assigned_vectors_ is indexed over the ADM's internal
        composite_front (built by generate_composite_front across all methods'
        fronts), which may differ in size/order from all_solution_ids if the
        non-dominated filtering inside the ADM dropped dominated solutions.
        We report against the ADM's own composite front length; solution ids
        beyond that length (if any) are simply not attributed to a vector.
        """
        assigned_idx = self.adm.assigned_vectors_
        n_vectors = self.reference_vectors.shape[0]
        if assigned_idx is None:
            counts = np.zeros(n_vectors, dtype=int)
            assignments = [
                {"vector_id": f"V{vid + 1}", "assigned_solution_ids": [], "assigned_count": 0}
                for vid in range(n_vectors)
            ]
            max_assigned = {"vector_id": "V1", "assigned_count": 0}
            return assignments, max_assigned

        counts = np.bincount(assigned_idx, minlength=n_vectors)
        ids_for_assignment = all_solution_ids[: len(assigned_idx)]
        assignments = []
        for vid in range(n_vectors):
            idx = np.where(assigned_idx == vid)[0]
            assignments.append({
                "vector_id": f"V{vid + 1}",
                "assigned_solution_ids": [ids_for_assignment[i] for i in idx if i < len(ids_for_assignment)],
                "assigned_count": int(counts[vid]),
            })
        max_vid = int(np.argmax(counts)) if len(counts) else 0
        max_assigned = {"vector_id": f"V{max_vid + 1}", "assigned_count": int(counts[max_vid]) if len(counts) else 0}
        return assignments, max_assigned

    def run(self) -> dict:
        initial_reference_point = _serialize(self.adm.preference)
        current_preference_dict = _to_preference_dict(self.adm.preference, self.problem)
        current_pref_array = _to_array(self.adm.preference, self.n_obj)

        # CHANGE 3 (cont.): also validate/expand the nadir against the very
        # first (initial) preference point, before the loop starts using it.
        self._update_nadir_from_preference(current_pref_array)

        total_iterations = self.learning_iterations + self.decision_iterations
        for iteration in range(1, total_iterations + 1):
            phase = "learning" if iteration <= self.learning_iterations else "decision"
            method_fronts = [
                runner.run_iteration(iteration, current_preference_dict) for runner in self.runners
            ]

            # CHANGE 2: keep the nadir valid (dominating) w.r.t. every
            # objective vector observed so far, BEFORE computing any
            # hypervolume/phi indicator for this iteration. CHANGE 4 keeps
            # self.adm.true_nadir in sync automatically as part of this.
            self._update_nadir_from_observations(method_fronts)

            composite_front = []
            for mf in method_fronts:
                for sid, obj in zip(mf.solution_ids, mf.objectives):
                    composite_front.append({
                        "solution_id": sid,
                        "method": mf.method_name,
                        "objectives": obj.tolist(),
                    })
            all_solution_ids = [entry["solution_id"] for entry in composite_front]
            # Feed each method's raw front separately, as ADMAfsar.get_next_preference(*fronts)
            # builds its own accumulated composite_front internally via generate_composite_front,
            # and now also stores assigned_vectors_ for external inspection. Thanks to CHANGE 4,
            # the ADM scores this against the SAME up-to-date nadir the pipeline uses.
            pref = self.adm.get_next_preference(*[mf.objectives for mf in method_fronts])
            pref_serialized = _serialize(pref)
            pref_array = _to_array(pref, self.n_obj)

            # CHANGE 3: the newly generated RP must also be dominated by the
            # nadir BEFORE it is used as current_pref_array in the next
            # iteration's PHI computations. CHANGE 4 re-syncs the ADM here too.
            self._update_nadir_from_preference(pref_array)

            # assignments come directly from the ADM's exposed state
            # (reference_vectors_ / assigned_vectors_) instead of a separate
            # ReferenceVectorAssigner recomputing cosine similarity.
            assignments, max_assigned = self._build_assignments_from_adm(all_solution_ids)

            # Positive/negative hypervolume per generation, computed against the
            # reference point that was ACTIVE during this iteration's runs
            # (current_pref_array), not the one produced afterwards.
            hv_by_method = {}
            phi_per_method = {}
            for mf in method_fronts:
                pos_series, neg_series, phi_series = [], [], []
                for gen_front in mf.generation_fronts:
                    pos_g, neg_g, phi_g = self._phi_for_front(gen_front, current_pref_array)
                    pos_series.append(pos_g)
                    neg_series.append(neg_g)
                    phi_series.append(phi_g)
                hv_by_method[mf.method_name] = {
                    "positive_hypervolume_per_generation": pos_series,
                    "negative_hypervolume_per_generation": neg_series,
                    "phi_per_generation": phi_series,
                    "phi_iteration": phi_series[-1] if phi_series else 0.0,
                }
                phi_per_method[mf.method_name] = phi_series[-1] if phi_series else 0.0
            iteration_phi = float(np.mean(list(phi_per_method.values()))) if phi_per_method else 0.0
            if phase == "learning":
                self.phi_learning_values.append(iteration_phi)
            else:
                self.phi_decision_values.append(iteration_phi)
            self.iteration_records.append(IterationRecord(
                iteration=iteration,
                phase=phase,
                composite_front=composite_front,
                preference_information={
                    "type": "reference_point",
                    "reference_point": pref_serialized,
                    "selected_reference_vector": max_assigned["vector_id"],
                    "selection_rule": "least_assigned_vector_for_exploration"
                    if phase == "learning"
                    else "max_assigned_vector_as_roi",
                    "description": "auto-generated preference from ADM",
                },
                hypervolume_by_method=hv_by_method,
                reference_vector_assignments=assignments,
                max_assigned_vector=max_assigned,
                phi_per_method=phi_per_method,
            ))
            current_preference_dict = _to_preference_dict(pref, self.problem)
            current_pref_array = pref_array
        return self._build_output(initial_reference_point)

    def _build_output(self, initial_reference_point) -> dict:
        problem_name = getattr(self.problem, "name", None) or "DTLZ2"
        phi_learn_total = float(np.sum(self.phi_learning_values)) if self.phi_learning_values else 0.0
        phi_learn_std = float(np.std(self.phi_learning_values)) if self.phi_learning_values else 0.0
        phi_dec_total = float(np.sum(self.phi_decision_values)) if self.phi_decision_values else 0.0
        phi_dec_std = float(np.std(self.phi_decision_values)) if self.phi_decision_values else 0.0
        return {
            "experiment_id": f"{problem_name}_adm_phi_{self.seed}",
            "problem": {
                "name": problem_name,
                "objectives": self.n_obj,
                "variables": len(self.problem.variables),
            },
            "methods": self.methods,
            "adm_configuration": {
                "learning_iterations": self.learning_iterations,
                "decision_iterations": self.decision_iterations,
                "generations_per_iteration": self.generations_per_iteration,
                "seed": self.seed,
            },
            "initial_reference_point": initial_reference_point,
            "final_nadir": _serialize(self.nadir),
            "reference_vectors": [
                {"vector_id": f"V{i+1}", "direction": _serialize(vec)}
                for i, vec in enumerate(self.reference_vectors)
            ],
            "iterations": [
                {
                    "iteration": r.iteration,
                    "phase": r.phase,
                    "composite_front": r.composite_front,
                    "preference_information": r.preference_information,
                    "hypervolume": r.hypervolume_by_method,
                    "reference_vector_assignments": r.reference_vector_assignments,
                    "max_assigned_vector": r.max_assigned_vector,
                }
                for r in self.iteration_records
            ],
            "phi_summary": {
                "learning_phase": {"total": phi_learn_total, "std": phi_learn_std},
                "decision_phase": {"total": phi_dec_total, "std": phi_dec_std},
            },
        }


def run_experiment_suite(problems, methods, learning_iters, decision_iters, gens_per_iter, seed, adm_name="afsar"):
    """Runs the full experiment across a list of problems and returns a list of result dicts."""
    all_results = []
    for problem in problems:
        pipeline = ExperimentPipeline(
            problem=problem,
            methods=methods,
            learning_iterations=learning_iters,
            decision_iterations=decision_iters,
            generations_per_iteration=gens_per_iter,
            seed=seed,
            adm_name=adm_name,
        )
        all_results.append(pipeline.run())
    return all_results


def main():
    from desdeo.problem.testproblems import dtlz2
    out = Path("output")
    out.mkdir(exist_ok=True)
    problems = [dtlz2(n_objectives=5, n_variables=12)]
    data = run_experiment_suite(
        problems=problems,
        methods=["iRVEA", "iNSGA-III"],
        learning_iters=4,
        decision_iters=3,
        gens_per_iter=10,
        seed=123,
        adm_name="afsar",
    )
    path = out / "adm_phi_log.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()