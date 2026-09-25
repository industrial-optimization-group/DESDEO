/* Types specific to the JINA combined multi-scenario interactive method.
 *
 * Defined locally rather than re-exported from `$lib/gen/endpoints/DESDEOFastAPI` for the same
 * reason as the sibling multi-scenario and pool-matching methods (see their `types.ts`): the
 * generated response types trigger a TypeScript narrowing quirk under optional chaining, which
 * collapses a `$state`-held response to `never` and takes every callback parameter derived from
 * it down to an implicit `any`. These interfaces are structurally identical to the backend's
 * Pydantic response models (desdeo/api/models/district_heating_combined.py).
 *
 * Generic: this method works with any problem that has an attached scenario model, not just
 * district heating — every label, scenario name and range comes from the backend.
 */

/** One (objective, scenario) pair the decision maker sets an aspiration level for. */
export interface CombinedCell {
	symbol: string;
	obj_symbol: string;
	/** Empty for a shared objective, which takes the same value in every scenario. */
	scenario: string;
	shared: boolean;
	label: string;
	unit?: string | null;
	maximize: boolean;
	/** Best value reachable for this objective in this scenario alone. */
	ideal: number;
	/** Worst value in that scenario's payoff table. */
	nadir: number;
	/** |nadir - ideal|, the ASF normalization applied to this cell. */
	weight: number;
}

export interface CombinedGrid {
	problem_id: number;
	problem_name: string;
	scenarios: string[];
	objectives: string[];
	objective_labels: { [key: string]: string };
	strategic_symbols: string[];
	strategic_labels: { [key: string]: string };
	strategic_units: { [key: string]: string };
	/** {symbol: short component name}, for compact table columns. */
	strategic_components: { [key: string]: string };
	/** Upper bound per strategic variable, null when unbounded. For a problem following the
	 *  district heating convention this is also the capacity that already exists, which is what
	 *  lets a design's decision be read as capacity added on top. */
	strategic_axis_max: { [key: string]: number | null };
	cells: CombinedCell[];
	/** How many scalarizer variants this problem has — the most distinct designs one round can
	 *  produce, and the maximum the DM should be able to ask for. */
	scalarizer_count: number;
	/** Display labels, in priority order (balanced first). */
	scalarizer_labels: string[];
}

export interface CombinedCellResult {
	symbol: string;
	aspiration: number;
	achieved: number;
	/** (achieved - aspiration) / weight — this cell's term in the ASF max. */
	scaled: number;
	/** True when the solution is limited by this cell. */
	binds: boolean;
}

/** The single design one iteration produces. One ASF solve per round means one design; a design
 *  that resurfaces later keeps its `solution_number` and is flagged as a `repeat`. */
export interface CombinedSolution {
	design_id: number;
	solution_number: number;
	/** Which scalarizer variants landed on this design, e.g. ['balanced', 'emphasize_obj4'].
	 *  More than one means the emphasis did not buy a different build. */
	matched_by: string[];
	repeat: boolean;
	alpha: number;
	all_reached: boolean;
	cell_results: CombinedCellResult[];
	strategic_values: { [key: string]: number };
	/** One row per scenario, keyed by base objective symbol. A shared objective's single value is
	 *  repeated into every row. */
	breakdown: { [key: string]: number | string }[];
}

/** State after an iteration — also what get_or_initialize returns, so the page renders one shape
 *  whether it just solved or is resuming a session. */
export interface CombinedResult {
	state_id: number;
	iteration_number: number;
	reference_point: { [key: string]: number };
	note?: string | null;
	/** The primary (balanced) design — the one the DM's own reference point produced. */
	solution?: CombinedSolution | null;
	/** Every design this round produced, balanced first, already trimmed to `max_solutions`. */
	solutions: CombinedSolution[];
	/** The cap the round used; null means every variant's design was returned. */
	max_solutions?: number | null;
	scalarizer_count: number;
	wish_list: number[];
	scenarios: string[];
	objectives: string[];
	objective_labels: { [key: string]: string };
	default_domain_thresholds: { [key: string]: number };
}

export interface CombinedSessionTreeEntry {
	state_id: number;
	iteration_number: number;
	note?: string | null;
	reference_point: { [key: string]: number };
	solution?: CombinedSolution | null;
	solutions: CombinedSolution[];
}

export interface CombinedWishlistResult {
	state_id: number;
	wish_list: number[];
}

/** Per design: how many scenarios meet each thresholded objective. An objective with no threshold
 *  comes back null rather than being counted as passing. */
export interface CombinedDomainRow {
	design_id: number;
	mean_domain_criterion: number;
	[key: string]: number | string | null;
}

export interface CombinedAnalysisResult {
	wish_list: number[];
	domain_criterion: CombinedDomainRow[];
	domain_thresholds: { [key: string]: number };
	/** Total scenarios, i.e. the maximum a count can reach. */
	scenario_count: number;
}

/* The iterate request body is declared here rather than imported from
 * `$lib/gen/endpoints/DESDEOFastAPI`: the generated client is only as current as the last
 * `npm run generate:client` against a live backend, and it predates `max_solutions`. Same
 * reasoning as the response interfaces above. */
export interface CombinedIterateBody {
	problem_id: number;
	session_id?: number | null;
	reference_point: { [key: string]: number };
	/** Cap on designs returned this round. Every variant still solves; this trims what is shown,
	 *  so nothing is lost from the design list or wish list. */
	max_solutions?: number | null;
	note?: string | null;
}

/** Distinct colors per solution, matching the multi-scenario method's palette so a DM moving
 *  between the two methods reads the same colors the same way. */
export const SOLUTION_COLORS = [
	// The original eight, unchanged and in order: a design's colour comes from its position here,
	// so reordering or inserting would repaint every design a decision maker has already seen.
	'#08519c',
	'#238b45',
	'#e08214',
	'#762a83',
	'#d73027',
	'#1a1a1a',
	'#0bb99c',
	'#b930d8',
	// Twelve more, appended so a ninth and tenth design no longer wrap around to the first two.
	// Chosen by greedy maximum-minimum separation in CIELAB against everything already in the
	// list, restricted to L* 22-72 so each one reads as a thin line on white without being so
	// dark it reads as the black entry. Worst pair across all twenty is deltaE 26, against 30 for
	// the original eight alone.
	'#c49c94',
	'#e7298a',
	'#543005',
	'#01665e',
	'#66a61e',
	'#e377c2',
	'#8e0152',
	'#a65628',
	'#666666',
	'#7f0000',
	'#17becf',
	'#00441b'
];
