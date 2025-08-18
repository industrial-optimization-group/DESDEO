import type { components } from '$lib/api/client-types';

type ProblemInfo = components['schemas']['ProblemInfo'];

/**
 * Reference data structure for visualization components
 */
export type ReferenceData = {
    referencePoint?: { [key: string]: number };
    previousReferencePoint?: { [key: string]: number };
    preferredRanges?: { [key: string]: { min: number; max: number } };
    preferredSolutions?: Array<{ [key: string]: number }>;
    nonPreferredSolutions?: Array<{ [key: string]: number }>;
};

/**
 * Create reference data from preference values
 * 
 * @param current_preference_values - Current iteration's preference values
 * @param previous_preference_values - Previous iteration's preference values
 * @param problem - Problem definition with objective symbols
 * @param tolerancePercent - Tolerance percentage for preferred ranges (default: 10%)
 * @returns Reference data object for visualization
 */
export function createReferenceData(
    current_preference_values: number[],
    previous_preference_values: number[],
    problem: ProblemInfo | null,
    previous_objective_values?: number[][],
    tolerancePercent: number = 0.1
): ReferenceData | undefined {
    if (!problem?.objectives) return undefined;

    // Create reference point from current preferences
    const referencePoint: { [key: string]: number } = {};
    if (current_preference_values.length > 0) {
        current_preference_values.forEach((value, index) => {
            if (problem.objectives[index]) {
                referencePoint[problem.objectives[index].symbol] = value;
            }
        });
    }

    // Create reference point from previous preferences
    const previousReferencePoint: { [key: string]: number } = {};
    if (previous_preference_values.length > 0) {
        previous_preference_values.forEach((value, index) => {
            if (problem.objectives[index]) {
                previousReferencePoint[problem.objectives[index].symbol] = value;
            }
        });
    }

    // Create preferred ranges with tolerance
    const preferredRanges: { [key: string]: { min: number; max: number } } = {};
    if (current_preference_values.length > 0) {
        current_preference_values.forEach((value, index) => {
            if (problem.objectives[index]) {
                const objSymbol = problem.objectives[index].symbol;
                const tolerance = Math.abs(value * tolerancePercent);
                preferredRanges[objSymbol] = {
                    min: value - tolerance,
                    max: value + tolerance
                };
            }
        });
    }

    // Convert previous objective values to preferred solutions format
    const preferredSolutions: Array<{ [key: string]: number }> = [];
    if (previous_objective_values && previous_objective_values.length > 0 && problem.objectives.length > 0) {
        previous_objective_values.forEach(solutionArray => {
            if (solutionArray.length === problem.objectives.length) {
                const solutionObj: { [key: string]: number } = {};
                solutionArray.forEach((value, index) => {
                    if (problem.objectives[index]) {
                        solutionObj[problem.objectives[index].symbol] = value;
                    }
                });
                if (Object.keys(solutionObj).length > 0) {
                    preferredSolutions.push(solutionObj);
                }
            }
        });
    }
    
    return {
        referencePoint: Object.keys(referencePoint).length > 0 ? referencePoint : undefined,
        previousReferencePoint: Object.keys(previousReferencePoint).length > 0 ? previousReferencePoint : undefined,
        preferredRanges: Object.keys(preferredRanges).length > 0 ? preferredRanges : undefined,
        preferredSolutions: preferredSolutions.length > 0 ? preferredSolutions : undefined
    };
}

/**
 * Convert preference values array to named object, symbol as name
 * 
 * @param preference_values - Array of preference values
 * @param problem - Problem definition with objective symbols
 * @returns Object mapping objective symbols to preference values
 */
export function preferencesToNamedObject(
    preference_values: number[],
    problem: ProblemInfo | null
): { [key: string]: number } {
    const result: { [key: string]: number } = {};
    
    if (!problem?.objectives || !preference_values.length) return result;

    preference_values.forEach((value, index) => {
        if (problem.objectives[index]) {
            result[problem.objectives[index].symbol] = value;
        }
    });

    return result;
}