import type { components } from '$lib/api/client-types';
import { CLASSIFICATION_TYPES } from '$lib/constants';

type ObjectiveInfo = components['schemas']['ProblemInfo']['objectives'][0];

export function calculateClassification(
  objective: ObjectiveInfo,
  selectedValue: number | undefined,
  precision = 0.001
): string {
  if (objective.ideal == null || objective.nadir == null) {
    return CLASSIFICATION_TYPES.ChangeFreely;
  }

  const solutionValue = objective.ideal;
  const lowerBound = Math.min(objective.ideal, objective.nadir);
  const higherBound = Math.max(objective.ideal, objective.nadir);

  if (selectedValue === undefined || solutionValue === undefined) {
    return CLASSIFICATION_TYPES.ChangeFreely;
  }

  if (Math.abs(selectedValue - lowerBound) < precision || selectedValue < lowerBound) {
    return CLASSIFICATION_TYPES.ChangeFreely;
  } else if (Math.abs(selectedValue - higherBound) < precision || selectedValue > higherBound) {
    return CLASSIFICATION_TYPES.ImproveFreely;
  } else if (Math.abs(selectedValue - solutionValue) < precision) {
    return CLASSIFICATION_TYPES.KeepConstant;
  } else if (selectedValue < solutionValue) {
    return CLASSIFICATION_TYPES.WorsenUntil;
  } else if (selectedValue > solutionValue) {
    return CLASSIFICATION_TYPES.ImproveUntil;
  }

  return CLASSIFICATION_TYPES.ChangeFreely;
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