<!--
    Interactive EMO Method Page
    ===========================
    
    @description
    Interactive Evolutionary Multi-Objective (EMO) methods interface.
    This page provides an interface for EMO methods from the DESDEO framework.
	The method being used (NSGA-III or RVEA) can be modified in the backend code. 
	In the future, we plan to let an analyst select the method from the UI.

    @author Giomara Larraga <glarragw@jyu.fi>
    @created July 2025
    
    @dependencies
    - BaseLayout: Main layout component with snippet-based architecture
    - AppSidebar: Preferences and controls sidebar
    - AdvancedSidebar: Sidebar with explanations and advanced settings
    - Combobox: Solution visualization type selector
     
    @preference_types
    Supported preference types:
    - ReferencePoint: Desirable values for each objective
    - PreferredRange: Acceptable ranges for each objective
    - PreferredSolution: Specific solution as preference

    @todo_items
    1. Add visualizations for the objective space.
       - Add parallel coordinates plot and bar charts.

    2. Backend Integration:
       - Replace simulation in _update_from_optimization_procedure with real API calls
       - Implement proper error handling for network requests
       - Add loading states during optimization
    
    3. Saved Solutions:
       - Implement solution saving/loading functionality
       - Add solution comparison features
-->

<script lang="ts">
	import { BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import AdvancedSidebar from '$lib/components/custom/preferences-bar/advanced-sidebar.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import type { components } from '$lib/api/client-types';
	import { onMount } from 'svelte';
	import { Combobox } from '$lib/components/ui/combobox';
	import { PREFERENCE_TYPES } from '$lib/constants';
	import { formatNumber, formatNumberArray } from '$lib/helpers';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';

	type ProblemInfo = components['schemas']['ProblemInfo'];

	/**
	 * Type definition for preference values
	 * Maps to the available preference types in the system
	 */
	type PreferenceValue = (typeof PREFERENCE_TYPES)[keyof typeof PREFERENCE_TYPES];

	/**
	 * Interface for preference objects
	 * Combines preference type with corresponding numerical values
	 */
	interface Preference {
		type: PreferenceValue; // Type of preference (ReferencePoint, PreferredRange, etc.)
		values: number[]; // Numerical values for the preference
	}

	// --- Component Props ---

	/**
	 * Page data containing available optimization problems
	 * Passed from the page loader function
	 */
	const { data } = $props<{ data: ProblemInfo[] }>();

	// --- State Variables ---

	/**
	 * Currently selected optimization problem
	 * null if no problem is selected or available
	 */
	let problem: ProblemInfo | null = $state(null);

	/**
	 * List of available optimization problems
	 * Extracted from the page data, with fallback to empty array
	 */
	let problem_list = data.problems ?? [];

	/**
	 * Selected type of solutions to visualize
	 * Options: 'current', 'best', 'all'
	 */
	let selected_type_solutions = $state('current');

	/**
	 * Number of solutions to generate in each iteration
	 * Controls the size of the solution set returned by the optimizer
	 */
	let num_solutions = $state(1);
	// Change these to store arrays of solutions instead of single values
	let solutions_objective_values = $state<number[][]>([]); // Array of objective value arrays
	let solutions_decision_values = $state<number[][]>([]); // Array of decision variable arrays
	let objective_values = $state<number[]>([]); // Keep this for current/selected solution

	let emo_method = $state('NSGA3'); // or "RVEA"
	let max_evaluations = $state(1000);
	let use_archive = $state(true);

	/**
	 * User's previous preference configuration
	 * Stored for comparison and rollback purposes
	 */
	let previous_preference = $state<Preference>({
		type: PREFERENCE_TYPES.ReferencePoint,
		values: []
	});

	/**
	 * User's current preference configuration
	 * Active preference used for the next optimization iteration
	 */
	let current_preference = $state<Preference>({
		type: PREFERENCE_TYPES.ReferencePoint,
		values: []
	});

	// --- Constants ---

	/**
	 * Available options for solution visualization
	 * Determines which subset of solutions to display
	 */
	const type_solutions_to_visualize = [
		{ value: 'current', label: 'Current solutions' }, // Solutions from latest iteration
		{ value: 'best', label: 'Best solutions' }, // Pareto-optimal solutions
		{ value: 'all', label: 'All solutions' } // All generated solutions
	];

	// --- Internal Event Handlers ---

	/**
	 * Handles changes in the solution visualization type
	 * Updates the selected type and logs the change
	 *
	 * @param event - Event object containing the selected value
	 * @param event.value - The newly selected visualization type
	 */
	function handle_change(event: { value: string }) {
		selected_type_solutions = event.value;
		console.log('Selected type of solutions:', selected_type_solutions);
	}

	// --- Public Callback Methods (Called by Child Components) ---

	/**
	 * Handles preference changes from the sidebar component
	 * Updates the current preference state without triggering optimization
	 * This is called when users modify preference values in real-time
	 *
	 * @param data - Preference data from the sidebar
	 * @param data.num_solutions - Number of solutions to generate
	 * @param data.type_preferences - Type of preference (ReferencePoint, etc.)
	 * @param data.preference_values - Numerical preference values
	 * @param data.objective_values - Current objective function values
	 */
	function handlePreferenceChange(data: {
		num_solutions: number;
		type_preferences: PreferenceValue;
		preference_values: number[];
		objective_values: number[];
	}) {
		// Update internal state with new preference data
		num_solutions = data.num_solutions;
		objective_values = [...data.objective_values];

		// Update current preference configuration
		current_preference = {
			type: data.type_preferences,
			values: [...data.preference_values]
		};

		// Log the preference change for debugging
		console.log('Preference changed:', {
			num_solutions,
			current_preference: {
				type: current_preference.type,
				values: formatNumberArray(current_preference.values)
			},
			previous_preference: {
				type: previous_preference.type,
				values: formatNumberArray(previous_preference.values)
			},
			objective_values: formatNumberArray(objective_values)
		});
	}

	/**
	 * Handles the iteration request from the sidebar
	 * Triggers a new optimization iteration with current preferences
	 * This is the main optimization workflow trigger
	 *
	 * @param data - Current preference data for optimization
	 * @param data.num_solutions - Number of solutions to generate
	 * @param data.type_preferences - Type of preference for optimization
	 * @param data.preference_values - Preference values to guide optimization
	 * @param data.objective_values - Current objective values
	 */
	function handleIterate(data: {
		num_solutions: number;
		type_preferences: PreferenceValue;
		preference_values: number[];
		objective_values: number[];
	}) {
		console.log('Iterate clicked with data:', {
			num_solutions: data.num_solutions,
			type_preferences: data.type_preferences,
			preference_values: formatNumberArray(data.preference_values),
			objective_values: formatNumberArray(data.objective_values)
		});

		// Store current preference as previous before updating
		// This enables comparison and potential rollback
		previous_preference = {
			type: current_preference.type,
			values: [...current_preference.values]
		};

		// Trigger the optimization process with current preferences
		_update_from_optimization_procedure(data);
	}

	type EMOSolveRequest = components['schemas']['EMOSolveRequest'];
	type ReferencePoint = components['schemas']['ReferencePoint'];

	async function updateFromOptimizationProcedure(data: {
		num_solutions: number;
		type_preferences: PreferenceValue;
		preference_values: number[];
		objective_values: number[];
	}) {
		try {
			console.log('Starting EMO solve with data:', data);

			if (!problem?.id) {
				throw new Error('No problem ID available');
			}

			// Create the aspiration_levels object
			const aspiration_levels: { [key: string]: number } = {};

			if (problem.objectives && data.preference_values) {
				problem.objectives.forEach((objective, index) => {
					if (index < data.preference_values.length) {
						// Use the format from the test: "f_1_min", "f_2_min", etc.
						const key = `f_${index + 1}_min`;
						aspiration_levels[key] = data.preference_values[index];
					}
				});
			}

			console.log('Created aspiration_levels:', aspiration_levels);

			const preference: ReferencePoint = {
				preference_type: 'reference_point',
				aspiration_levels: aspiration_levels
			};

			const solveRequest: EMOSolveRequest = {
				problem_id: problem.id,
				method: emo_method,
				preference: preference,
				max_evaluations: max_evaluations,
				number_of_vectors: data.num_solutions,
				use_archive: use_archive,
				session_id: null,
				parent_state_id: null
			};

			console.log('Final solve request:', JSON.stringify(solveRequest, null, 2));

			// Call the solve endpoint
			const response = await fetch('/interactive_methods/EMO/solve', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				credentials: 'include',
				body: JSON.stringify(solveRequest)
			});

			console.log('Response status:', response.status);
			console.log('Response headers:', Object.fromEntries(response.headers.entries()));

			if (!response.ok) {
				const errorData = await response.json();
				console.error('Error response data:', errorData);
				throw new Error(
					`HTTP error! status: ${response.status}, message: ${errorData.error || 'Unknown error'}, details: ${errorData.details || 'No details'}`
				);
			}

			const result = await response.json();
			console.log('Success response:', result);

			if (result.success && result.data) {
				const emoState = result.data; // This is EMOState type
				console.log('EMO solve response:', emoState);

				// Extract ALL solutions and their objective values
				if (
					emoState.solutions &&
					emoState.solutions.length > 0 &&
					emoState.outputs &&
					emoState.outputs.length > 0
				) {
					// Clear previous solutions
					solutions_objective_values = [];
					solutions_decision_values = [];

					// Process each solution
					emoState.solutions.forEach((solution: number[], solutionIndex: number) => {
						// Extract decision variables (solution variables)
						if (Array.isArray(solution)) {
							solutions_decision_values.push([...solution]);
						} else if (typeof solution === 'object') {
							// If solution is an object, convert to array
							const decisionVars = Object.values(solution).filter(
								(val) => typeof val === 'number'
							) as number[];
							solutions_decision_values.push(decisionVars);
						}

						// Extract corresponding objective values
						if (emoState.outputs[solutionIndex]) {
							const output = emoState.outputs[solutionIndex];
							const objectiveVals: number[] = [];

							if (problem?.objectives) {
								// Use objective names to extract values in correct order
								problem.objectives.forEach((objective) => {
									if (output[objective.name] !== undefined) {
										objectiveVals.push(output[objective.name]);
									}
								});
							} else {
								// Fallback: use all numeric values from output
								Object.values(output).forEach((val) => {
									if (typeof val === 'number') {
										objectiveVals.push(val);
									}
								});
							}

							if (objectiveVals.length > 0) {
								solutions_objective_values.push(objectiveVals);
							}
						}
					});

					// Update the current objective values with the first solution (or best solution)
					if (solutions_objective_values.length > 0) {
						objective_values = [...solutions_objective_values[0]];
					}

					console.log('Extracted solutions:', {
						numSolutions: solutions_objective_values.length,
						objectiveValues: solutions_objective_values,
						decisionValues: solutions_decision_values,
						currentObjective: objective_values
					});
				}

				// Update number of solutions if provided
				if (emoState.number_of_vectors) {
					num_solutions = emoState.number_of_vectors;
				}

				console.log('Updated from EMO solve:', {
					num_solutions,
					total_solutions: solutions_objective_values.length,
					previous_preference: {
						type: previous_preference.type,
						values: formatNumberArray(previous_preference.values)
					},
					current_preference: {
						type: current_preference.type,
						values: formatNumberArray(current_preference.values)
					},
					objective_values: formatNumberArray(objective_values)
				});
			} else {
				console.error('EMO solve failed:', result.error || 'Unknown error');
				throw new Error(result.error || 'EMO solve failed');
			}
		} catch (error) {
			console.error('Error calling EMO solve:', error);
			alert(`Error solving problem: ${error}`);
		}
	}

	/**
	 * Handles the finish request from the sidebar
	 * Completes the optimization process and stores final results
	 *
	 * @param data - Final preference data
	 * @param data.num_solutions - Final number of solutions
	 * @param data.type_preferences - Final preference type
	 * @param data.preference_values - Final preference values
	 * @param data.objective_values - Final objective values
	 */
	function handleFinish(data: {
		num_solutions: number;
		type_preferences: PreferenceValue;
		preference_values: number[];
		objective_values: number[];
	}) {
		console.log('Finish clicked with data:', {
			num_solutions: data.num_solutions,
			type_preferences: data.type_preferences,
			preference_values: formatNumberArray(data.preference_values),
			objective_values: formatNumberArray(data.objective_values)
		});

		// Store final result as previous preference for history
		previous_preference = {
			type: current_preference.type,
			values: [...current_preference.values]
		};

		// Log final optimization results
		console.log('Final preferences:', {
			previous_preference: {
				type: previous_preference.type,
				values: formatNumberArray(previous_preference.values)
			},
			current_preference: {
				type: current_preference.type,
				values: formatNumberArray(current_preference.values)
			},
			objective_values: formatNumberArray(objective_values)
		});

		// TODO: Save results to backend/database
		// TODO: Navigate to results page or show completion dialog
	}

	// --- Private Internal Methods ---

	/**
	 * Updates state with results from the optimization procedure
	 * This method interfaces with the backend optimization algorithm
	 * Currently simulates optimization results for testing
	 *
	 * @private
	 * @param data - Input data for optimization
	 * @param data.num_solutions - Number of solutions requested
	 * @param data.type_preferences - Preference type for optimization guidance
	 * @param data.preference_values - Preference values for optimization
	 * @param data.objective_values - Current objective values
	 *
	 * @workflow
	 * 1. Call backend optimization service with current preferences
	 * 2. Receive new solution set from optimizer
	 * 3. Update objective_values with new results
	 * 4. Update current_preference if preferences were adjusted
	 * 5. Trigger UI updates through reactive statements
	 */
	function _update_from_optimization_procedure(data: {
		num_solutions: number;
		type_preferences: PreferenceValue;
		preference_values: number[];
		objective_values: number[];
	}) {
		// TODO: Replace simulation with actual backend call
		// Example backend call:
		// const response = await optimizationAPI.iterate({
		//     problemId: problem.id,
		//     preferences: {
		//         type: data.type_preferences,
		//         values: data.preference_values
		//     },
		//     numSolutions: data.num_solutions
		// });

		// SIMULATION: Generate new values that simulate optimization results
		// In real implementation, these values come from the optimization backend
		const simulated_new_objective_values = objective_values.map(
			(val) => val + Math.random() * 0.1 - 0.05 // Small random changes
		);
		const simulated_new_preference_values = current_preference.values.map(
			(val) => val + Math.random() * 0.1 - 0.05 // Small random changes
		);

		// Update state with new optimization results
		objective_values = simulated_new_objective_values;
		current_preference = {
			type: current_preference.type, // Preference type typically stays the same
			values: simulated_new_preference_values
		};

		// Log optimization results for debugging
		console.log('Updated from optimization:', {
			num_solutions, // This value remains unchanged
			previous_preference: {
				type: previous_preference.type,
				values: formatNumberArray(previous_preference.values)
			},
			current_preference: {
				type: current_preference.type,
				values: formatNumberArray(current_preference.values)
			},
			objective_values: formatNumberArray(objective_values)
		});
	}

	/**
	 * Initializes default values when a problem is loaded
	 * Sets up initial preferences based on problem characteristics
	 *
	 * @private
	 * @workflow
	 * 1. Extract ideal values from problem objectives
	 * 2. Use ideal values as initial preference and objective values
	 * 3. Set default preference type to ReferencePoint
	 * 4. Initialize both current and previous preferences identically
	 */
	function _initialize_default_values() {
		if (problem) {
			// Clear previous solutions
			solutions_objective_values = [];
			solutions_decision_values = [];

			// Extract ideal values from problem objectives as defaults
			// Fallback to 0 if ideal value is not specified
			const default_values = problem.objectives.map((obj) =>
				typeof obj.ideal === 'number' ? obj.ideal : 0
			);

			// Initialize objective values with ideal values
			objective_values = [...default_values];

			// Initialize current preference with default values
			current_preference = {
				type: PREFERENCE_TYPES.ReferencePoint,
				values: [...default_values]
			};

			// Initialize previous preference identically
			// (This will be overwritten after first iteration)
			previous_preference = {
				type: PREFERENCE_TYPES.ReferencePoint,
				values: [...default_values]
			};

			console.log('Initialized default values:', {
				problem: problem.name,
				objectives: problem.objectives.length,
				default_values: formatNumberArray(default_values)
			});
		}
	}

	// --- Reactive Effects ---

	/**
	 * Reactive effect: Initialize values when problem changes
	 * Automatically called when the problem state is updated
	 */
	$effect(() => {
		_initialize_default_values();
	});

	// --- Lifecycle Hooks ---

	/**
	 * Component mount lifecycle
	 * Loads the selected problem from the method selection store
	 */
	onMount(() => {
		if ($methodSelection.selectedProblemId) {
			// Find the problem that matches the selected ID
			problem = problem_list.find(
				(p: ProblemInfo) => String(p.id) === String($methodSelection.selectedProblemId)
			);

			if (problem) {
				console.log('Loaded problem:', {
					id: problem.id,
					name: problem.name,
					objectives: problem.objectives.length
				});
			} else {
				console.warn('Problem not found for ID:', $methodSelection.selectedProblemId);
			}
		}
	});
</script>

<!--
    Template Structure
    ==================
    
    Layout: Three-column layout with resizable panels
    - Left: Preferences sidebar (AppSidebar)
    - Center: Main content area with solution explorer and numerical values
    - Right: Advanced settings sidebar (AdvancedSidebar)
    
    The center area is divided vertically into:
    - Top: Solution explorer with visualization area
    - Bottom: Numerical values 
-->
<BaseLayout showLeftSidebar={!!problem} showRightSidebar={true}>
	{#snippet leftSidebar()}
		{#if problem}
			<AppSidebar
				{problem}
				preference_types={[
					PREFERENCE_TYPES.ReferencePoint,
					PREFERENCE_TYPES.PreferredRange,
					PREFERENCE_TYPES.PreferredSolution
				]}
				{num_solutions}
				type_preferences={current_preference.type}
				preference_values={current_preference.values}
				{objective_values}
				showNumSolutions={true}
				onPreferenceChange={handlePreferenceChange}
				onIterate={handleIterate}
				onFinish={handleFinish}
			/>
		{/if}
	{/snippet}

	{#snippet explorerControls()}
		<span>View: </span>
		<Combobox
			options={type_solutions_to_visualize}
			defaultSelected={selected_type_solutions}
			onChange={handle_change}
		/>
	{/snippet}

	{#snippet debugPanel()}
		<div class="mb-4 rounded bg-gray-50 p-2 text-xs">
			<div><strong>Num Solutions:</strong> {num_solutions}</div>
			<div><strong>Objective Values:</strong> {formatNumberArray(objective_values)}</div>
			<div class="mt-2">
				<strong>Current Preference:</strong>
				<div class="ml-2">
					<div>Type: {current_preference.type}</div>
					<div>Values: {formatNumberArray(current_preference.values)}</div>
				</div>
			</div>
			<div class="mt-2">
				<strong>Previous Preference:</strong>
				<div class="ml-2">
					<div>Type: {previous_preference.type}</div>
					<div>Values: {formatNumberArray(previous_preference.values)}</div>
				</div>
			</div>
		</div>
	{/snippet}

	<!-- This container will flex to fill available space -->
	{#snippet visualizationArea()}
		{#if problem}
			<VisualizationsPanel
				{problem}
				previous_preference_values={previous_preference.values}
				previous_preference_type={previous_preference.type}
				current_preference_values={current_preference.values}
				current_preference_type={current_preference.type}
				{solutions_objective_values}
				{solutions_decision_values}
				onSelectSolution={(index) => {
					// Update current objective values when user selects a solution
					if (solutions_objective_values[index]) {
						objective_values = [...solutions_objective_values[index]];
						console.log('Selected solution', index, 'with objectives:', objective_values);
					}
				}}
			/>
		{:else}
			<div class="flex h-full items-center justify-center text-gray-500">
				No problem data available for visualization
			</div>
		{/if}
	{/snippet}
	{#snippet numericalValues()}
		<div class="space-y-4">
			<div>Table of solutions</div>

			<!-- Preference Comparison Cards -->
			<div class="grid grid-cols-2 gap-4">
				<div class="rounded border p-3">
					<h4 class="font-semibold">Current Preference</h4>
					<p class="text-sm text-gray-600">Type: {current_preference.type}</p>
					<p class="text-sm text-gray-600">
						Values: {formatNumberArray(current_preference.values)}
					</p>
				</div>
				<div class="rounded border p-3">
					<h4 class="font-semibold">Previous Preference</h4>
					<p class="text-sm text-gray-600">Type: {previous_preference.type}</p>
					<p class="text-sm text-gray-600">
						Values: {formatNumberArray(previous_preference.values)}
					</p>
				</div>
			</div>

			<!-- Detailed Values Table -->
			<div class="mt-4">
				<h4 class="mb-2 font-semibold">Detailed Values</h4>
				<div class="overflow-x-auto">
					<table class="min-w-full border border-gray-200">
						<thead class="bg-gray-50">
							<tr>
								<th class="border border-gray-200 px-4 py-2 text-left">Objective</th>
								<th class="border border-gray-200 px-4 py-2 text-left">Current Value</th>
								<th class="border border-gray-200 px-4 py-2 text-left">Previous Value</th>
								<th class="border border-gray-200 px-4 py-2 text-left">Objective Value</th>
							</tr>
						</thead>
						<tbody>
							{#if problem}
								{#each problem.objectives as objective, idx}
									<tr class="hover:bg-gray-50">
										<td class="border border-gray-200 px-4 py-2">{objective.name}</td>
										<td class="border border-gray-200 px-4 py-2">
											{formatNumber(current_preference.values[idx] || 0)}
										</td>
										<td class="border border-gray-200 px-4 py-2">
											{formatNumber(previous_preference.values[idx] || 0)}
										</td>
										<td class="border border-gray-200 px-4 py-2">
											{formatNumber(objective_values[idx] || 0)}
										</td>
									</tr>
								{/each}
							{/if}
						</tbody>
					</table>
				</div>
			</div>
		</div>
	{/snippet}

	{#snippet savedSolutions()}
		<!-- TODO: Implement saved solutions functionality -->
		Visualize saved solutions
	{/snippet}

	{#snippet rightSidebar()}
		<AdvancedSidebar />
	{/snippet}
</BaseLayout>
