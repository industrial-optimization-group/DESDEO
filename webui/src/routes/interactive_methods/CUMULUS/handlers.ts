/**
 * CUMULUS API Client-Side Handlers
 */

import {
	solveSolutionsMethodCumulusSolvePost,
	getOrInitializeMethodCumulusGetOrInitializePost,
	saveMethodCumulusSavePost,
	deleteSaveMethodCumulusDeleteSavePost,
	finalizeMethodCumulusFinalizePost,
	solveIntermediateMethodCumulusIntermediatePost,
	getUtopiaDataUtopiaPost,
	setObjectiveConstraintsMethodCumulusObjectiveConstraintPost,
	modifyProblemMethodCumulusModifyProblemPost,
	modifyProblemStatusMethodCumulusModifyProblemStatusStateIdGet,
	getSolutionDescriptionSolutionDescriptionGetPost,
	getScenarioAvailabilityMethodCumulusScenarioAvailabilityGet,
	applyScenarioMeasuresMethodCumulusApplyScenarioMeasuresPost
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type {
	CumulusClassificationRequest,
	CumulusInitializationRequest,
	CumulusSaveRequest,
	CumulusDeleteSaveRequest,
	CumulusFinalizeRequest,
	IntermediateSolutionRequest,
	SolutionInfo,
	CumulusObjectiveConstraintRequest,
	CumulusModificationRequest,
	CumulusModificationResponse,
	CumulusScenarioAvailabilityResponse,
	SolutionDescriptionRequest,
	ConstraintTypeEnum,
	ProblemInfo,
	SolutionReferenceResponse as Solution,
	ReferencePoint
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type { Response } from './types';
import { errorMessage, isLoading } from '../../../stores/uiState';

/** Convert a Solution to a SolutionInfo for API requests. */
function toSolutionInfo(solution: Solution, name?: string | null): SolutionInfo {
	return {
		state_id: solution.state_id,
		solution_index: solution.solution_index ?? 0,
		name: name ?? solution.name
	};
}

/**
 * Handles the generation of intermediate solutions between two selected reference solutions.
 */
export async function handle_intermediate(
	problem: ProblemInfo | null,
	selected_solutions: Solution[],
	num_desired: number
): Promise<Response | null> {
	if (!problem) {
		errorMessage.set('No problem selected');
		return null;
	}
	if (selected_solutions.length !== 2) {
		errorMessage.set('Exactly 2 solutions must be selected for intermediate solutions');
		return null;
	}

	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: IntermediateSolutionRequest = {
			problem_id: problem.id,
			reference_solution_1: toSolutionInfo(selected_solutions[0]),
			reference_solution_2: toSolutionInfo(selected_solutions[1]),
			num_desired: num_desired
		};

		const response = await solveIntermediateMethodCumulusIntermediatePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Intermediate solutions failed with status ${response.status}`);
			return null;
		}

		return response.data as unknown as Response;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in handle_intermediate:', msg);
		return null;
	} finally {
		isLoading.set(false);
	}
}

/**
 * Handles a CUMULUS iteration based on user-defined reference point preferences.
 */
export async function handle_iterate(
	problem: ProblemInfo,
	current_preference: number[],
	selected_iteration_objectives: Record<string, number>,
	_current_num_iteration_solutions: number,
	scalarizations: string[] = ['cumulonimbus']
): Promise<Response | null> {
	isLoading.set(true);
	errorMessage.set(null);

	try {
		const preference: ReferencePoint = {
			preference_type: 'reference_point',
			aspiration_levels: problem.objectives.reduce(
				(acc, obj, idx) => {
					acc[obj.symbol] = current_preference[idx];
					return acc;
				},
				{} as Record<string, number>
			)
		};

		const request: CumulusClassificationRequest = {
			problem_id: problem.id,
			current_objectives: selected_iteration_objectives,
			preference: preference,
			scalarizations: scalarizations
		};

		const response = await solveSolutionsMethodCumulusSolvePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Iteration failed with status ${response.status}`);
			return null;
		}

		return response.data as unknown as Response;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in handle_iterate:', msg);
		return null;
	} finally {
		isLoading.set(false);
	}
}

/**
 * Saves a solution with an optional user-provided name.
 */
export async function handle_save(
	problem: ProblemInfo | null,
	solution: Solution,
	name: string | undefined
): Promise<boolean> {
	if (!problem) {
		errorMessage.set('No problem selected');
		return false;
	}

	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: CumulusSaveRequest = {
			problem_id: problem.id,
			solution_info: [toSolutionInfo(solution, name ?? null)]
		};

		const response = await saveMethodCumulusSavePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Save failed with status ${response.status}`);
			return false;
		}

		return true;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in handle_save:', msg);
		return false;
	} finally {
		isLoading.set(false);
	}
}

/**
 * Removes a previously saved solution.
 */
export async function handle_remove_saved(
	problem: ProblemInfo | null,
	solution: Solution
): Promise<boolean> {
	if (!problem) {
		errorMessage.set('No problem selected');
		return false;
	}

	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: CumulusDeleteSaveRequest = {
			state_id: solution.state_id,
			solution_index: solution.solution_index ?? 0,
			problem_id: problem.id
		};

		const response = await deleteSaveMethodCumulusDeleteSavePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Delete save failed with status ${response.status}`);
			return false;
		}

		return true;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in handle_remove_saved:', msg);
		return false;
	} finally {
		isLoading.set(false);
	}
}

/**
 * Marks a solution as the final chosen solution for the session.
 */
export async function handle_finish(
	problem: ProblemInfo | null,
	solution: Solution,
	_preferences: ReferencePoint
): Promise<boolean> {
	if (!problem) {
		errorMessage.set('No problem selected');
		return false;
	}

	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: CumulusFinalizeRequest = {
			problem_id: problem.id,
			solution_info: toSolutionInfo(solution)
		};

		const response = await finalizeMethodCumulusFinalizePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Finalize failed with status ${response.status}`);
			return false;
		}

		return true;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in handle_finish:', msg);
		return false;
	} finally {
		isLoading.set(false);
	}
}

/**
 * Fetches map data related to a specific solution for UTOPIA visualization.
 */
export async function get_maps(
	problem: ProblemInfo,
	solution: Solution
): Promise<{
	years: string[];
	options: Record<string, any>;
	map_json: object;
	map_name: string;
	description: string;
	compensation: number;
} | null> {
	isLoading.set(true);
	errorMessage.set(null);

	try {
		const response = await getUtopiaDataUtopiaPost({
			problem_id: problem.id,
			solution: toSolutionInfo(solution)
		});

		if (response.status !== 200) {
			errorMessage.set(`Get maps failed with status ${response.status}`);
			return null;
		}

		const result = response.data as any;

		if (result) {
			for (const year of result.years) {
				if (result.options[year].tooltip.formatterEnabled) {
					result.options[year].tooltip.formatter = function (params: any) {
						return `${params.name}`;
					};
				}
			}
		}

		return result;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in get_maps:', msg);
		return null;
	} finally {
		isLoading.set(false);
	}
}

/**
 * Fetches a textual solution description from the solution_description endpoint.
 */
export async function get_solution_description(
	problem: ProblemInfo,
	solution: Solution
): Promise<string | null> {
	try {
		const request: SolutionDescriptionRequest = {
			problem_id: problem.id,
			solution: toSolutionInfo(solution)
		};
		const response = await getSolutionDescriptionSolutionDescriptionGetPost(request);

		if (response.status !== 200 || !response.data.available) return null;
		return response.data.description;
	} catch {
		return null;
	}
}

/**
 * Initializes a new CUMULUS state for a given problem, or retrieves the latest one.
 *
 * Pass `skip_scenarios = true` to bypass scenario detection and force plain initialization
 * (used when the DM declines to build a combined scenario problem).
 */
export async function initialize_cumulus_state(
	problem_id: number,
	skip_scenarios = false
): Promise<Response | null> {
	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: CumulusInitializationRequest = {
			problem_id: problem_id,
			// An empty array signals "skip scenario detection"; null triggers it.
			uncertainty_measures: skip_scenarios ? [] : null
		};

		const response = await getOrInitializeMethodCumulusGetOrInitializePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Initialization failed with status ${response.status}`);
			return null;
		}

		return response.data as unknown as Response;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in initialize_cumulus_state:', msg);
		return null;
	} finally {
		isLoading.set(false);
	}
}

export type MeasureType =
	| 'expected_value'
	| 'worst_case_robust'
	| 'conditional_value_at_risk'
	| 'weighted_scenarios';

export interface MeasureOptions {
	cvar_alpha?: number;
}

function build_uncertainty_measures_request(
	problem_id: number,
	scenario_model_id: number,
	objective_symbols: string[],
	selected_measures: MeasureType[],
	measure_options: MeasureOptions,
	name?: string
): CumulusInitializationRequest {
	return {
		problem_id: problem_id,
		name: name || null,
		uncertainty_measures: selected_measures.map((measure_type) => ({
			measure_type,
			scenario_model_id,
			symbols: objective_symbols,
			...(measure_type === 'conditional_value_at_risk' && {
				alpha: measure_options.cvar_alpha ?? 0.95
			})
		}))
	};
}

/**
 * Re-calls get-or-initialize with the DM-chosen uncertainty measures applied,
 * building a combined multi-scenario problem before starting the method.
 */
export async function initialize_cumulus_state_with_scenarios(
	problem_id: number,
	scenario_model_id: number,
	objective_symbols: string[],
	selected_measures: MeasureType[],
	measure_options: MeasureOptions = {},
	name?: string
): Promise<Response | null> {
	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request = build_uncertainty_measures_request(
			problem_id,
			scenario_model_id,
			objective_symbols,
			selected_measures,
			measure_options,
			name
		);

		const response = await getOrInitializeMethodCumulusGetOrInitializePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Scenario initialization failed with status ${response.status}`);
			return null;
		}

		return response.data as unknown as Response;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in initialize_cumulus_state_with_scenarios:', msg);
		return null;
	} finally {
		isLoading.set(false);
	}
}

/**
 * Checks whether a problem (or the base problem it was combined from) has an associated
 * scenario model, so the "Add uncertainty measures" action can be shown or hidden accordingly.
 */
export async function check_scenario_availability(
	problem_id: number
): Promise<CumulusScenarioAvailabilityResponse | null> {
	try {
		const response = await getScenarioAvailabilityMethodCumulusScenarioAvailabilityGet({
			problem_id
		});

		if (response.status !== 200) {
			return null;
		}

		return response.data as unknown as CumulusScenarioAvailabilityResponse;
	} catch (error) {
		console.error(
			'Error in check_scenario_availability:',
			error instanceof Error ? error.message : error
		);
		return null;
	}
}

/**
 * Builds (or rebuilds) a combined scenario problem with the given uncertainty measures,
 * regardless of whether CUMULUS has already been initialized for the current problem.
 * Used by the "Add uncertainty measures" menu action, which can be used both before the
 * method has started and later, to change which measures are included.
 */
export async function apply_scenario_measures(
	problem_id: number,
	scenario_model_id: number,
	objective_symbols: string[],
	selected_measures: MeasureType[],
	measure_options: MeasureOptions = {},
	name?: string
): Promise<Response | null> {
	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request = build_uncertainty_measures_request(
			problem_id,
			scenario_model_id,
			objective_symbols,
			selected_measures,
			measure_options,
			name
		);

		const response = await applyScenarioMeasuresMethodCumulusApplyScenarioMeasuresPost(request);

		if (response.status !== 200) {
			errorMessage.set(`Applying uncertainty measures failed with status ${response.status}`);
			return null;
		}

		return response.data as unknown as Response;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in apply_scenario_measures:', msg);
		return null;
	} finally {
		isLoading.set(false);
	}
}

type UIConstraintType = '<=0' | '=0' | '<=0 (soft)' | '=0 (soft)';

interface UIConstraint {
	func: string;
	type: UIConstraintType;
}

export interface ObjectiveConstraintResult {
	/** The objective-constraint state holding the soft list now in effect. */
	state_id: number;
	hard_constraint_ids: number[];
	soft_constraint_ids: number[];
	/**
	 * Set when hard bounds rebuilt the problem. Solving and the solution archive are scoped by
	 * problem id, so the session has to switch to this problem; the old one stays intact.
	 */
	new_problem_id: number | null;
	/**
	 * True when the rebuilt problem excludes the solution the decision maker was on, so the
	 * method cannot continue from it and restarts from a fresh starting point.
	 */
	current_solution_excluded: boolean;
}

/** Objective constraints are named `oc_1`, `oc_2`, … */
const OBJECTIVE_CONSTRAINT_SYMBOL = /^oc_(\d+)$/;

/** Poll cadence and give-up point for the background modify-problem checks. */
const MODIFICATION_POLL_INTERVAL_MS = 1000;
const MODIFICATION_POLL_TIMEOUT_MS = 10 * 60 * 1000;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** FastAPI reports an HTTPException as a plain string detail, validation errors as a list. */
function errorDetail(data: unknown): string | null {
	const detail = (data as { detail?: unknown } | null)?.detail;
	return typeof detail === 'string' ? detail : null;
}

/**
 * First unused `oc_` index in `problem`.
 *
 * Hard bounds become real constraints of the rebuilt problem, and /modify-problem replaces any
 * element whose symbol already exists. Numbering past what the problem already carries is what
 * keeps a second hard bound from silently overwriting the first.
 */
function nextConstraintIndex(problem: ProblemInfo): number {
	let highest = 0;
	for (const constraint of problem.constraints ?? []) {
		const match = OBJECTIVE_CONSTRAINT_SYMBOL.exec(constraint.symbol);
		if (match) highest = Math.max(highest, Number(match[1]));
	}
	return highest + 1;
}

function toConstraintDB(constraints: UIConstraint[], soft: boolean, first_index: number) {
	return constraints
		.filter((c) => c.type.includes('soft') === soft)
		.map((c, i) => ({
			name: c.func,
			symbol: `oc_${first_index + i}`,
			func: c.func,
			cons_type: (c.type.startsWith('<=') ? '<=' : '=') as ConstraintTypeEnum
		}));
}

const DISCARDED_MESSAGE =
	'The bounded problem could not be used and was discarded. No constraints were applied.';

export type ModificationOutcome =
	/** The background checks passed and the modified problem is ready to be used. */
	| { kind: 'accepted'; response: CumulusModificationResponse }
	/** The bounds were refused and the modified problem discarded. */
	| { kind: 'rejected'; reason: string }
	/** Neither could be established: polling itself failed or ran out of time. */
	| { kind: 'failed' };

/**
 * Polls /modify-problem/status until the background feasibility check settles.
 *
 * `is_ready` only means the check has finished, so a ready response still has to be read for
 * the verdict — hence the three outcomes rather than a bare response.
 */
export async function poll_modification_status(
	state_id: number,
	{
		interval_ms = MODIFICATION_POLL_INTERVAL_MS,
		timeout_ms = MODIFICATION_POLL_TIMEOUT_MS
	}: { interval_ms?: number; timeout_ms?: number } = {}
): Promise<ModificationOutcome> {
	const deadline = Date.now() + timeout_ms;

	for (;;) {
		const response = await modifyProblemStatusMethodCumulusModifyProblemStatusStateIdGet(state_id);

		// The generated union only knows the documented statuses, but 404 is reachable — see
		// below. Widening is confined to this check so that `response.status` still narrows
		// `response.data` afterwards.
		if ((response.status as number) === 404) {
			// Discarding an infeasible modification deletes the problem it created, and the state
			// meant to report that outcome belongs to that problem, so it is deleted along with
			// it. A state that has gone missing since the request is therefore the rejection,
			// reported without the detail the deleted row was carrying.
			return { kind: 'rejected', reason: DISCARDED_MESSAGE };
		}

		if (response.status !== 200) {
			errorMessage.set(
				errorDetail(response.data) ??
					`Checking the modified problem failed with status ${response.status}`
			);
			return { kind: 'failed' };
		}

		if (response.data.is_ready) {
			if (response.data.problem_deleted || response.data.error) {
				return { kind: 'rejected', reason: response.data.error ?? DISCARDED_MESSAGE };
			}
			return { kind: 'accepted', response: response.data };
		}

		if (Date.now() >= deadline) {
			errorMessage.set(
				'Checking the modified problem is taking longer than expected. The constraints have ' +
					'not been applied to this session; try again in a moment.'
			);
			return { kind: 'failed' };
		}

		await sleep(interval_ms);
	}
}

interface HardConstraintOutcome {
	/** The modification state that the new problem's later states hang off. */
	state_id: number;
	/** The problem the bounds produced. */
	problem_id: number;
	/** The bounds exclude the solution the decision maker was on. */
	current_solution_excluded: boolean;
}

/**
 * Applies hard objective bounds through /modify-problem and waits for the background checks.
 *
 * The endpoint returns as soon as it has built the new problem and settles feasibility
 * afterwards, so its immediate response says nothing about whether the bounds hold — but it is
 * where the identifiers and the (synchronously decided) current-solution verdict come from. The
 * poll only decides whether the modification is accepted. A rejected one deletes the problem it
 * created server-side, leaving the decision maker on the one they were already using.
 */
async function apply_hard_constraints(
	problem: ProblemInfo,
	parent_state_id: number | null,
	hard: ReturnType<typeof toConstraintDB>,
	on_progress: (message: string) => void
): Promise<HardConstraintOutcome | null> {
	const request: CumulusModificationRequest = {
		problem_id: problem.id,
		parent_state_id: parent_state_id ?? null,
		modifications: { constraints: hard }
	};

	const response = await modifyProblemMethodCumulusModifyProblemPost(request);

	if (response.status !== 200) {
		errorMessage.set(
			errorDetail(response.data) ??
				`Applying hard objective constraints failed with status ${response.status}`
		);
		return null;
	}

	// Whether the current solution survives the bounds is known without solving, so it can be
	// reported while the more expensive feasibility check is still running.
	on_progress(
		response.data.current_solution_feasible === false
			? 'The solution you are on is outside the new bounds. Checking whether the bounded ' +
					'problem has any solutions at all…'
			: 'Checking that the bounded problem still has solutions…'
	);

	const outcome = await poll_modification_status(response.data.state_id);

	if (outcome.kind !== 'accepted') {
		if (outcome.kind === 'rejected') errorMessage.set(outcome.reason);
		return null;
	}

	return {
		state_id: response.data.state_id,
		problem_id: response.data.problem_id,
		current_solution_excluded: response.data.current_solution_feasible === false
	};
}

/**
 * Applies the decision maker's objective constraint list.
 *
 * The two kinds take different routes: soft constraints are stored alongside the current
 * problem, while hard bounds rebuild it into a new problem through /modify-problem. Hard ones
 * go first, because the soft list has to be stored against whichever problem ends up in effect
 * — storing it first would attach it to a problem a rejected bound then leaves behind. A
 * rejected bound therefore applies nothing at all.
 */
export async function set_objective_constraints(
	problem: ProblemInfo,
	parent_state_id: number | null,
	constraints: UIConstraint[],
	on_progress: (message: string) => void = () => {}
): Promise<ObjectiveConstraintResult | null> {
	isLoading.set(true);
	errorMessage.set(null);

	// Symbols continue past the problem's existing objective constraints so that neither the
	// hard bounds nor the soft list collide with what is already there.
	const first_index = nextConstraintIndex(problem);
	const hard = toConstraintDB(constraints, false, first_index);
	const soft = toConstraintDB(constraints, true, first_index + hard.length);

	try {
		let target_problem_id = problem.id;
		let target_parent_state_id = parent_state_id;
		let new_problem_id: number | null = null;
		let current_solution_excluded = false;

		if (hard.length > 0) {
			const modification = await apply_hard_constraints(
				problem,
				parent_state_id,
				hard,
				on_progress
			);
			if (modification === null) return null;

			new_problem_id = modification.problem_id;
			target_problem_id = modification.problem_id;
			target_parent_state_id = modification.state_id;
			current_solution_excluded = modification.current_solution_excluded;

			on_progress('Applying soft constraints…');
		}

		// Sent even when empty: the endpoint replaces the stored list, which is how the decision
		// maker clears soft constraints they have removed from the dialog.
		const request: CumulusObjectiveConstraintRequest = {
			problem_id: target_problem_id,
			parent_state_id: target_parent_state_id ?? null,
			hard_constraints: [],
			soft_constraints: soft
		};

		const response = await setObjectiveConstraintsMethodCumulusObjectiveConstraintPost(request);

		if (response.status !== 200) {
			const reason =
				errorDetail(response.data) ??
				`Setting objective constraints failed with status ${response.status}`;
			// The bounded problem was built and kept, but without the soft list it is not what the
			// decision maker asked for. Staying on the current problem leaves them somewhere
			// coherent, and the bounded problem remains selectable later.
			errorMessage.set(
				new_problem_id === null
					? reason
					: `${reason} The hard bounds produced a new problem, but this session stayed on the ` +
							'current one because the soft constraints could not be applied to it.'
			);
			return null;
		}

		return {
			state_id: response.data.state_id,
			hard_constraint_ids: response.data.hard_constraint_ids,
			soft_constraint_ids: response.data.soft_constraint_ids,
			new_problem_id,
			current_solution_excluded
		};
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in set_objective_constraints:', msg);
		return null;
	} finally {
		isLoading.set(false);
	}
}
