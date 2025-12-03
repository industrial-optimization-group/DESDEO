import type { components } from '$lib/api/client-types';

type ProblemInfo = components['schemas']['ProblemInfo'];

export type Solution = {
    values: { [key: string]: number };
    label?: string;
};
/**
 * Reference data structure for visualization components
 */
export type ReferenceData = {
    referencePoint?: Solution;
    previousReferencePoints?: Solution[]; // Changed from single to array
    preferredRanges?: { [key: string]: { min: number; max: number } };
    preferredSolutions?: Solution[];
    nonPreferredSolutions?: Solution[];
    otherSolutions?: Solution[];
};

/**
 * Create reference data from preference values
 * 
 * @param current_preference_values - Current iteration's preference values
 * @param previous_preference_values - Array of previous iterations' preference values
 * @param problem - Problem definition with objective symbols
 * @param tolerancePercent - Tolerance percentage for preferred ranges (default: 10%)
 * @returns Reference data object for visualization
 */
export function createReferenceData(
    current_preference_values: number[],
    previous_preference_values: number[][],
    problem: ProblemInfo | null,
    previous_objective_values?: number[][],
    other_objective_values?: number[][],
    labels?: {
        currentRefLabel?: string;
        previousRefLabel?: string;
        previousSolutionLabels?: string[];
        otherSolutionLabels?: string[];
    },
    tolerancePercent: number = 0.1
): ReferenceData | undefined {
    if (!problem?.objectives) return undefined;

    // Create reference point from current preferences
    const referencePoint: Solution = {
        values: {},
        label: labels?.currentRefLabel
    };
    if (current_preference_values.length > 0) {
        current_preference_values.forEach((value, index) => {
            if (problem.objectives[index]) {
                referencePoint.values[problem.objectives[index].symbol] = value;
            }
        });
    }

    // Create reference point from previous preferences
    const previousReferencePoints: Solution[] = [];
    if (previous_preference_values.length > 0) {
        previous_preference_values.forEach((preferenceArray) => {
            const previousReferencePoint: Solution = {
                values: {},
                label: labels?.previousRefLabel ? `${labels.previousRefLabel}` : `Previous preference`
            };
            
            preferenceArray.forEach((value, index) => {
                if (problem.objectives[index]) {
                    previousReferencePoint.values[problem.objectives[index].symbol] = value;
                }
            });
            
            if (Object.keys(previousReferencePoint.values).length > 0) {
                previousReferencePoints.push(previousReferencePoint);
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
    const preferredSolutions: Solution[] = [];
    if (previous_objective_values && previous_objective_values.length > 0 && problem.objectives.length > 0) {
        previous_objective_values.forEach((solutionArray, idx) => {
            if (solutionArray.length === problem.objectives.length) {
                const solutionObj: Solution = {
                    values: {},
                    label: labels?.previousSolutionLabels?.[idx]
                };
                solutionArray.forEach((value, index) => {
                    if (problem.objectives[index]) {
                        solutionObj.values[problem.objectives[index].symbol] = value;
                    }
                });
                if (Object.keys(solutionObj).length > 0) {
                    preferredSolutions.push(solutionObj);
                }
            }
        });
    }

    // Convert other objective values to other solutions format
    const otherSolutions: Solution[] = [];
    if (other_objective_values && other_objective_values.length > 0 && problem.objectives.length > 0) {
        other_objective_values.forEach((solutionArray, idx) => {
            if (solutionArray.length === problem.objectives.length) {
                const solutionObj: Solution = {
                    values: {},
                    label: labels?.otherSolutionLabels?.[idx]
                };
                solutionArray.forEach((value, index) => {
                    if (problem.objectives[index]) {
                        solutionObj.values[problem.objectives[index].symbol] = value;
                    }
                });
                if (Object.keys(solutionObj).length > 0) {
                    otherSolutions.push(solutionObj);
                }
            }
        });
    }
    return {
        referencePoint: Object.keys(referencePoint).length > 0 ? referencePoint : undefined,
        previousReferencePoints: previousReferencePoints.length > 0 ? previousReferencePoints : undefined,
        preferredRanges: Object.keys(preferredRanges).length > 0 ? preferredRanges : undefined,
        preferredSolutions: preferredSolutions.length > 0 ? preferredSolutions : undefined,
        otherSolutions: otherSolutions.length > 0 ? otherSolutions : undefined
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