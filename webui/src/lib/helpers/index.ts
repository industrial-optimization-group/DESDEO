import type { components } from '$lib/api/client-types';
import { CLASSIFICATION_TYPES, PREFERENCE_TYPES, SIGNIFICANT_DIGITS } from '$lib/constants';

type ObjectiveInfo = components['schemas']['ProblemInfo']['objectives'][0];
type ProblemInfo = components['schemas']['ProblemInfo'];

export function calculateClassification(
  objective: ObjectiveInfo,
  selectedValue: number | undefined,
  currentObjectiveValue: number | undefined = undefined,
  precision = 0.001
): string {
  if (objective.ideal == null || objective.nadir == null) {
    return CLASSIFICATION_TYPES.ChangeFreely;
  }

  const lowerBound = Math.min(objective.ideal, objective.nadir);
  const higherBound = Math.max(objective.ideal, objective.nadir);
  const solutionValue = currentObjectiveValue !== undefined ? currentObjectiveValue : undefined;

  if (selectedValue === undefined || solutionValue === undefined) {
    return CLASSIFICATION_TYPES.ChangeFreely;
  }

  // Check if at bounds
  if (Math.abs(selectedValue - lowerBound) < precision || selectedValue < lowerBound) {
    // At lower bound
    return objective.maximize ? CLASSIFICATION_TYPES.ChangeFreely : CLASSIFICATION_TYPES.ImproveFreely;
  } else if (Math.abs(selectedValue - higherBound) < precision || selectedValue > higherBound) {
    // At upper bound
    return objective.maximize ? CLASSIFICATION_TYPES.ImproveFreely : CLASSIFICATION_TYPES.ChangeFreely;
  } else if (Math.abs(selectedValue - solutionValue) < precision) {
    // At current solution value
    return CLASSIFICATION_TYPES.KeepConstant;
  }

  // Determine if the selected value is better or worse than solution value
  // based on objective's optimization direction
  const isSelectedBetter = objective.maximize 
    ? selectedValue > solutionValue  // For maximization: higher is better
    : selectedValue < solutionValue; // For minimization: lower is better

  return isSelectedBetter 
    ? CLASSIFICATION_TYPES.ImproveUntil 
    : CLASSIFICATION_TYPES.WorsenUntil;
}

export function getObjectiveBounds(objective: ObjectiveInfo) {
  if (objective.ideal == null || objective.nadir == null) {
    return null;
  }
  return {
    min: Math.min(objective.ideal, objective.nadir),
    max: Math.max(objective.ideal, objective.nadir)
  };
}

export function clampValue(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export type PreferenceType = keyof typeof PREFERENCE_TYPES;
export type PreferenceValue = typeof PREFERENCE_TYPES[PreferenceType];


export function formatNumber(value: number, digits: number = SIGNIFICANT_DIGITS): string {
  return value.toFixed(digits); // toFixed or toPrecision?
}

export function formatNumberArray(values: number[], digits: number = SIGNIFICANT_DIGITS): string {
  return values.map(v => formatNumber(v, digits)).join(', ');
}

/**
 * Gets the display accuracy from problem metadata or returns default value
 * TODO: This function is just a mock function that tries to find information that doesn't exist,
 * and defaults to accuracy of SIGNIFICANT_DIGITS.
 * @param problem The problem to check
 * @returns The display accuracy (number of significant digits)
 */
export function getDisplayAccuracy(problem: ProblemInfo | null): number[] {
    // Default to 2 significant digits if not specified
    const DEFAULT_ACCURACY = SIGNIFICANT_DIGITS;
    
    if (!problem) {
        return [];
    }
    if (!problem.problem_metadata ) {
        return problem.objectives.map(() => DEFAULT_ACCURACY);
    }

    // Check if metadata has display_accuracy field with per-objective accuracies
    // TODO: this does not make sense: I dont know where in the metadata the display accuracy would exist, since it doesn't,
    // and metadata might need to be fetched in http request?
    // Anyway, this is just mocking anyway.
    if ('display_accuracy' in problem.problem_metadata) {
        const displayAccuracy = problem.problem_metadata.display_accuracy;
        
        // If it's an array, use it (assuming it matches objectives length)
        if (Array.isArray(displayAccuracy)) {
            // Pad with defaults if array is shorter than objectives
            const result = displayAccuracy.slice(0, problem.objectives.length);
            while (result.length < problem.objectives.length) {
                result.push(DEFAULT_ACCURACY);
            }
            return result.map(acc => typeof acc === 'number' ? acc : DEFAULT_ACCURACY);
        }
        
        // If it's a single number, use it for all objectives
        if (typeof displayAccuracy === 'number') {
            return problem.objectives.map(() => displayAccuracy);
        }
    }

    return problem.objectives.map(() => DEFAULT_ACCURACY);
}