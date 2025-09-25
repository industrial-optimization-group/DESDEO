/**
 * NIMBUS Helper Functions
 *
 * This file contains utility functions for the UI of NIMBUS interactive multiobjective optimization method.
 * These functions handle common operations like data transformation, validation, API calls, and
 * visualization data preparation.
 *
 * @author Stina <palomakistina@gmail.com>
 * @created August 2025
 */

import type { components } from '$lib/api/client-types';
import { errorMessage, isLoading } from '../../../stores/uiState';

// Type definitions for NIMBUS components
type ProblemInfo = components['schemas']['ProblemInfo'];
type Solution = components['schemas']['SolutionReferenceResponse'];

// Define the Response type needed for our helper functions
type NIMBUSClassificationResponse = components['schemas']['NIMBUSClassificationResponse'];
type NIMBUSInitializationResponse = components['schemas']['NIMBUSInitializationResponse'];
type Response = NIMBUSClassificationResponse | NIMBUSInitializationResponse;

/**
 * Checks if a problem has utopia metadata for map visualization
 * @param prob The problem to check
 * @returns boolean indicating if the problem has utopia metadata
 */
export function checkUtopiaMetadata(prob: ProblemInfo | null) {
	// Check if the problem and its metadata exist
	if (!prob || !prob.problem_metadata) {
		return false;
	}

	// Check if forest_metadata exists and is not empty
	return (
		prob.problem_metadata.forest_metadata !== null &&
		Array.isArray(prob.problem_metadata.forest_metadata) &&
		prob.problem_metadata.forest_metadata.length > 0
	);
}

/**
 * Maps solutions objective values to arrays suitable for visualization components
 * @param solutions Array of solutions with objective values
 * @param problem The problem containing objective definitions
 * @returns Array of arrays with objective values in the order defined by the problem
 */
export function mapSolutionsToObjectiveValues(solutions: Solution[], problem: ProblemInfo) {
	return solutions.map((result) => {
		return problem.objectives.map((obj) => {
			const value = result.objective_values && result.objective_values[obj.symbol];
			return Array.isArray(value) ? value[0] : value;
		});
	});
}

/**
 * Initialize preferences from previous state or ideal values
 * @param state The current NIMBUS response state
 * @param problem The current problem
 * @returns Array of preference values
 */
export function updatePreferencesFromState(
	state: Response | null,
	problem: ProblemInfo | null
): number[] {
	if (!problem) return [];

	// Try to get previous preference from NIMBUS state
	if (state && 'previous_preference' in state && state.previous_preference) {
		// Extract aspiration levels from previous preference
		const previous_pref = state.previous_preference as {
			aspiration_levels?: Record<string, number>;
		};
		if (previous_pref.aspiration_levels) {
			return problem.objectives.map(
				(obj) => previous_pref.aspiration_levels![obj.symbol] ?? obj.ideal ?? 0
			);
		}
	}

	// Fallback to ideal values
	return problem.objectives.map((obj) => obj.ideal ?? 0);
}

/**
 * Converts objective values in object format to array format
 * Used to transform previous objectives for visualization components
 *
 * @param objectiveObj The objective values in object format keyed by symbol
 * @param problem The problem containing objective definitions
 * @returns Array of values in the order defined by the problem objectives
 */
export function convertObjectiveToArray(
	objectiveObj: Record<string, number> | undefined | null,
	problem: ProblemInfo | null
): number[] {
	if (!problem || !objectiveObj) {
		return [];
	}

	return problem.objectives.map((obj) => {
		const value = objectiveObj[obj.symbol];
		return value !== undefined && value !== null ? (Array.isArray(value) ? value[0] : value) : 0;
	});
}

/**
 * Processes previous objective values and reference solutions for visualization components
 *
 * @param state The current NIMBUS response state
 * @param problem The problem containing objective definitions
 * @returns Array of arrays with previous objective values
 */
export function processPreviousObjectiveValues(
	state: any,
	problem: ProblemInfo | null
): number[][] {
	if (!problem || !state) {
		return [];
	}

	const result: number[][] = [];

	// Add previous_objectives if it exists
	if (state.previous_objectives) {
		result.push(convertObjectiveToArray(state.previous_objectives, problem));
	}

	// Add reference_solution_1 if it exists
	if (state.reference_solution_1) {
		result.push(convertObjectiveToArray(state.reference_solution_1, problem));
	}

	// Add reference_solution_2 if it exists
	if (state.reference_solution_2) {
		result.push(convertObjectiveToArray(state.reference_solution_2, problem));
	}

	return result;
}

/**
 * Validates if iteration is allowed based on preferences and objectives
 * Iteration requires at least one preference to be better and one to be worse
 * @param problem The current problem
 * @param preferenceValues Current preference values
 * @param objectiveValues Current objective values
 * @param precision Precision threshold for floating point comparisons
 * @returns Boolean indicating if iteration is allowed
 */
export function validateIterationAllowed(
	problem: ProblemInfo | null,
	preferenceValues: number[],
	objectiveValues: Record<string, number>,
	precision: number = 0.001
): boolean {
	if (!problem || preferenceValues.length === 0 || Object.keys(objectiveValues).length === 0) {
		return false;
	}

	let hasImprovement = false;
	let hasWorsening = false;

	for (let i = 0; i < problem.objectives.length; i++) {
		const objective = problem.objectives[i];
		const preferenceValue = preferenceValues[i];
		const currentValue = objectiveValues[objective.symbol];

		if (preferenceValue === undefined || currentValue === undefined) {
			continue;
		}

		// Check if values are approximately equal (within precision)
		const isEqual = Math.abs(preferenceValue - currentValue) < precision;

		if (isEqual) {
			// Values are approximately equal - "keep constant"
			continue;
		}

		// Determine if preference is better than current value, considering optimization direction
		const isPreferenceBetter = objective.maximize
			? preferenceValue > currentValue
			: preferenceValue < currentValue;

		// Update improvement or worsening flags based on comparison
		if (isPreferenceBetter) {
			hasImprovement = true;
		} else {
			hasWorsening = true;
		}
	}

	// Need both improvement and worsening for valid NIMBUS classification
	return hasImprovement && hasWorsening;
}

/**
 * Updates solution names from saved solutions
 *
 * @param savedSolutions - Array of saved solutions with names
 * @param targetSolutions - Array of solutions to update with names
 * @returns The updated target solutions array
 */
export function updateSolutionNames(
	savedSolutions: Solution[],
	targetSolutions: Solution[]
): Solution[] {
	if (!savedSolutions || !targetSolutions) {
		return targetSolutions;
	}

	// Create a copy of the target solutions to avoid mutating the original
	const updatedSolutions = [...targetSolutions];

	// Update names for solutions that exist in saved solutions
	for (let solution of updatedSolutions) {
		const savedIndex = savedSolutions.findIndex(
			(saved) =>
				saved.state_id === solution.state_id && saved.solution_index === solution.solution_index
		);

		if (savedIndex !== -1) {
			// Solution exists in saved_solutions, update the name
			solution.name = savedSolutions[savedIndex].name;
		}
	}

	return updatedSolutions;
}

/**
 * Generic API call function for NIMBUS operations.
 * This function wraps the fetch API to provide a consistent way to interact with the NIMBUS backend proxy.
 * It handles setting a loading state, clearing previous errors, request timeouts, and unified error handling.
 *
 * @param type The specific NIMBUS operation to perform (e.g., 'initialize', 'iterate').
 * @param data The payload to send in the request body.
 * @param timeout The timeout for the request in milliseconds. Defaults to 10000 (10 seconds).
 * @returns A promise that resolves with the data from the API response, or null if an error occurs.
 * @template T The expected type of the data in the successful response.
 */
export async function callNimbusAPI<T>(
	type: string,
	data: Record<string, any>,
	timeout = 10000 // 10s default
): Promise<T | null> {
	isLoading.set(true);
	errorMessage.set(null);
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), timeout);

	try {
		const response = await fetch(`/interactive_methods/NIMBUS/?type=${type}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(data),
			signal: controller.signal
		});

		clearTimeout(timeoutId);

		const result = await response.json();

		if (!response.ok || !result.success) {
			const errorMsg = result.error || `HTTP error! Status: ${response.status}`;
			throw new Error(errorMsg);
		}

		return result.data as T;
	} catch (error) {
		let errorMsg: string;
		if (error instanceof Error) {
			if (error.name === 'AbortError') {
				errorMsg = 'The request timed out. Please try again.';
			} else {
				errorMsg = error.message;
			}
		} else {
			errorMsg = 'An unknown error occurred';
		}
		errorMessage.set(errorMsg);
		console.error(`Error calling NIMBUS ${type} API:`, errorMsg);
		return null;
	} finally {
		isLoading.set(false);
	}
}

export async function callGNimbusAPI<T = Response>(type: string, data: Record<string, any>): Promise<{
    success: boolean;
    data?: T;
    error?: string;
}> {
    try {
        const response = await fetch(`/interactive_methods/GNIMBUS/?type=${type}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const result = await response.json();
        return result;
    } catch (error) {
        console.error(`Error calling GNIMBUS ${type} API:`, error);
        return {
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error'
        };
    }
}
