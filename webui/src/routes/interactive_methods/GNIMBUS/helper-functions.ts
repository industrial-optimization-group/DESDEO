/**
 * GNIMBUS Helper Functions
 *
 * @author Stina Palomäki <palomakistina@gmail.com>
 * @created October 2025
 * @updated November 2025
 *
 * @description
 * This file contains utility functions for the GNIMBUS interactive group decision making method.
 * Functions handle data transformation, validation, API calls, message handling,
 * visualization data preparation, and state management.
 *
 * @features
 * - Problem metadata validation (UTOPIA map support)
 * - User status message generation based on role and phase
 * - Data transformation for visualizations
 * - Preference validation and iteration control
 * - Solution history computation and organization
 * - API communication with unified error handling
 * - State synchronization utilities
 */

import type { ProblemInfo, Solution, Response, AllIterations } from './types';
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
	isActionDone: boolean;
	phase: string;
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
 * @returns Status message text with formatted phase names and clear instructions
 */
export function getStatusMessage(state: MessageState): string {
	// Process finished
	if (state.step === 'finish') {
		return 'The decision process has ended succesfully. Viewing the selected final solution below.';
	}

	// Owner but not decision maker
	if (state.isOwner && !state.isDecisionMaker) {
		return state.step === 'optimization'
			? `Click button to change the phase.`
			: `Please wait for decision makers to complete voting.`;
	}

	// Decision maker in voting mode
	if (state.step === 'voting' && state.isDecisionMaker) {
		if (state.phase === 'decision' || state.phase === 'compromise') {
			return state.isActionDone
				? `Your vote has been recorded. You may change your vote while waiting for others to complete.`
				: `Please vote for choosing the suggested solution as a final solution.`;
		}
		return state.isActionDone
			? `Your vote has been recorded. You may change your vote while waiting for others to complete.`
			: `Please select your preferred solution from visualization or table to cast your vote.`;
	}

	// Decision maker in optimization mode
	if (state.step === 'optimization' && state.isDecisionMaker) {
		return state.isActionDone
			? `Your preferences are set. You may modify them while waiting for other decision makers.`
			: `Use the classification interface on the left to set your preferences for the current solution.`;
	}

	// Default case
	return 'Viewing group progress.';
}

export interface VisualizationData {
	solutions: number[][];
	previous: number[][];
	others: number[][];
	solutionLabels?:
		| {
				[key: string]: string;
		  }
		| undefined;
}

export interface PreferenceData {
	previousValues: number[][];
	currentValues: number[];
}

export function createVisualizationData(
	problem: ProblemInfo | null,
	step: string,
	currentState: Response,
	solutionOptions: any[],
	historyOption: 'current' | 'all_own' | 'all_group' | 'all_final',
	isDecisionMaker: boolean
): VisualizationData {
	if (!problem) return { solutions: [], previous: [], others: [] };

	let solutionLabels;
	if (historyOption === 'all_own') {
		solutionLabels = Object.fromEntries(
			solutionOptions.map((solution, i) => {
				return isDecisionMaker
					? [
							i,
							solutionOptions.length === 1
								? 'Your solution'
								: `Your solution ${solution.iteration_number ?? ''}`
						]
					: [
							i,
							solutionOptions.length === 1
								? 'Users solution'
								: `Users solution ${solution.iteration_number ?? ''}`
						];
			})
		);
	} else if (historyOption === 'all_final') {
		solutionLabels = Object.fromEntries(
			solutionOptions.map((solution, i) => {
				return [
					i,
					solutionOptions.length === 1
						? 'Group solution'
						: `Group solution ${solution.iteration_number ?? ''}`
				];
			})
		);
	} else {
		solutionLabels = Object.fromEntries(
			solutionOptions.map((solution, i) => [
				i,
				solutionOptions.length === 1
					? 'Group solution'
					: `Group solution ${solution.solution_index}`
			])
		);
	}

	return {
		solutions: mapSolutionsToObjectiveValues(solutionOptions, problem),
		previous:
			step === 'voting' &&
			currentState.phase !== 'decision' &&
			currentState.phase !== 'compromise' &&
			currentState.personal_result_index !== null
				? mapSolutionsToObjectiveValues(
						[currentState.user_results[currentState.personal_result_index]],
						problem
					)
				: [],
		others:
			step === 'voting' ? mapSolutionsToObjectiveValues(currentState.user_results, problem) : [],
		solutionLabels
	};
}

export function createPreferenceData(
	step: string,
	lastIteratedPreference: number[],
	currentPreference: number[]
): PreferenceData {
	return {
		previousValues: [lastIteratedPreference],
		currentValues: step === 'optimization' ? currentPreference : []
	};
}

// Helper function to determine the current step based on iteration state
export function determineStep(iteration: Response): 'optimization' | 'voting' | 'finish' {
	if (iteration.phase === 'init') {
		return 'optimization';
	}
	if (
		(iteration.phase === 'decision' || iteration.phase === 'compromise') &&
		iteration.voting_preferences?.method === 'end' &&
		iteration.voting_preferences.success
	) {
		return 'finish';
	}
	return iteration.final_result !== null ? 'optimization' : 'voting';
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

export interface HistoryData {
	own_solutions: any[];
	common_solutions: any[];
	final_solutions: any[];
	preferences: number[][];
}

/**
 * Transforms full iterations data into organized history data, giving all solutions iteration numbers
 */
export function computeHistory(
	full_iterations: AllIterations,
	userId: number | undefined,
	isDecisionMaker: boolean,
	step: string
): HistoryData {
	if (!full_iterations.all_full_iterations || !userId) {
		return {
			own_solutions: [],
			common_solutions: [],
			preferences: [],
			final_solutions: []
		};
	}
	const arrayLength = full_iterations.all_full_iterations.length;

	// TODO: isDecisionmaker means that personal_result_index !== null,
	// so maybe to show all to owner, one could remove the isDecisionmaker and instead flatmap with condition that if null, just get all.
	// Transform own solutions with iteration numbers (only if user is decisionMaker and thus has personal results, and user_results exist)
	const own_solutions = isDecisionMaker
		? full_iterations.all_full_iterations.slice(0, arrayLength - 1).map((iteration, index) => {
				const iterationNumber = arrayLength - 1 - index; // Count backwards to get iteration number
				if (iteration.phase === 'decision' || iteration.phase === 'compromise') {
					return {
						undefined,
						iteration_number: iterationNumber
					};
				}
				return iteration.user_results && iteration.user_results.length > 0
					? {
							...iteration.user_results[iteration.personal_result_index || 0],
							iteration_number: iterationNumber
						}
					: {
							undefined,
							iteration_number: iterationNumber
						};
			})
		: full_iterations.all_full_iterations.slice(0, arrayLength - 1).flatMap((iteration, index) => {
				const iterationNumber = arrayLength - 1 - index; // Count backwards to get iteration number
				return (iteration.user_results ?? []).map((solution) => ({
					...solution,
					iteration_number: iterationNumber
				}));
			});

	// Transform common solutions with iteration numbers
	const common_solutions = full_iterations.all_full_iterations // Iteration should always have common results, at least []. No need to filter.
		.flatMap((iteration, index) => {
			const iterationNumber = arrayLength - 1 - index; // Count backwards to get iteration number
			return (iteration.common_results ?? []).map((solution) => ({
				...solution,
				iteration_number: iterationNumber
			}));
		});

	const final_solutions = full_iterations.all_full_iterations
		.filter((_, index) => {
			if (step === 'voting') return index !== 0;
			return true;
		}) // filters the first if step is voting; in this case there is no final solution in that iteration.
		.map((iteration, index) => {
			const iterationNumber = arrayLength - 1 - index; // Count backwards to get iteration number
			return {
				...iteration.final_result,
				iteration_number: step === 'voting' ? iterationNumber - 1 : iterationNumber // if the first one is removed, array is shorter so index is one less
			};
		});

	// Extract preferences history TODO: is no dm, can return all?
	const preferences = extractPreferencesHistory(isDecisionMaker, full_iterations, userId);

	return {
		own_solutions,
		common_solutions,
		preferences,
		final_solutions
	};
}

/**
 * Extracts preferences history for a specific user
 */
function extractPreferencesHistory(
	isDecisionMaker: boolean,
	full_iterations: AllIterations,
	userId: number
): number[][] {
	const set_preferences = full_iterations.all_full_iterations
		.slice(0, full_iterations.all_full_iterations.length - 1) // Exclude initial iteration as it has no preferences
		.map((iteration) => iteration.optimization_preferences?.set_preferences);

	if (!isDecisionMaker) {
		// Extract preferences from ALL users across all iterations
		const preferences = set_preferences.flatMap((iterationPrefs) => {
			if (!iterationPrefs) return [];
			// Get all users' preferences for this iteration
			return Object.values(iterationPrefs).map((userPrefs) =>
				Object.values(userPrefs.aspiration_levels)
			);
		});

		return preferences;
	}

	// Extract preferences only for the specific user (decision maker)
	const preferences = set_preferences
		.map((data) => {
			if (data) {
				return Object.values(data[userId].aspiration_levels);
			}
		})
		.filter((vals): vals is number[] => vals !== null && vals !== undefined);

	return preferences;
}

/**
 * Gets solutions based on view mode and current state
 * This replaces the complex solution_options derived logic
 */
export function getSolutionsForView(
	historyData: HistoryData,
	current_state: any,
	history_option: 'current' | 'all_own' | 'all_group' | 'all_final',
	step: string
): Solution[] {
	if (!current_state) return [];

	// History modes
	if (history_option === 'all_group') {
		return historyData.common_solutions;
	}
	if (history_option === 'all_own') {
		return historyData.own_solutions;
	}
	if (history_option === 'all_final') {
		return historyData.final_solutions;
	}

	// Current iteration mode
	switch (step) {
		case 'optimization':
			return current_state.final_result?.objective_values ? [current_state.final_result] : [];
		case 'voting':
			return current_state.common_results ?? [];
		case 'finish':
			return current_state.common_results ?? [];
		default:
			return [];
	}
}

/**
 * Gets the appropriate preference values for a given index
 */
export function getChosenPreference(preferences: number[][], selectedIndex: number): number[] {
	return preferences[selectedIndex] || [];
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
			console.log(status);
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
