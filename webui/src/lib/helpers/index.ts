import type { components } from '$lib/api/client-types';
import { CLASSIFICATION_TYPES, PREFERENCE_TYPES } from '$lib/constants';

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

export type PreferenceType = keyof typeof PREFERENCE_TYPES;
export type PreferenceValue = typeof PREFERENCE_TYPES[PreferenceType];

export function validatePreferenceTypes(types: string[]): PreferenceValue[] {
  const validTypes = Object.values(PREFERENCE_TYPES);
  return types.filter((type): type is PreferenceValue => 
    validTypes.includes(type as PreferenceValue)
  );
}

export function isValidPreferenceType(type: string): type is PreferenceValue {
  return Object.values(PREFERENCE_TYPES).includes(type as PreferenceValue);
}

export interface PreferenceValues {
  [PREFERENCE_TYPES.Classification]: number[];
  [PREFERENCE_TYPES.ReferencePoint]: number[];
  [PREFERENCE_TYPES.PreferredRange]: { lower: number[]; upper: number[] };
  [PREFERENCE_TYPES.PreferredSolution]: number[];
  [PREFERENCE_TYPES.NonPreferredSolution]: number[];
}

export type PreferenceValueType<T extends PreferenceValue> = PreferenceValues[T];

export function createDefaultPreferenceValues(objectives: ObjectiveInfo[]): PreferenceValues {
  const defaultValues = objectives.map(obj => typeof obj.ideal === 'number' ? obj.ideal : 0);
  
  return {
    [PREFERENCE_TYPES.Classification]: [...defaultValues],
    [PREFERENCE_TYPES.ReferencePoint]: [...defaultValues],
    [PREFERENCE_TYPES.PreferredRange]: {
      lower: [...defaultValues],
      upper: [...defaultValues]
    },
    [PREFERENCE_TYPES.PreferredSolution]: [...defaultValues],
    [PREFERENCE_TYPES.NonPreferredSolution]: [...defaultValues]
  };
}