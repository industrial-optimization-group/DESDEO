/**
 * GNIMBUS Helper Functions
 *
 * This file contains utility functions for the GNIMBUS interactive group decision making method.
 * Functions handle data transformation, validation, API calls, message handling,
 * and visualization data preparation.
 *
 * @author Stina Palomäki <palomakistina@gmail.com>
 * @created October 2025
 */

import type { ProblemInfo, Solution, Response } from './types';
import { errorMessage, isLoading } from '../../../stores/uiState';

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

interface MessageState {
	isOwner: boolean;
	isDecisionMaker: boolean;
	step: 'optimization' | 'voting' | 'finish';
	phase: string;
	isActionDone: boolean;
}
/**
 * Determines the appropriate status message based on current application state
 *
 * @param state Current state of the application including:
 *        - isOwner: Whether current user is group owner
 *        - isDecisionMaker: Whether current user is a decision maker
 *        - step: Current step (optimization/voting)
 *        - phase: Current phase (learning/crp/decision)
 *        - isActionDone: Whether user has completed their current action
 * @returns Status message text, that is the instruction text depending on step
 */
export function getStatusMessage(state: MessageState): string {
	// Owner but not decision maker
	if (state.isOwner && !state.isDecisionMaker) {
		let phase = state.phase === 'init' ? 'learning' : state.phase;
		return state.step === 'optimization'
			? `Viewing current solutions in ${phase} phase. \n Click button to choose next phase.`
			: `Viewing solutions in ${phase} phase. Please wait for voting to complete.`;
	}

	// Decision maker in voting mode
	if (state.step === 'voting' && state.isDecisionMaker) {
		return state.isActionDone
				? 'Waiting for other users to finish voting. You can still change your vote by selecting another solution.'
				: 'Please vote for your preferred solution by selecting it from the table below.';
	}

	// Decision maker in optimization mode
	if (state.step === 'optimization' && state.isDecisionMaker) {
		return  state.isActionDone
				? 'Waiting for other users to finish their iterations. You can still modify your preferences and iterate again.'
				: 'Please set your preferences for the current solution using the classification interface on the left.';
	}

	// Default case
	return 'Viewing group progress.';
}

export interface VisualizationData {
	solutions: number[][];
	previous: number[][];
	others: number[][];
}

export interface PreferenceData {
	previousValues: number[];
	currentValues: number[];
}

export function createVisualizationData(
	problem: ProblemInfo | null,
	step: string,
	currentState: Response,
	solutionOptions: Solution[]
): VisualizationData {
	if (!problem) return { solutions: [], previous: [], others: [] };

	return {
		solutions: mapSolutionsToObjectiveValues(solutionOptions, problem),
		previous:
			step === 'voting' &&
			currentState.phase !== 'decision' &&
			currentState.personal_result_index !== null
				? mapSolutionsToObjectiveValues(
						[currentState.user_results[currentState.personal_result_index]],
						problem
					)
				: [],
		others:
			step === 'voting' ? mapSolutionsToObjectiveValues(currentState.user_results, problem) : []
	};
}

export function createPreferenceData(
	step: string,
	lastIteratedPreference: number[],
	currentPreference: number[]
): PreferenceData {
	return {
		previousValues: step === 'optimization' ? lastIteratedPreference : [],
		currentValues: step === 'optimization' ? currentPreference : []
	};
}

// Helper function to determine the current step based on iteration state
export function determineStep(iteration: Response): 'optimization' | 'voting' | 'finish' {
	if (iteration.phase === 'init') {
		return 'optimization';
	}
	if (
		iteration.phase === 'decision' &&
		iteration.voting_preferences?.method === 'end' &&
		iteration.voting_preferences.success
	) {
		return 'finish';
	}
	return iteration.voting_preferences !== null ? 'optimization' : 'voting';
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
 * Maps solutions objective values to arrays suitable for visualization components
 *
 * @param solutions Array of solutions with objective values
 * @param problem The problem containing objective definitions
 * @returns Array of arrays with objective values in the order defined by the problem
 */
export function mapSolutionsToObjectiveValues(solutions: Solution[], problem: ProblemInfo) {
	return solutions.map((solution) => {
		return problem.objectives.map((obj) => {
			const value = solution.objective_values && solution.objective_values[obj.symbol];
			return Array.isArray(value) ? value[0] : value;
		});
	});
}

/**
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
export async function callGNimbusAPI<T>(
	type: string,
	data: Record<string, any>,
	timeout = 10000 // 10s default
): Promise<{
	success: boolean;
	data?: T;
	error?: string;
}> {
	isLoading.set(true);
	errorMessage.set(null);
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), timeout);

	try {
		const response = await fetch(`/interactive_methods/GNIMBUS/?type=${type}`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(data),
			signal: controller.signal
		});

		clearTimeout(timeoutId);

		const result = await response.json();

		if (!response.ok || !result.success) {
			const status = response.status;
			console.log(status)
			let errorMsg = result.error || `HTTP error! Status: ${status}`;
			if (status === 401) errorMsg = `${errorMsg} Please log in again.`;
			// if (status === 403) errorMsg = `${errorMsg} You do not have permission to perform this action.`; // TODO: use if needed
			throw new Error(errorMsg);
		}
		return result;
		
	} catch (error) {
		let errorMsg: string;
		if (error instanceof Error) {
			if (error.name === 'AbortError') {
				errorMsg = 'The request timed out. Please try again.';
			} else {
				errorMsg = error.message;
			}
		} else {
			errorMsg = 'An unknown error occurred';
		}
		errorMessage.set(errorMsg);
		console.error(`Error calling NIMBUS ${type} API:`, errorMsg);
		return { success: false, error: errorMsg };
	} finally {
		isLoading.set(false);
	}
}
