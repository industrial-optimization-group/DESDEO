<!--
    EMO Interactive Method Page
    ===========================
    
    @description
    Interactive multi-objective optimization page for the Evolutionary Multi-Objective (EMO) method.
    This page provides an interface for users to iteratively refine their preferences and explore
    solutions in multi-objective optimization problems.
    
    @author Giomara Larraga <glarragw@jyu.fi>
    @created July 2025
    
    @architecture
    ┌─────────────────┬─────────────────────────────────────┬─────────────────┐
    │   Preferences   │           Main Content              │   Advanced      │
    │    Sidebar      │                                     │    Sidebar      │
    │                 │  ┌─────────────────────────────────┐ │                 │
    │ - Problem Info  │  │        Solution Explorer        │ │ - Settings      │
    │ - Preference    │  │                                 │ │ - Export        │
    │   Types         │  │ ┌─────────────────────────────┐ │ │ - Explanations  │
    │ - Values        │  │ │      Objective Space        │ │ │                 │
    │ - Actions       │  │ │    (Visualization Area)     │ │ │                 │
    │   (Iterate,     │  │ │                             │ │ │                 │
    │    Finish)      │  │ └─────────────────────────────┘ │ │                 │
    │                 │  ├─────────────────────────────────┤ │                 │
    │                 │  │        Numerical Values         │ │                 │
    │                 │  │   - Current vs Previous         │ │                 │
    │                 │  │   - Detailed Table              │ │                 │
    │                 │  └─────────────────────────────────┘ │                 │
    └─────────────────┴─────────────────────────────────────┴─────────────────┘
    
    @data_flow
    1. User selects problem → Problem loaded from methodSelection store
    2. Default preferences initialized based on problem objectives
    3. User modifies preferences → handlePreferenceChange() called
    4. User clicks "Iterate" → handleIterate() called → Backend optimization
    5. New solutions generated → UI updated with new objective values
    6. User can repeat steps 3-5 or finish the process
    
    @state_management
    - problem: Currently selected optimization problem
    - current_preference: User's current preference settings
    - previous_preference: User's previous preference (for comparison)
    - objective_values: Current objective function values from optimization
    - num_solutions: Number of solutions to generate
    
    @naming_conventions
    - Internal variables/methods: snake_case (e.g., current_preference, handle_change)
    - Public callback methods: camelCase (e.g., handlePreferenceChange, handleIterate)
    - Component props: Match external API naming conventions
-->

<script lang="ts">
	// --- Core Imports ---
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import AdvancedSidebar from '$lib/components/custom/preferences-bar/advanced-sidebar.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import * as Menubar from '$lib/components/ui/menubar/index.js';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import type { components } from '$lib/api/client-types';
	import { onMount } from 'svelte';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { Combobox } from '$lib/components/ui/combobox';
	import { PREFERENCE_TYPES } from '$lib/constants';
	import { formatNumber, formatNumberArray } from '$lib/helpers';

	// --- Type Definitions ---

	/**
	 * Type definition for optimization problem information
	 * Contains objectives, constraints, and problem metadata
	 */
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

	/**
	 * Current objective function values from the optimization process
	 * Updated after each iteration with new solution values
	 */
	let objective_values = $state<number[]>([]);

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
    - Bottom: Numerical values with comparison tables
-->
<div class="flex min-h-[calc(100vh-3rem)]">
	<!-- Left Sidebar: Preferences and Controls -->
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

	<!-- Main Content Area -->
	<div class="flex-1">
		<Resizable.PaneGroup direction="vertical">
			<!-- Top Panel: Solution Explorer -->
			<Resizable.Pane class="p-2">
				<div class="flex-row">
					<!-- Solution Explorer Header -->
					<div class="flex flex-row items-center justify-between gap-4 pb-2">
						<div class="font-semibold">Solution explorer</div>
						<div>
							<span>View: </span>
							<Combobox
								options={type_solutions_to_visualize}
								defaultSelected={selected_type_solutions}
								onChange={handle_change}
							/>
						</div>
					</div>

					<!-- Debug Information Panel -->
					<!-- Shows current state for development/debugging purposes -->
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

					<!-- Main Visualization Area -->
					<div class="h-full w-full">
						<div class="grid h-full w-full gap-4 xl:grid-cols-1">
							<div class="min-h-[50rem] flex-1 rounded bg-gray-100 p-4">
								<span>Objective space</span>
								<!-- TODO: Add parallel coordinates visualization -->
								<!-- TODO: Add scatter plot matrix -->
								<!-- TODO: Add other multi-objective visualization components -->
							</div>
						</div>
					</div>
				</div>
			</Resizable.Pane>

			<!-- Resizable Handle -->
			<Resizable.Handle />

			<!-- Bottom Panel: Numerical Values and Tables -->
			<Resizable.Pane class="p-2">
				<Tabs.Root value="numerical-values">
					<Tabs.List>
						<Tabs.Trigger value="numerical-values">Numerical values</Tabs.Trigger>
						<Tabs.Trigger value="saved-solutions">Saved solutions</Tabs.Trigger>
					</Tabs.List>

					<!-- Numerical Values Tab -->
					<Tabs.Content value="numerical-values">
						<div class="space-y-4">
							<div>Table of solutions</div>

							<!-- Preference Comparison Cards -->
							<!-- Shows side-by-side comparison of current vs previous preferences -->
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
							<!-- Provides objective-by-objective breakdown of all values -->
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
					</Tabs.Content>

					<!-- Saved Solutions Tab -->
					<Tabs.Content value="saved-solutions">
						<!-- TODO: Implement saved solutions functionality -->
						<!-- This should show previously saved solution sets -->
						Visualize saved solutions
					</Tabs.Content>
				</Tabs.Root>
			</Resizable.Pane>
		</Resizable.PaneGroup>
	</div>

	<!-- Right Sidebar: Advanced Settings -->
	<AdvancedSidebar />
</div>
