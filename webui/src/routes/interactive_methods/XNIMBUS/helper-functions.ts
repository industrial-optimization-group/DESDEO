/**
 * XNIMBUS Helper Functions
 *
 * Utility functions for the XNIMBUS (Explainable NIMBUS) interactive multiobjective optimization method.
 */

import type {
	ProblemInfo,
	SolutionReferenceResponse
} from '$lib/gen/models';

type Solution = SolutionReferenceResponse;

export function checkUtopiaMetadata(prob: ProblemInfo | null) {
	if (!prob || !prob.problem_metadata) {
		return false;
	}
	return (
		prob.problem_metadata.forest_metadata !== null &&
		Array.isArray(prob.problem_metadata.forest_metadata) &&
		prob.problem_metadata.forest_metadata.length > 0
	);
}

export function mapSolutionsToObjectiveValues(solutions: Solution[], problem: ProblemInfo) {
	return solutions.map((result) => {
		return problem.objectives.map((obj) => {
			const value = result.objective_values && result.objective_values[obj.symbol];
			return Array.isArray(value) ? value[0] : value;
		});
	});
}

export function getDictionaryObjectiveNames(problem: ProblemInfo) {
	const objectiveNames: Record<string, string> = {};
	problem.objectives.forEach((obj) => {
		objectiveNames[obj.symbol] = obj.name ?? obj.symbol;
	});
	return objectiveNames;
}

export function updatePreferencesFromState(
	state: Record<string, unknown> | null,
	problem: ProblemInfo | null
): number[] {
	if (!problem) return [];

	if (state && 'previous_preference' in state && state.previous_preference) {
		const previous_pref = state.previous_preference as {
			aspiration_levels?: Record<string, number>;
		};
		if (previous_pref.aspiration_levels) {
			return problem.objectives.map(
				(obj) => previous_pref.aspiration_levels![obj.symbol] ?? obj.ideal ?? 0
			);
		}
	}

	return problem.objectives.map((obj) => obj.ideal ?? 0);
}

export function isInitialState(state: Record<string, unknown> | null): boolean {
	if (state && 'previous_preference' in state && state.previous_preference) {
		return false;
	}
	return true;
}

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

export function processPreviousObjectiveValues(
	state: any,
	problem: ProblemInfo | null
): number[][] {
	if (!problem || !state) {
		return [];
	}

	const result: number[][] = [];

	if (state.previous_objectives) {
		result.push(convertObjectiveToArray(state.previous_objectives, problem));
	}
	if (state.reference_solution_1) {
		result.push(convertObjectiveToArray(state.reference_solution_1, problem));
	}
	if (state.reference_solution_2) {
		result.push(convertObjectiveToArray(state.reference_solution_2, problem));
	}

	return result;
}

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

		const isEqual = Math.abs(preferenceValue - currentValue) < precision;

		if (isEqual) {
			continue;
		}

		const isPreferenceBetter = objective.maximize
			? preferenceValue > currentValue
			: preferenceValue < currentValue;

		if (isPreferenceBetter) {
			hasImprovement = true;
		} else {
			hasWorsening = true;
		}
	}

	return hasImprovement && hasWorsening;
}

export function updateSolutionNames(
	savedSolutions: Solution[],
	targetSolutions: Solution[]
): Solution[] {
	if (!savedSolutions || !targetSolutions) {
		return targetSolutions;
	}

	const updatedSolutions = [...targetSolutions];

	for (let solution of updatedSolutions) {
		const savedIndex = savedSolutions.findIndex(
			(saved) =>
				saved.state_id === solution.state_id && saved.solution_index === solution.solution_index
		);

		if (savedIndex !== -1) {
			solution.name = savedSolutions[savedIndex].name;
		}
	}

	return updatedSolutions;
}

export function getRangeMultipliers(
	multipliers: Array<Record<string, number>> | null | undefined
): Record<string, { min: number; max: number }> {
	if (!multipliers || multipliers.length === 0) {
		return {};
	}
	const objectiveKeys = Object.keys(multipliers[0]);
	const minMax: Record<string, { min: number; max: number }> = {};

	objectiveKeys.forEach((key) => {
		let min = Infinity;
		let max = -Infinity;
		multipliers.forEach((solution) => {
			const value = solution[key];
			if (value !== undefined) {
				if (value < min) min = value;
				if (value > max) max = value;
			}
		});
		minMax[key] = { min, max };
	});

	return minMax;
}

export function getRangeTradeoffs(
	tradeoffs: number[][] | null | undefined
): { min: number; max: number }[] {
	if (!tradeoffs || tradeoffs.length === 0) {
		return [{ min: 0, max: 0 }];
	}

	const nObjectives = tradeoffs.length;
	const minMax: { min: number; max: number }[] = [];
	for (let j = 0; j < nObjectives; j++) {
		let min = Infinity;
		let max = -Infinity;
		for (let i = 0; i < nObjectives; i++) {
			const value = tradeoffs[i][j];
			if (value < min) min = value;
			if (value > max) max = value;
		}
		minMax.push({ min, max });
	}
	return minMax;
}

export function normalizeMultipliers(
	multipliers: Array<Record<string, number>> | null | undefined
): Array<Record<string, number>> {
	if (!multipliers || multipliers.length === 0) {
		return [];
	}

	const objectiveKeys = Object.keys(multipliers[0]);
	const normalizedMultipliers: Array<Record<string, number>> = [];
	const minMax = getRangeMultipliers(multipliers);

	multipliers.forEach((solution) => {
		const normalizedSolution: Record<string, number> = {};
		objectiveKeys.forEach((key) => {
			const value = solution[key];
			const range = minMax[key].max - minMax[key].min;
			if (range === 0) {
				normalizedSolution[key] = 0;
			} else {
				normalizedSolution[key] = (value - minMax[key].min) / range;
			}
		});
		normalizedMultipliers.push(normalizedSolution);
	});

	return normalizedMultipliers;
}

export function normalizeTradeoffs(
	tradeoffs: number[][] | null | undefined
): number[][] {
	if (!tradeoffs || tradeoffs.length === 0) {
		return [];
	}

	const nObjectives = tradeoffs.length;
	const normalizedTradeoffs: number[][] = [];
	const minMax = getRangeTradeoffs(tradeoffs);

	for (let i = 0; i < nObjectives; i++) {
		const normalizedRow: number[] = [];
		for (let j = 0; j < nObjectives; j++) {
			const value = tradeoffs[i][j];
			const range = minMax[j].max - minMax[j].min;
			if (range === 0) {
				normalizedRow.push(0);
			} else {
				normalizedRow.push((value - minMax[j].min) / range);
			}
		}
		normalizedTradeoffs.push(normalizedRow);
	}

	return normalizedTradeoffs;
}
