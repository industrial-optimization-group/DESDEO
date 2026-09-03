/* Types specific to the JINA single-scenario pool-matching interactive method.
 *
 * Defined locally rather than re-exported from `$lib/gen/endpoints/DESDEOFastAPI` for the same
 * reason as the sibling multi-scenario method (see its `types.ts`): the generated response types
 * trigger a TypeScript narrowing quirk under optional chaining. These interfaces are structurally
 * identical to the backend's Pydantic response models (desdeo/api/models/district_heating_system.py).
 *
 * Generic: this method works with any problem that has an attached pool-matching metadata row,
 * not just district heating — objective/strategic-variable/scalarizer labels all come from
 * `ProblemMeta` (fetched from the backend), not from hard-coded constants.
 */

export type ObjectiveValues = { [key: string]: number };

export interface ObjectiveMeta {
	symbol: string;
	name: string;
	unit?: string | null;
	label: string;
	maximize: boolean;
	varies_by_scenario: boolean;
}

export interface StrategicVarMeta {
	symbol: string;
	name: string;
	label: string;
	component: string;
	unit?: string | null;
	axis_max?: number | null;
}

export interface ScalarizerMeta {
	name: string;
	emphasize?: string | null;
	label: string;
}

export interface ProblemMeta {
	problem_id: number;
	problem_name: string;
	scenario_model_id?: number | null;
	objectives: ObjectiveMeta[];
	strategic_vars: StrategicVarMeta[];
	scalarizers: ScalarizerMeta[];
	all_scenarios: string[];
	default_domain_thresholds: ObjectiveValues;
	default_af_absolute_floors: ObjectiveValues;
	supports_compound_scenarios: boolean;
	compound_description?: string | null;
	lambda_objective?: string | null;
}

export interface MatchedSolution {
	design_id: number;
	solution_number: number;
	matched_by: string[];
	n_scenarios: number;
	rows: { target_operation_scenario: string; [key: string]: unknown }[];
	worst_case: ObjectiveValues;
	best_case: ObjectiveValues;
}

export interface StrategicDesign {
	design_id: number;
	source_design_scenario: string;
	reference_id: number;
	scalarizer: string;
	strategic_vals: ObjectiveValues;
	breakdown: { scenario: string; [key: string]: unknown }[];
}

export interface StrategicDesignsResult {
	designs: StrategicDesign[];
	axis_max: { [key: string]: number | null };
}

// Scalarizers are always emitted "aasf" (balanced) first, then one "generic_asf" emphasis
// variant per objective in objective order, then GUESS/STOM — so a fixed palette indexed by
// position gives every problem stable, distinct colors with zero per-problem configuration.
export const SCALARIZER_PALETTE = ['#326dad', '#d45353', '#639922', '#ba7517', '#7f77dd', '#0bb99c', '#b930d8'];

// Strategic Design Explorer colors designs by which scenario they were originally optimized for
// (meaningful here, unlike the sibling Robust method, where every design is solved jointly
// across all scenarios at once) — same position-indexed-palette approach as scalarizers.
export const SCENARIO_PALETTE = [
	'#326dad',
	'#b930d8',
	'#241d9e',
	'#ba7517',
	'#7f77dd',
	'#d45353',
	'#639922',
	'#0bb99c'
];

export interface IterateState {
	state_id: number;
	reference_point: ObjectiveValues;
	note?: string | null;
	solutions: MatchedSolution[];
	wish_list: number[];
	already_shown_ids: number[];
	global_ideal: ObjectiveValues;
	global_nadir: ObjectiveValues;
	all_scenarios: string[];
	meta: ProblemMeta;
}

export interface WishlistState {
	state_id: number;
	wish_list: number[];
	skipped_ids?: number[];
}

/** One row per design: max regret per objective (0-1, normalized) plus the mean. */
export interface MaxRegretRow {
	design_id: number;
	mean_normalized_regret: number;
	[key: string]: unknown;
}

/** One row per design: count of scenarios meeting the domain-criterion threshold, per objective. */
export interface DomainCriterionRow {
	design_id: number;
	mean_domain_criterion: number;
	[key: string]: unknown;
}

/** One row per design: antifragility U/D/AF per objective, raw units, and Taleb class. */
export interface AntifragilitySummaryRow {
	design_id: number;
	[key: string]: unknown;
}

/** One row per design x objective x disrupted scenario. */
export interface AntifragilityDeviationRow {
	design_id: number;
	objective: string;
	target_operation_scenario: string;
	d: number;
	d_raw: number;
	value: number;
	event_class?: 'fragile' | 'bounded_loss' | 'untouched' | 'gain';
}

/** One node (iteration or wish-list update) in a session's history, oldest first. */
export interface SessionTreeEntry {
	state_id: number;
	kind: 'iterate' | 'wishlist_update';
	parent_id?: number | null;
	reference_point?: ObjectiveValues | null;
	note?: string | null;
	solutions?: MatchedSolution[] | null;
	wish_list?: number[] | null;
}

export interface AnalysisResult {
	wish_list: number[];
	max_regret: MaxRegretRow[];
	domain_criterion: DomainCriterionRow[];
	antifragility_summary: AntifragilitySummaryRow[];
	antifragility_deviations: AntifragilityDeviationRow[];
	af_objectives: string[];
	baseline_scenario: string;
	domain_thresholds: ObjectiveValues;
	af_absolute_floors: ObjectiveValues;
}

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
