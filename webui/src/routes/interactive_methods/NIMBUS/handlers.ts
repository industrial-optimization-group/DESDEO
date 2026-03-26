/**
 * NIMBUS API Client-Side Handlers
 *
 * Uses Orval-generated endpoint functions to call the backend directly,
 * replacing the previous +server.ts proxy + callNimbusAPI pattern.
 */
import {
	solveSolutionsMethodNimbusSolvePost,
	getOrInitializeMethodNimbusGetOrInitializePost,
	saveMethodNimbusSavePost,
	deleteSaveMethodNimbusDeleteSavePost,
	finalizeNimbusMethodNimbusFinalizePost,
	solveNimbusIntermediateMethodNimbusIntermediatePost,
	getUtopiaDataUtopiaPost
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type {
	NIMBUSClassificationRequest,
	NIMBUSInitializationRequest,
	NIMBUSSaveRequest,
	NIMBUSDeleteSaveRequest,
	NIMBUSFinalizeRequest,
	IntermediateSolutionRequest,
	SolutionInfo
} from '$lib/gen/models';
import type { ProblemInfo, Solution } from '$lib/types';
import type { Response, ReferencePoint, FinishResponse } from './types';
import { errorMessage, isLoading } from '../../../stores/uiState';

/** Convert a Solution (SolutionReferenceResponse) to a SolutionInfo for API requests. */
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
		console.error('No problem selected');
		return null;
	}
	if (selected_solutions.length !== 2) {
		errorMessage.set('Exactly 2 solutions must be selected for intermediate solutions');
		console.error('Exactly 2 solutions must be selected for intermediate solutions');
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

		const response = await solveNimbusIntermediateMethodNimbusIntermediatePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Intermediate solutions failed with status ${response.status}`);
			console.error('NIMBUS intermediate failed:', response.status);
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
 * Handles a NIMBUS iteration based on user-defined preferences and classifications.
 */
export async function handle_iterate(
	problem: ProblemInfo,
	current_preference: number[],
	selected_iteration_objectives: Record<string, number>,
	current_num_iteration_solutions: number
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

		const request: NIMBUSClassificationRequest = {
			problem_id: problem.id,
			current_objectives: selected_iteration_objectives,
			num_desired: current_num_iteration_solutions,
			preference: preference
		};

		const response = await solveSolutionsMethodNimbusSolvePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Iteration failed with status ${response.status}`);
			console.error('NIMBUS iterate failed:', response.status);
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
		console.error('No problem selected');
		return false;
	}

	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: NIMBUSSaveRequest = {
			problem_id: problem.id,
			solution_info: [toSolutionInfo(solution, name ?? null)]
		};

		const response = await saveMethodNimbusSavePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Save failed with status ${response.status}`);
			console.error('NIMBUS save failed:', response.status);
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
		console.error('No problem selected');
		return false;
	}

	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: NIMBUSDeleteSaveRequest = {
			state_id: solution.state_id,
			solution_index: solution.solution_index ?? 0,
			problem_id: problem.id
		};

		const response = await deleteSaveMethodNimbusDeleteSavePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Delete save failed with status ${response.status}`);
			console.error('NIMBUS delete save failed:', response.status);
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
	preferences: ReferencePoint
): Promise<boolean> {
	if (!problem) {
		errorMessage.set('No problem selected');
		console.error('No problem selected');
		return false;
	}

	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: NIMBUSFinalizeRequest = {
			problem_id: problem.id,
			solution_info: toSolutionInfo(solution)
		};

		const response = await finalizeNimbusMethodNimbusFinalizePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Finalize failed with status ${response.status}`);
			console.error('NIMBUS finalize failed:', response.status);
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
			console.error('NIMBUS get maps failed:', response.status);
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
 * Initializes a new NIMBUS state for a given problem, or retrieves the latest one.
 */
export async function initialize_nimbus_state(problem_id: number): Promise<Response | null> {
	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: NIMBUSInitializationRequest = {
			problem_id: problem_id
		};

		const response = await getOrInitializeMethodNimbusGetOrInitializePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Initialization failed with status ${response.status}`);
			console.error('NIMBUS initialization failed:', response.status);
			return null;
		}

		return response.data as unknown as Response;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in initialize_nimbus_state:', msg);
		return null;
	} finally {
		isLoading.set(false);
	}
}
