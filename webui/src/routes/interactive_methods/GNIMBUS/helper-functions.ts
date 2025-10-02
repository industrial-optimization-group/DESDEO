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
type Solution = components["schemas"]["SolutionReference"]


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
 * TODO: does not need timeout this long, at least?
 * Generic API call function for GNIMBUS operations.
 * This function wraps the fetch API to provide a consistent way to interact with the GNIMBUS backend proxy.
 * It handles setting a loading state, clearing previous errors, request timeouts, and unified error handling.
 *
 * @param type The specific GNIMBUS operation to perform (e.g., 'switch_phase', 'get_all_iterations').
 * @param data The payload to send in the request body.
 * @param timeout The timeout for the request in milliseconds. Defaults to 10000 (10 seconds).
 * @returns A promise that resolves with the data from the API response, or null if an error occurs.
 * @template T The expected type of the data in the successful response.
 */
/**
 * Maps solutions objective values to arrays suitable for visualization components
 * @param solutions Array of solutions with objective values
 * @param problem The problem containing objective definitions
 * @returns Array of arrays with objective values in the order defined by the problem
 */
export function mapSolutionsToObjectiveValues(solutions: Solution[], problem: ProblemInfo) {
    return solutions.map(result => {
        return problem.objectives.map(obj => {
            const value = result.objective_values && result.objective_values[obj.symbol];
            return Array.isArray(value) ? value[0] : value;
        });
    });
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
