/**
 * NIMBUS API Client-Side Handlers
 *
 * Uses Orval-generated endpoint functions to call the backend directly,
 * replacing the previous +server.ts proxy + callNimbusAPI pattern.
 */
import {
	saveMethodNimbusSavePost,
	deleteSaveMethodNimbusDeleteSavePost,
	finalizeNimbusMethodNimbusFinalizePost,
	solveSolutionsMethodRpmSolvePost
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
import type { Response, ReferencePoint, FinishResponse } from './types';
import { errorMessage, isLoading } from '../../../stores/uiState';
import { addProblemProblemAddPostBodyOnePreferencePreferenceTypeDefault } from '$lib/gen/endpoints/DESDEOFastAPIzod';

/** Convert a Solution (SolutionReferenceResponse) to a SolutionInfo for API requests. */
function toSolutionInfo(solution: Solution, name?: string | null): SolutionInfo {
	return {
		state_id: solution.state_id,
		solution_index: solution.solution_index ?? 0,
		name: name ?? solution.name
	};
}

/**
 * Handles a NIMBUS iteration based on user-defined preferences and classifications.
 */
export async function handle_iterate(
	problem: ProblemInfo,
	session_id: number | null,
	parent_state_id: number | null,
	preference: ReferencePoint
): Promise<Response | null> {
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
 * Initializes a new RPM state for a given problem, or retrieves the latest one.
 */
export async function initialize_rpm_state(problem: ProblemInfo, session_id: number | null, parent_state_id: number | null, preference: ReferencePoint): Promise<Response | null> {
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

		return response.data as unknown as Response;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in initialize_rpm_state:', msg);
		return null;
	} finally {
		isLoading.set(false);
	}
}
