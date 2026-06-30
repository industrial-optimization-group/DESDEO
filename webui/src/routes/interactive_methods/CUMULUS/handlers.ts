/**
 * CUMULUS API Client-Side Handlers
 *
 * NOTE: The Orval-generated functions used here require running
 * `npm run generate:client` after the backend endpoints are available.
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
	getSolutionDescriptionSolutionDescriptionGetPost
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
		// uncertainty_measures will appear in the generated client after `npm run generate:client`.
		const request = {
			problem_id: problem_id,
			// An empty array signals "skip scenario detection"; null triggers it.
			uncertainty_measures: skip_scenarios ? [] : null
		} as CumulusInitializationRequest;

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

export type MeasureType = 'expected_value' | 'worst_case_robust' | 'conditional_value_at_risk' | 'weighted_scenarios';

export interface MeasureOptions {
	cvar_alpha?: number;
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
		const request = {
			problem_id: problem_id,
			name: name || null,
			uncertainty_measures: selected_measures.map((measure_type) => ({
				measure_type,
				scenario_model_id,
				symbols: objective_symbols,
				...(measure_type === 'conditional_value_at_risk' && { alpha: measure_options.cvar_alpha ?? 0.95 })
			}))
		} as CumulusInitializationRequest;

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

type UIConstraintType = '<=0' | '=0' | '<=0 (soft)' | '=0 (soft)';

interface UIConstraint {
	func: string;
	type: UIConstraintType;
}

interface ObjectiveConstraintResult {
	state_id: number;
	hard_constraint_ids: number[];
	soft_constraint_ids: number[];
}

function toConstraintDB(constraints: UIConstraint[], soft: boolean, offset: number) {
	return constraints
		.filter((c) => c.type.includes('soft') === soft)
		.map((c, i) => ({
			name: c.func,
			symbol: `oc_${offset + i + 1}`,
			func: c.func,
			cons_type: (c.type.startsWith('<=') ? '<=' : '=') as ConstraintTypeEnum
		}));
}

export async function set_objective_constraints(
	problem: ProblemInfo,
	parent_state_id: number | null,
	constraints: UIConstraint[]
): Promise<ObjectiveConstraintResult | null> {
	isLoading.set(true);
	errorMessage.set(null);

	const hard = toConstraintDB(constraints, false, 0);
	const soft = toConstraintDB(constraints, true, hard.length);

	const request: CumulusObjectiveConstraintRequest = {
		problem_id: problem.id,
		parent_state_id: parent_state_id ?? null,
		hard_constraints: hard,
		soft_constraints: soft
	};

	try {
		const response = await setObjectiveConstraintsMethodCumulusObjectiveConstraintPost(request);

		if (response.status !== 200) {
			const detail = (response.data as unknown as { detail?: string })?.detail;
			errorMessage.set(detail ?? `Setting objective constraints failed with status ${response.status}`);
			return null;
		}

		return response.data;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in set_objective_constraints:', msg);
		return null;
	} finally {
		isLoading.set(false);
	}
}
