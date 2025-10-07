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
	message: string;
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
 *        - message: Current WebSocket or system message
 *        - isOwner: Whether current user is group owner
 *        - isDecisionMaker: Whether current user is a decision maker
 *        - step: Current step (optimization/voting)
 *        - phase: Current phase (learning/crp/decision)
 *        - isActionDone: Whether user has completed their current action
 * @returns Object containing status message text and alert flag
 */
export function getStatusMessage(state: MessageState): { text: string; isAlert?: boolean } {
	// Handle websocket messages first
	if (
		state.message &&
		!state.message.includes('Please fetch') &&
		!state.message.includes('Voting has concluded')
	) {
		return { text: state.message };
	}

	// Owner but not decision maker
	if (state.isOwner && !state.isDecisionMaker) {
		return {
			text:
				state.step === 'optimization'
					? `Viewing current solutions in ${state.phase} phase. Phase can be switched during optimization steps.`
					: `Viewing solutions in ${state.phase} phase. Please wait for voting to complete.`
		};
	}

	// Decision maker in voting mode
	if (state.step === 'voting' && state.isDecisionMaker) {
		return {
			text: state.isActionDone
				? 'Waiting for other users to finish voting. You can still change your vote by selecting another solution.'
				: 'Please vote for your preferred solution by selecting it from the table below.',
			isAlert: !state.isActionDone
		};
	}

	// Decision maker in optimization mode
	if (state.step === 'optimization' && state.isDecisionMaker) {
		return {
			text: state.isActionDone
				? 'Waiting for other users to finish their iterations. You can still modify your preferences and iterate again.'
				: 'Please set your preferences for the current solution using the classification interface on the left.',
			isAlert: !state.isActionDone
		};
	}

	// Default case
	return { text: 'Viewing group progress.' };
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
 * TODO: timeout thing, general http and websocket cleaning and refactoring. if errors and spinners not needed, remove from imports
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
	data: Record<string, any>
): Promise<{
	success: boolean;
	data?: T;
	error?: string;
}> {
	try {
		const response = await fetch(`/interactive_methods/GNIMBUS/?type=${type}`, {
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
		console.error(`Error calling GNIMBUS ${type} API:`, error);
		return {
			success: false,
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
}
