/**
 * Preference Point API Client-Side Handlers
 *
 * Uses Orval-generated endpoint functions to call the backend directly.
 */
import {
	saveMethodNimbusSavePost,
	deleteSaveMethodNimbusDeleteSavePost,
	finalizeNimbusMethodNimbusFinalizePost,
	solveSolutionsMethodRpmSolvePost,
	getUtopiaDataUtopiaPost,
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type {
	NIMBUSSaveRequest,
	NIMBUSDeleteSaveRequest,
	NIMBUSFinalizeRequest,
	SolutionInfo,
	RPMSolveRequest,
	RPMState,
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type { ProblemInfo, Solution } from '$lib/types';
import type { ReferencePoint } from './types';
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
			console.error('Reference Point Method save failed:', response.status);
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
			console.error('Reference Point Method delete save failed:', response.status);
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
	preference: ReferencePoint,
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
 * Handles a Reference Point iteration based on user-defined preferences.
 */
export async function handle_iterate(
	problem: ProblemInfo,
	session_id: number | null,
	parent_state_id: number | null,
	preference: ReferencePoint
): Promise<RPMState | null> {
	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: RPMSolveRequest = {
			problem_id: problem.id,
			session_id: session_id,
			parent_state_id: parent_state_id ?? undefined,
			preference: preference,
		};

		const response = await solveSolutionsMethodRpmSolvePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Iteration failed with status ${response.status}`);
			console.error('RPM iterate failed:', response.status);
			return null;
		}

		return response.data;
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
 * Initializes a new RPM state for a given problem, or retrieves the latest one.
 */
export async function initialize_rpm_state(problem: ProblemInfo, session_id: number | null, parent_state_id: number | null, preference: ReferencePoint): Promise<RPMState | null> {
	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: RPMSolveRequest = {
			problem_id: problem.id,
			session_id: session_id,
			parent_state_id: parent_state_id ?? undefined,
			preference: preference,
		}

		const response = await solveSolutionsMethodRpmSolvePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Initialization failed with status ${response.status}`);
			console.error('RPM initialization failed:', response.status);
			return null;
		}

		return response.data;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in initialize_rpm_state:', msg);
		return null;
	} finally {
		isLoading.set(false);
	}
}

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
