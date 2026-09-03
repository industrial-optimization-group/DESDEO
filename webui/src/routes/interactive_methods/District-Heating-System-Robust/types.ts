/* Types specific to the JINA multi-scenario interactive method.
 *
 * Defined locally rather than re-exported from `$lib/gen/endpoints/DESDEOFastAPI` for the same
 * reason as the sibling pool-matching method (see its `types.ts`): the generated response types
 * trigger a TypeScript narrowing quirk under optional chaining. These interfaces are structurally
 * identical to the backend's Pydantic response models (desdeo/api/models/district_heating_robust.py).
 *
 * Generic: this method works with any problem that has an attached scenario model, not just
 * district heating — objective/strategic-variable/scalarizer labels all come from `ProblemMeta`
 * (fetched from the backend), not from hard-coded constants.
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
	scenario_model_id: number;
	objectives: ObjectiveMeta[];
	strategic_vars: StrategicVarMeta[];
	scalarizers: ScalarizerMeta[];
	all_scenarios: string[];
	default_domain_thresholds: ObjectiveValues;
	default_af_absolute_floors: ObjectiveValues;
	supports_compound_scenarios: boolean;
	compound_description?: string | null;
}

export interface MatchedSolution {
	design_id: number;
	solution_number: number;
	matched_by: string[];
	/** True if this design first appeared in an earlier iteration — it can resurface (not
	 * excludable, since every variant re-solves live), so it's flagged instead of hidden. */
	repeat: boolean;
	breakdown: { scenario: string; [key: string]: unknown }[];
	worst_case: ObjectiveValues;
	best_case: ObjectiveValues;
}

export interface StrategicDesign {
	design_id: number;
	solution_number: number;
	scalarizer: string;
	first_iteration?: number | null;
	strategic_vals: ObjectiveValues;
	robust_vals: ObjectiveValues;
	breakdown: { scenario: string; [key: string]: unknown }[];
}

export interface StrategicDesignsResult {
	designs: StrategicDesign[];
	axis_max: { [key: string]: number | null };
}

// Scalarizers are always emitted "balanced" first, then one "emphasize" variant per objective in
// objective order — so a fixed palette indexed by position gives every problem stable, distinct
// colors with zero per-problem configuration.
export const SCALARIZER_PALETTE = ['#326dad', '#d45353', '#639922', '#ba7517', '#7f77dd', '#0bb99c', '#b930d8'];

export interface CombinedScenarioRow {
	design_id: number;
	combined_scenario: string;
	status: string;
	[key: string]: unknown;
}

export interface CombinedScenarioSummaryRow {
	design_id: number;
	solution_number: number;
	[key: string]: unknown;
}

export interface CombinedScenarioResult {
	candidate_ids: number[];
	combo_names: string[];
	rows: CombinedScenarioRow[];
	summary: CombinedScenarioSummaryRow[];
	/** True when each row also carries `{obj}_superadd` — see the Super-additivity heatmap. */
	supports_superadditivity: boolean;
	/** One row per (design, reference scenario) — baseline + each single disruption alone. Same
	 * shape as `rows`, with `combined_scenario` holding the reference scenario's own name. Only
	 * populated when `supports_superadditivity` is true. */
	reference_rows: CombinedScenarioRow[];
	/** {combo_name: [reference_name_a, reference_name_b]} — resolves a chosen (A, B) pair to its
	 * combo name for the single-vs-combined comparison view. Null when unavailable. */
	pair_components: Record<string, [string, string]> | null;
}

export interface IterateState {
	state_id: number;
	iteration_number: number;
	reference_point: ObjectiveValues;
	note?: string | null;
	solutions: MatchedSolution[];
	wish_list: number[];
	global_ideal: ObjectiveValues;
	global_nadir: ObjectiveValues;
	all_scenarios: string[];
	meta: ProblemMeta;
}

export interface WishlistState {
	state_id: number;
	wish_list: number[];
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
	iteration_number?: number | null;
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
