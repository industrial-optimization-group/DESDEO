import type { components } from '$lib/api/client-types';

type ProblemInfo = components['schemas']['ProblemInfo'];
type Solution = components['schemas']['UserSavedSolutionAddress'];

// Define the Response type needed for our helper functions
type NIMBUSClassificationResponse = components['schemas']['NIMBUSClassificationResponse'];
type NIMBUSInitializationResponse = components['schemas']['NIMBUSInitializationResponse'];
type BaseResponse = NIMBUSClassificationResponse | NIMBUSInitializationResponse;
type Response = BaseResponse & {
    current_solutions: Solution[],
    saved_solutions: Solution[],
    all_solutions: Solution[],
};

/**
 * Checks if a problem has utopia metadata for map visualization
 * @param prob The problem to check
 * @returns boolean indicating if the problem has utopia metadata
 */
export function checkUtopiaMetadata(prob: ProblemInfo | null) {
    if (!prob || !prob.problem_metadata || !prob.problem_metadata.data) {
        return false;
    }
    return prob.problem_metadata.data.some(meta => meta.metadata_type === "forest_problem_metadata");
}

/**
 * Maps solutions objective values to arrays suitable for visualization components
 * @param solutions Array of solutions with objective values
 * @param problem The problem containing objective definitions
 * @returns Array of arrays with objective values in the order defined by the problem
 */
export function mapSolutionsToObjectiveValues(solutions: Solution[], problem: ProblemInfo) {
    return solutions.map(result => {
        return problem.objectives.map(obj => {
            const value = result.objective_values[obj.symbol];
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
export function updatePreferencesFromState(state: Response | null, problem: ProblemInfo | null): number[] {
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
 * Validates if iteration is allowed based on preferences and objectives
 * Iteration requires at least one preference to be better and one to be worse
 * @param problem The current problem
 * @param preferenceValues Current preference values
 * @param objectiveValues Current objective values
 * @returns Boolean indicating if iteration is allowed
 */
export function validateIterationAllowed(
    problem: ProblemInfo | null,
    preferenceValues: number[],
    objectiveValues: Record<string, number>
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

        // Check if preference differs from current value
        if (preferenceValue > currentValue) {
            hasImprovement = true;
        } else if (preferenceValue < currentValue) {
            hasWorsening = true;
        }
    }

    // Need both improvement and worsening for valid NIMBUS classification
    return hasImprovement && hasWorsening;
}

/**
 * Generic API call function for NIMBUS operations
 * @param type The operation type (initialize, iterate, intermediate, save, choose, get_maps)
 * @param data The data to send in the request body
 * @returns Promise with the API response
 */
export async function callNimbusAPI<T = Response>(type: string, data: Record<string, any>): Promise<{
    success: boolean;
    data?: T;
    error?: string;
}> {
    try {
        const response = await fetch(`/interactive_methods/NIMBUS/?type=${type}`, {
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
        console.error(`Error calling NIMBUS ${type} API:`, error);
        return {
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error'
        };
    }
}
