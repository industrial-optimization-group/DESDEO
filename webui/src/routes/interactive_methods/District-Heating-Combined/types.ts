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
	cells: CombinedCell[];
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
	solution?: CombinedSolution | null;
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

/** Distinct colors per solution, matching the multi-scenario method's palette so a DM moving
 *  between the two methods reads the same colors the same way. */
export const SOLUTION_COLORS = [
	'#08519c',
	'#238b45',
	'#e08214',
	'#762a83',
	'#d73027',
	'#1a1a1a',
	'#0bb99c',
	'#b930d8'
];
