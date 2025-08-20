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
 * @param problem The problem to check
 * @returns The display accuracy (number of significant digits)
 */
export function getDisplayAccuracy(problem: ProblemInfo | null): number {
    // Default to 2 significant digits if not specified
    const DEFAULT_ACCURACY = SIGNIFICANT_DIGITS;
    
    if (!problem || !problem.problem_metadata || !problem.problem_metadata.data) {
        return DEFAULT_ACCURACY;
    }

    // Check if any metadata has display_accuracy field
    for (const meta of problem.problem_metadata.data) {
        if ('display_accuracy' in meta && typeof meta.display_accuracy === 'number') {
            return meta.display_accuracy;
        }
    }

    return DEFAULT_ACCURACY;
}