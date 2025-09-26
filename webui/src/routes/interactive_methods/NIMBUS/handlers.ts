/**
 * NIMBUS API Client-Side Handlers
 *
 * @author Stina Palomäki <palomakistina@gmail.com>
 * @created August 2025
 *
 * @description
 * This file contains a set of handler functions responsible for preparing data and invoking
 * the `callNimbusAPI` function for various NIMBUS method operations. Each handler corresponds
 * to a specific user action in the NIMBUS UI, such as starting an iteration, saving a solution,
 * or generating intermediate points.
 *
 * These functions act as a bridge between the Svelte components and the generic API calling logic,
 * ensuring that the data sent to the backend proxy is correctly structured. They also perform
 * initial client-side validation, such as checking for the presence of a problem context.
 */
import type { ProblemInfo, Solution } from '$lib/types';
import type { Response } from './types';
import { callNimbusAPI } from './helper-functions';
import { errorMessage } from '../../../stores/uiState';

/**
 * Handles the generation of intermediate solutions between two selected reference solutions.
 * @param problem The active problem context.
 * @param selected_solutions An array containing the two solutions to generate intermediate points between.
 * @param num_desired The number of intermediate solutions to generate.
 * @returns A promise that resolves with the API response containing the new solutions, or null on failure.
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
	// Check if we have exactly 2 solutions selected
	if (selected_solutions.length !== 2) {
		errorMessage.set('Exactly 2 solutions must be selected for intermediate solutions');
		console.error('Exactly 2 solutions must be selected for intermediate solutions');
		return null;
	}

	const result = await callNimbusAPI<Response>('intermediate', {
		problem_id: problem.id,
		session_id: null, // Using active session
		parent_state_id: null, // No specific parent
		reference_solution_1: selected_solutions[0],
		reference_solution_2: selected_solutions[1],
		num_desired: num_desired
	});

	return result;
}

/**
 * Handles a NIMBUS iteration based on user-defined preferences and classifications.
 * @param problem The active problem context.
 * @param current_preference The user's specified reference point.
 * @param selected_iteration_objectives Objectives of the selected solution.
 * @param current_num_iteration_solutions The number of new solutions to generate.
 * @returns A promise that resolves with the API response containing the new solutions, or null on failure.
 */
export async function handle_iterate(
	problem: ProblemInfo,
	current_preference: number[],
	selected_iteration_objectives: Record<string, number>,
	current_num_iteration_solutions: number
): Promise<Response | null> {
	const preference = {
		preference_type: 'reference_point',
		aspiration_levels: problem.objectives.reduce(
			(acc, obj, idx) => {
				acc[obj.symbol] = current_preference[idx];
				return acc;
			},
			{} as Record<string, number>
		)
	};

	const result = await callNimbusAPI<Response>('iterate', {
		problem_id: problem.id,
		session_id: null,
		parent_state_id: null,
		current_objectives: selected_iteration_objectives,
		num_desired: current_num_iteration_solutions,
		preference: preference
	});

	return result;
}

/**
 * Saves a solution with an optional user-provided name.
 * @param problem The active problem context.
 * @param solution The solution to be saved.
 * @param name An optional name for the solution.
 * @returns A promise that resolves to true on success, or false on failure.
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

	// Create a copy of the solution with the name
	const solutionToSave = {
		...solution,
		name: name ?? null
	};

	interface SaveResponse {
		success: boolean;
	}

	const result = await callNimbusAPI<SaveResponse>('save', {
		problem_id: problem.id,
		solution_info: [solutionToSave]
	});

	return result !== null;
}

/**
 * Removes a previously saved solution.
 * @param problem The active problem context.
 * @param solution The saved solution to remove.
 * @returns A promise that resolves to true on success, or false on failure.
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

	interface RemoveResponse {
		success: boolean;
	}

	const result = await callNimbusAPI<RemoveResponse>('remove_saved', {
		problem_id: problem.id,
		solutions: [solution]
	});

	return result !== null;
}

/**
 * Marks a solution as the final chosen solution for the session.
 * @param problem The active problem context.
 * @param solution The final solution to be chosen.
 * @returns A promise that resolves to true on success, or false on failure.
 */
export async function handle_finish(
	problem: ProblemInfo | null,
	solution: Solution
): Promise<boolean> {
	if (!problem) {
		errorMessage.set('No problem selected');
		console.error('No problem selected');
		return false;
	}

	interface FinishResponse {
		success: boolean;
	}

	const result = await callNimbusAPI<FinishResponse>('choose', {
		problem_id: problem.id,
		solution: solution
	});

	return result !== null;
}

/**
 * Fetches map data related to a specific solution for UTOPIA visualization.
 * @param problem The active problem context.
 * @param solution The solution for which to fetch map data.
 * @returns A promise that resolves with the map data, or null on failure.
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
	interface MapsResponse {
		years: string[];
		options: Record<string, any>;
		map_json: object;
		map_name: string;
		description: string;
		compensation: number;
	}

	const result = await callNimbusAPI<MapsResponse>('get_maps', {
		problem_id: problem.id,
		solution: solution
	});

	if (result) {
		// Apply the formatter function client-side
		for (const year of result.years) {
			if (result.options[year].tooltip.formatterEnabled) {
				result.options[year].tooltip.formatter = function (params: any) {
					return `${params.name}`;
				};
			}
		}
	}
	return result;
}

/**
 * Initializes a new NIMBUS state for a given problem.
 * @param problem_id The ID of the problem to initialize.
 * @returns A promise that resolves with the initial state of the NIMBUS session, or null on failure.
 */
export async function initialize_nimbus_state(problem_id: number): Promise<Response | null> {
	const result = await callNimbusAPI<Response>('initialize', {
		problem_id: problem_id,
		session_id: null, // Use active session
		parent_state_id: null, // No parent for initialization
		solver: null // Use default solver
	});

	return result;
}
