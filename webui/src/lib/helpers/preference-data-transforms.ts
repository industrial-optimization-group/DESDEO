import type { components } from '$lib/api/client-types';

type ProblemInfo = components['schemas']['ProblemInfo'];

/**
 * Reference data structure for visualization components
 */
export type ReferenceData = {
    referencePoint?: { [key: string]: number };
    preferredRanges?: { [key: string]: { min: number; max: number } };
    preferredSolutions?: Array<{ [key: string]: number }>;
    nonPreferredSolutions?: Array<{ [key: string]: number }>;
};

/**
 * Create reference data from preference values
 * 
 * @param current_preference_values - Current iteration's preference values
 * @param previous_preference_values - Previous iteration's preference values
 * @param problem - Problem definition with objective names
 * @param tolerancePercent - Tolerance percentage for preferred ranges (default: 10%)
 * @returns Reference data object for visualization
 */
export function createReferenceData(
    current_preference_values: number[],
    previous_preference_values: number[],
    problem: ProblemInfo | null,
    tolerancePercent: number = 0.1
): ReferenceData | undefined {
    if (!problem?.objectives) return undefined;

    // Create reference point from current preferences
    const referencePoint: { [key: string]: number } = {};
    if (current_preference_values.length > 0) {
        current_preference_values.forEach((value, index) => {
            if (problem.objectives[index]) {
                referencePoint[problem.objectives[index].name] = value;
            }
        });
    }

    // Create preferred ranges with tolerance
    const preferredRanges: { [key: string]: { min: number; max: number } } = {};
    if (current_preference_values.length > 0) {
        current_preference_values.forEach((value, index) => {
            if (problem.objectives[index]) {
                const objName = problem.objectives[index].name;
                const tolerance = Math.abs(value * tolerancePercent);
                preferredRanges[objName] = {
                    min: value - tolerance,
                    max: value + tolerance
                };
            }
        });
    }

    return {
        referencePoint: Object.keys(referencePoint).length > 0 ? referencePoint : undefined,
        preferredRanges: Object.keys(preferredRanges).length > 0 ? preferredRanges : undefined
    };
}

/**
 * Convert preference values array to named object
 * 
 * @param preference_values - Array of preference values
 * @param problem - Problem definition with objective names
 * @returns Object mapping objective names to preference values
 */
export function preferencesToNamedObject(
    preference_values: number[],
    problem: ProblemInfo | null
): { [key: string]: number } {
    const result: { [key: string]: number } = {};
    
    if (!problem?.objectives || !preference_values.length) return result;

    preference_values.forEach((value, index) => {
        if (problem.objectives[index]) {
            result[problem.objectives[index].name] = value;
        }
    });

    return result;
}