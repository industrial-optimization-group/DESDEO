<script lang="ts">
	/**
	 * +page.svelte (NIMBUS method)
	 *
	 * @author Stina (Functionality) <palomakistina@gmail.com>
	 * @author Giomara Larraga (Base structure)<glarragw@jyu.fi>
	 * @created July 2025
	 *
	 * @description
	 * This page implements the NIMBUS interactive multiobjective optimization method in DESDEO.
	 * It displays a sidebar with problem information, a solution explorer with a combobox to select solution types,
	 * and a resizable pane layout for visualizing the objective and decision spaces, as well as solution tables.
	 *
	 * The implementation supports three main modes:
	 * - Iterate: For viewing and selecting preferences for solutions, and iterating to find new solutions
	 * - Intermediate: For generating new solutions between two selected solutions
	 * - Final: For displaying the final selected solution
	 *
	 * @props
	 * @property {Object} data - Contains a list of optimization problems fetched from the server.
	 * @property {ProblemInfo[]} data.problems - List of problems.
	 *
	 * @features
	 * - Sidebar with problem information and preference types.
	 * - Toggle between iteration and intermediate solution modes.
	 * - Solution explorer with a combobox to select between "Current", "Best", and "All" solutions.
	 * - Responsive, resizable layout with visualization panels.
	 * - Visualization of objective space and decision space (map for problems with utopia metadata).
	 * - Solution tables with saving, renaming, and removing functionality. TODO: removing request
	 * - Support for intermediate solution generation between two selected solutions.
	 * - Final solution selection and confirmation. TODO: actual http request
	 *
	 * @dependencies
	 * - BaseLayout: Layout component for the method view.
	 * - AppSidebar: Sidebar component for preferences and problem info.
	 * - IntermediateSidebar: Sidebar for intermediate solution generation.
	 * - SolutionTable: Table component for displaying solutions.
	 * - VisualizationsPanel: Component for displaying objective space visualizations.
	 * - UtopiaMap: Component for displaying maps (for problems with utopia metadata).
	 * - SegmentedControl: For mode selection UI.
	 * - Combobox: For solution type selection.
	 * - Button: UI component for actions like finishing.
	 * - ConfirmationDialog: For confirming actions.
	 * - InputDialog: For renaming saved solutions.
	 * - methodSelection: Svelte store for the currently selected problem.
	 *
	 * @notes
	 * - The selected problem is determined from the methodSelection store.
	 * - Maps are only displayed for problems with utopia metadata.
	 * - Helper functions are imported from 'helper-functions.ts' for common operations.
	 * - State is managed using Svelte's reactive $state and $derived declarations.
	 *
	 * @modes
	 * 1. Iterate Mode:
	 *    - Default mode when starting NIMBUS method
	 *    - Shows preferences sidebar with classification UI
	 *    - Allows user to set preferences and iterate to new solutions
	 *    - Displays solution table with current, saved, or all solutions
	 *
	 * 2. Intermediate Mode:
	 *    - Allows selecting exactly two solutions to generate intermediate solutions between them
	 *    - Shows intermediate sidebar UI for selecting number of solutions to generate
	 *    - Displays solution table with current, saved, or all solutions
	 *
	 * 3. Final Mode:
	 *    - Displayed after the user selects a final solution
	 *    - Shows a simplified layout focused on the chosen solution
	 *    - Removes sidebar and controls, presenting just the final results
	 */
	// Layout and core components
	import { BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import { methodSelection } from '../../../stores/methodSelection';
	import type { components } from '$lib/api/client-types';
	import { onMount } from 'svelte';

	// UI Components
	import { Combobox } from '$lib/components/ui/combobox';
	import { SegmentedControl } from '$lib/components/custom/segmented-control';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import ResizableHandle from '$lib/components/ui/resizable/resizable-handle.svelte';
	import Button from '$lib/components/ui/button/button.svelte';

	// Dialog Components
	import ConfirmationDialog from '$lib/components/custom/confirmation-dialog.svelte';
	import InputDialog from '$lib/components/custom/input-dialog.svelte';

	// NIMBUS specific components
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import IntermediateSidebar from '$lib/components/custom/nimbus/intermediate-sidebar.svelte';
	import SolutionTable from '$lib/components/custom/nimbus/solution-table.svelte';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';
	import UtopiaMap from '$lib/components/custom/nimbus/utopia-map.svelte';
	import { PREFERENCE_TYPES } from '$lib/constants';

	// Utility functions
	import {
		checkUtopiaMetadata,
		mapSolutionsToObjectiveValues,
		updatePreferencesFromState,
		validateIterationAllowed,
		callNimbusAPI,
		processPreviousObjectiveValues,
		updateSolutionNames
	} from './helper-functions';
	import { writable } from 'svelte/store';
	type ProblemInfo = components['schemas']['ProblemInfo'];
	// Define a general type combining all three responses that NIMBUS can return
	type Solution = components['schemas']['SolutionReferenceResponse'];
	type Response = {
		state_id: number | null;
		previous_preference?: components['schemas']['ReferencePoint'];
		previous_objectives?: {
			[key: string]: number;
		};
		reference_solution_1?: {
			[key: string]: number;
		};
		reference_solution_2?: {
			[key: string]: number;
		};
		current_solutions: Solution[];
		saved_solutions: Solution[];
		all_solutions: Solution[];
	};

	// State for NIMBUS iteration management
	let current_state: Response = $state({} as Response);

	let problem: ProblemInfo | null = $state(null);
	const { data } = $props<{ data: ProblemInfo[] }>();
	let problem_list = data.problems ?? [];
	// user can choose from three types of solutions: current, best, or all
	let selected_type_solutions = $state('current');
	const frameworks = [
		{ value: 'current', label: 'Current solutions' },
		{ value: 'best', label: 'Best candidate solutions' },
		{ value: 'all', label: 'All solutions' }
	];

	let chosen_solutions = $derived.by(() => {
		if (!current_state) return [];

		switch (selected_type_solutions) {
			case 'current':
				return current_state.current_solutions || [];
			case 'best':
				return current_state.saved_solutions || [];
			case 'all':
				return current_state.all_solutions || [];
			default:
				return current_state.current_solutions || [];
		}
	});

	// Get the label for the selected solution type from frameworks
	let selected_type_solutions_label = $derived.by(() => {
		const framework = frameworks.find((f) => f.value === selected_type_solutions);
		return framework ? framework.label : 'Solutions';
	});
	// variables for handling different modes (iteration, intermediate, save, finish)
	// and chosen solutions that are separate for every mode
	let mode: 'iterate' | 'final' | 'intermediate' = $state('iterate');
	// iteration mode
	let selected_iteration_index: number[] = $state([0]); // Index of solution from previous results to use in sidebar. List for consistency, but always has one element
	let current_num_iteration_solutions: number = $state(1); // how many solutions user wants when making the iteration
	let selected_iteration_objectives: Record<string, number> = $state({}); // actual objectives of the selected solution in iteration mode
	// intermediate mode
	let selected_intermediate_indexes: number[] = $state([]);
	let current_num_intermediate_solutions: number = $state(1);
	let selected_solutions_for_intermediate: Solution[] = $state([]); // actual objectives, but it is a list unlike for iteration, since user should choose two solutions

	// Reactive variable for selected indexes based on current mode
	let selectedIndexes = $derived.by(() => {
		if (mode === 'intermediate') {
			return selected_intermediate_indexes;
		} else {
			// Both "iterate" and "final" modes use the same index list
			return selected_iteration_index;
		}
	});
	// currentPreference is initialized from previous preference or ideal values
	let current_preference: number[] = $state([]);
	// Store the last iterated preference values to show as "previous" in UI
	let last_iterated_preference: number[] = $state([]);

	// Variable to track if problem has utopia metadata
	let hasUtopiaMetadata = $state(false);

	// Variables for showing the map for UTOPIA
	type PeriodKey = 'period1' | 'period2' | 'period3';
	let mapOptions = $state<Record<PeriodKey, Record<string, any>>>({
		period1: {},
		period2: {},
		period3: {}
	});
	let yearlist = $state<string[]>([]);
	let selectedPeriod = $state<PeriodKey>('period1');
	let geoJSON = $state<object | undefined>(undefined);
	let mapName = $state<string | undefined>(undefined);
	let mapDescription = $state<string | undefined>(undefined);
	let compensation = $state(0.0);

	// Variables for  for showing that calculations are ongoing
	// svelte-ignore non_reactive_update
	let calculating = $state(false);
	let error: string | null = null;

	// Validation: iteration is allowed when at least one preference is better and one is worse than current objectives
	let is_iteration_allowed = $derived(() => {
		// Use the imported utility function to validate if iteration is allowed
		return validateIterationAllowed(problem, current_preference, selected_iteration_objectives);
	});

	function handle_type_solutions_change(event: { value: string }) {
		change_solution_type_updating_selections(event.value as 'current' | 'best' | 'all');
	}

	// Helper function to change solution type and update selections
	function change_solution_type_updating_selections(newType: 'current' | 'best' | 'all') {
		// Update the internal state
		selected_type_solutions = newType;

		// Then update UI and data
		update_iteration_selection(current_state);
		update_intermediate_selection(current_state);
	}
	function handle_solution_click(index: number) {
		if (mode === 'iterate') {
			if (selected_iteration_index[0] === index) {
				return; // Already selected, do nothing
			}
			// Iterate mode: always select just one solution
			selected_iteration_index = [index];
			update_iteration_selection(current_state);
		} else if (mode === 'intermediate') {
			// Intermediate mode: allow selecting up to 2 rows
			if (selected_intermediate_indexes.includes(index)) {
				// If already selected, deselect it, checking unsaved changes first
				selected_intermediate_indexes = selected_intermediate_indexes.filter((i) => i !== index);
			} else if (selected_intermediate_indexes.length < 2) {
				// Only add if we haven't reached the limit of 2
				selected_intermediate_indexes = [...selected_intermediate_indexes, index];
			}
			update_intermediate_selection(current_state);
		}
	}

	// Dialog state management
	type DialogConfig = {
		open: boolean;
		title: string;
		description: string;
		confirmText: string;
		cancelText: string;
		onConfirm: () => void;
		onCancel?: () => void;
		confirmVariant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
	};

	let dialogConfig = $state<DialogConfig>({
		open: false,
		title: '',
		description: '',
		confirmText: '',
		cancelText: '',
		onConfirm: () => {},
		onCancel: () => {},
		confirmVariant: 'default'
	});

	// Helper function to open the dialog with specific configuration
	function openDialog(config: Partial<DialogConfig>) {
		dialogConfig = {
			...dialogConfig,
			...config,
			open: true
		};
	}

	// Function to handle finishing
	function confirm_finish() {
		// We now only handle the case when exactly one solution is selected
		// The button will be disabled otherwise
		// Get solution name or default to Solution #
		const selectedSolution = chosen_solutions[selectedIndexes[0]];
		const final_solution = { ...selectedSolution }; // Save the actual solution
		const solutionName = selectedSolution.name || `Solution #${selectedIndexes[0] + 1}`;

		openDialog({
			title: 'Confirm Final Choice',
			description: `Are you sure you want to proceed with "${solutionName}" as your final choice?`,
			confirmText: 'Yes, Proceed',
			cancelText: 'Cancel',
			onConfirm: () => handle_finish(final_solution, selectedIndexes[0])
		});
	}
	// TODO: find out if there is an endpoint or some actual functionality needed; now the endpoint is mocked
	async function handle_finish(final_solution: Solution, index: number) {
		interface FinishResponse {
			success: boolean;
		}

		const result = await callNimbusAPI<FinishResponse>('choose', {
			problem_id: problem?.id,
			solution: final_solution
		});

		if (result.success) {
			// Update the selected iteration index to match our final solution
			// This will ensure that in final mode we show the correct solution
			selected_iteration_index = [index];

			// Set mode to final after updating the indexes
			mode = 'final';
		} else {
			console.error('Failed to save final choice:', result.error);
		}
	}

	// Handle intermediate solutions generation
	async function handle_intermediate() {
		// Check if we have exactly 2 solutions selected
		if (selected_solutions_for_intermediate.length !== 2) {
			console.error('Exactly 2 solutions must be selected for intermediate solutions');
			return;
		}

		// Get the two selected solutions
		const solution1 = selected_solutions_for_intermediate[0];
		const solution2 = selected_solutions_for_intermediate[1];

		const result = await callNimbusAPI<Response>('intermediate', {
			problem_id: problem?.id,
			session_id: null, // Using active session
			parent_state_id: null, // No specific parent
			reference_solution_1: solution1,
			reference_solution_2: solution2,
			num_desired: current_num_intermediate_solutions
		});

		if (result.success && result.data) {
			// Update the current state with the intermediate solutions response
			current_state = result.data;

			// Update names from saved solutions (only for all_solutions, current_solutions are new)
			current_state.all_solutions = updateSolutionNames(
				current_state.saved_solutions,
				current_state.all_solutions
			);

			// Switch back to iterate mode after generating intermediate solutions
			mode = 'iterate';
			// Select the first solution by default
			selected_iteration_index = [0];
			// Switch to current solutions view and update UI
			change_solution_type_updating_selections('current');
		} else {
			console.error('Failed to solve intermediate solutions:', result.error);
		}
	}

	// Dialog state for renaming saved solution in input dialog
	let show_rename_dialog: boolean = $state(false);
	let solution_to_rename: Solution | null = $state(null);
	let solution_initial_name: string = $state('');

	function handle_change(solution: Solution): void {
		// Open the input dialog and set the solution to be renamed
		solution_to_rename = solution;
		solution_initial_name = solution.name || '';
		show_rename_dialog = true;
	}

	// Save a solution with an optional name
	// TODO: Handle the situation where there is already very similar solution saved.
	// Should inform user, make it possible for user to compare decision variables and decide if they want so save the new one too.
	// Accuracy of comparison should be display accuracy, because that is what the user sees.
	async function handle_save(solution: Solution, name: string | undefined) {
		// Create a copy of the solution with the name
		const solutionToSave = {
			...solution,
			name: name ?? null
		};

		// save the solution to the server. Endpoint checks if the exact solution is already saved and changes the name.
		interface SaveResponse {
			success: boolean;
		}

		const result = await callNimbusAPI<SaveResponse>('save', {
			problem_id: problem?.id,
			solution_info: [solutionToSave]
		});

		if (result.success) {
			// Update the solution in all lists after it is successfully saved in the backend
			const updateSolutionInList = (list: Solution[]) =>
				list.map((item) =>
					item.state_id === solution.state_id && item.solution_index === solution.solution_index
						? { ...solutionToSave, name: solutionToSave.name ?? null }
						: { ...item, name: item.name ?? null }
				);
			// Check if the solution already exists in saved_solutions
			const existingIndex = current_state.saved_solutions.findIndex(
				(saved) =>
					saved.state_id === solution.state_id && saved.solution_index === solution.solution_index
			);
			let updatedSavedSolutions;
			if (existingIndex !== -1) {
				// If exists in saved, update only the name
				updatedSavedSolutions = [...current_state.saved_solutions];
				updatedSavedSolutions[existingIndex] = {
					...updatedSavedSolutions[existingIndex],
					name: name || null
				};
			} else {
				// Add to saved_solutions
				updatedSavedSolutions = [...current_state.saved_solutions, solutionToSave];
			}

			current_state = {
				...current_state,
				current_solutions: updateSolutionInList(current_state.current_solutions),
				saved_solutions: updatedSavedSolutions,
				all_solutions: updateSolutionInList(current_state.all_solutions)
			};
		} else {
			console.error('Failed to save solution:', result.error);
		}
	}
	// Function to handle removing saved solution with confirmation
	function confirm_remove_saved(solution: Solution) {
		openDialog({
			title: 'Remove Saved Solution',
			description: `Are you sure you want to remove ${solution.name || 'this solution'} from saved solutions?`,
			confirmText: 'Remove',
			cancelText: 'Cancel',
			onConfirm: () => handle_remove_saved(solution)
			// confirmVariant: "destructive" // Use red color for destructive action
		});
	}

	// TODO: endpoint for removing saved solution is not implemented in +server.ts
	// Actual function to remove the saved solution after confirmation
	async function handle_remove_saved(solution: Solution) {
		interface RemoveResponse {
			success: boolean;
		}

		const result = await callNimbusAPI<RemoveResponse>('remove_saved', {
			problem_id: problem?.id,
			solutions: [solution]
		});

		if (result.success) {
			// Remove the solution from saved_solutions
			const updatedSavedSolutions = current_state.saved_solutions.filter(
				(saved) =>
					!(
						saved.state_id === solution.state_id && saved.solution_index === solution.solution_index
					)
			);

			// Update state with removed solution
			current_state = {
				...current_state,
				saved_solutions: updatedSavedSolutions
				// No need to update current_solutions or all_solutions as they should remain unchanged
				// We just need to remove the solution from saved_solutions
			};
		} else {
			console.error('Failed to remove saved solution:', result.error);
		}
	}

	// The optional unused values are kept for compatibility with the AppSidebar component
	async function handle_iterate(data: {
		numSolutions: number;
		typePreferences: string;
		preferenceValues: number[];
		objectiveValues: number[];
	}) {
		if (!problem) {
			console.error('No problem selected');
			return;
		}
		if (current_preference.length === 0) {
			console.error('No preferences set');
			return;
		}
		if (!is_iteration_allowed()) {
			console.error('Iteration not allowed based on current preferences and objectives');
			return;
		}

		const preference = {
			preference_type: 'reference_point',
			aspiration_levels: problem.objectives.reduce(
				(acc, obj, idx) => {
					acc[obj.symbol] = current_preference[idx];
					return acc;
				},
				{} as Record<string, number>
			)
		};

		try {
			calculating = true;
			error = null;

			const result = await callNimbusAPI<Response>(
				'iterate',
				{
					problem_id: problem.id,
					session_id: null,
					parent_state_id: null,
					current_objectives: selected_iteration_objectives,
					num_desired: current_num_iteration_solutions,
					preference
				},
				10000
			);

			if (!result.success || !result.data) {
				error = result.error ?? 'Unknown error';
			} else {
				// Store the preference values that were just used for iteration
				current_state = result.data;

				// Update names from saved solutions (only for all_solutions, current_solutions are new)
				current_state.all_solutions = updateSolutionNames(
					current_state.saved_solutions,
					current_state.all_solutions
				);

				selected_iteration_index = [0];
				// Switch to current solutions view after iteration
				change_solution_type_updating_selections('current');
				update_preferences_from_state(current_state);
				current_num_iteration_solutions = current_state.current_solutions.length;
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Unknown error';
			console.log(error);
		} finally {
			calculating = false;
		}
	}

	// Fetch maps data for UTOPIA visualization for one solution
	async function get_maps(solution: Solution) {
		if (!problem) {
			console.error('No problem selected');
			return;
		}

		// Define the expected return type for the maps API
		interface MapsResponse {
			years: string[];
			options: Record<string, any>;
			map_json: object;
			map_name: string;
			description: string;
			compensation: number;
		}

		const result = await callNimbusAPI<MapsResponse>('get_maps', {
			problem_id: problem.id,
			solution: solution
		});

		if (result.success && result.data) {
			const data = result.data;

			// Update state variables with the fetched data
			yearlist = data.years;

			// Apply the formatter function client-side
			for (let year of yearlist) {
				if (data.options[year].tooltip.formatterEnabled) {
					data.options[year].tooltip.formatter = function (params: any) {
						return `${params.name}`;
					};
				}
			}

			// Assign map options for each period
			mapOptions = {
				period1: data.options[yearlist[0]] || {},
				period2: data.options[yearlist[1]] || {},
				period3: data.options[yearlist[2]] || {}
			} as Record<PeriodKey, Record<string, any>>;

			geoJSON = data.map_json;
			mapName = data.map_name;
			mapDescription = data.description;
			compensation = Math.round(data.compensation * 100) / 100; // TODO: not used anywhere, in old UI only used in one sentence
		} else {
			console.error('Failed to get maps:', result.error);
		}
	}

	// Helper function to update current iteration objectives from the current state
	function update_iteration_selection(state: Response | null) {
		if (!problem) return;
		if (!state) return;

		// Use chosen_solutions instead of hardcoding current_solutions
		if (chosen_solutions.length === 0) return;

		// Make sure the selected index is within bounds of the chosen solutions
		if (selected_iteration_index[0] >= chosen_solutions.length) {
			selected_iteration_index = [0]; // Reset to first solution if out of bounds
		}

		const selectedSolution = chosen_solutions[selected_iteration_index[0]];
		selected_iteration_objectives = selectedSolution.objective_values || {};

		// Only fetch maps if problem has utopia metadata
		if (hasUtopiaMetadata) {
			get_maps(selectedSolution);
		}
	}

	// Helper function to initialize preferences from previous state or ideal values
	function update_preferences_from_state(state: Response | null) {
		if (!problem) return;
		current_preference = updatePreferencesFromState(state, problem);
		last_iterated_preference = [...current_preference];
	}

	// Helper function to update current intermediate objectives from the current state
	function update_intermediate_selection(state: Response | null) {
		if (!problem) return;
		if (!state) return;
		if (chosen_solutions.length === 0) return;

		// Filter selected indexes that are within bounds
		const validIndexes = selected_intermediate_indexes.filter((i) => i < chosen_solutions.length);
		if (validIndexes.length !== selected_intermediate_indexes.length) {
			selected_intermediate_indexes = validIndexes; // Update if any were out of bounds
		}

		selected_solutions_for_intermediate = selected_intermediate_indexes.map(
			(i) => chosen_solutions[i]
		);
	}

	// helper function to check if a solution is saved (exists in savedSolutions)
	function isSaved(solution: Solution): boolean {
		return current_state.saved_solutions.some(
			(saved) =>
				saved.state_id === solution.state_id && saved.solution_index === solution.solution_index
		);
	}

	onMount(async () => {
		if ($methodSelection.selectedProblemId) {
			problem = problem_list.find(
				(p: ProblemInfo) => String(p.id) === String($methodSelection.selectedProblemId)
			);

			if (problem) {
				// Check if problem has utopia metadata (this only needs to be done once)
				// Using the imported utility function
				hasUtopiaMetadata = checkUtopiaMetadata(problem);

				// Initialize NIMBUS state from the API
				await initialize_nimbus_state(problem.id);
			}
		}
	});

	// Initialize NIMBUS state by calling the API endpoint
	async function initialize_nimbus_state(problem_id: number) {
		const result = await callNimbusAPI<Response>('initialize', {
			problem_id: problem_id,
			session_id: null, // Use active session
			parent_state_id: null, // No parent for initialization
			solver: null // Use default solver
		});

		if (result.success && result.data) {
			// Store response data
			current_state = result.data;

			// Update names from saved solutions
			current_state.current_solutions = updateSolutionNames(
				current_state.saved_solutions,
				current_state.current_solutions
			);
			current_state.all_solutions = updateSolutionNames(
				current_state.saved_solutions,
				current_state.all_solutions
			);

			// Initialize other state
			selected_iteration_index = [0];
			update_iteration_selection(current_state);
			update_preferences_from_state(current_state);
			current_num_iteration_solutions = current_state.current_solutions.length;
		} else {
			console.error('NIMBUS initialization failed:', result.error);
		}
	}

	// Convert data to match AppSidebar interface
	let type_preferences = $state(PREFERENCE_TYPES.Classification);

	// Add the missing callback that updates internal state
	// This function is called when the user changes preferences in the AppSidebar
	function handle_preference_change(data: {
		numSolutions: number;
		typePreferences: string;
		preferenceValues: number[];
		objectiveValues: number[];
	}) {
		current_num_iteration_solutions = data.numSolutions;
		type_preferences = data.typePreferences;
		current_preference = [...data.preferenceValues];
	}
</script>

{#if mode === 'final'}
	<BaseLayout showLeftSidebar={false} showRightSidebar={false} bottomPanelTitle="Final Solution">
		{#snippet visualizationArea()}
			{#if problem && selected_iteration_index.length > 0}
				<!-- Resizable layout for visualizations -->
				<div class="h-full">
					<Resizable.PaneGroup direction="horizontal" class="h-full">
						<!-- Left side: VisualizationsPanel with constrained height -->
						<Resizable.Pane defaultSize={65} minSize={40} class="h-full">
							<!-- Visualization panel showing only the final selected solution -->
							<VisualizationsPanel
								{problem}
								previousPreferenceValues={last_iterated_preference}
								previousPreferenceType={type_preferences}
								currentPreferenceValues={current_preference}
								currentPreferenceType={type_preferences}
								solutionsObjectiveValues={problem
									? mapSolutionsToObjectiveValues(
											[chosen_solutions[selected_iteration_index[0]]],
											problem
										)
									: []}
								externalSelectedIndexes={selected_iteration_index}
								onSelectSolution={() => {}}
							/>
						</Resizable.Pane>

						<!-- Right side: Decision space placeholder, only shown for problems with utopia metadata -->
						{#if hasUtopiaMetadata}
							<!-- Resizable handle between panels with custom styling -->
							<ResizableHandle withHandle class="border-l border-gray-200 shadow-sm" />

							<!-- Map visualization -->
							<Resizable.Pane defaultSize={35} minSize={20} class="h-full">
								<UtopiaMap
									{mapOptions}
									bind:selectedPeriod
									{yearlist}
									{geoJSON}
									{mapName}
									{mapDescription}
								/>
							</Resizable.Pane>
						{/if}
					</Resizable.PaneGroup>
				</div>
			{:else}
				<div class="flex h-full items-center justify-center text-gray-500">
					No problem data available for visualization
				</div>
			{/if}
		{/snippet}
		{#snippet numericalValues()}
			{#if problem && chosen_solutions.length > 0 && selected_iteration_index.length > 0}
				<SolutionTable
					{problem}
					solverResults={[chosen_solutions[selected_iteration_index[0]]]}
					{isSaved}
					selectedSolutions={selected_iteration_index}
					{handle_save}
					{handle_change}
					handle_remove_saved={confirm_remove_saved}
					handle_row_click={() => {}}
					isFrozen={true}
				/>
			{/if}
		{/snippet}
	</BaseLayout>
{:else}
	<BaseLayout
		showLeftSidebar={!!problem}
		showRightSidebar={false}
		bottomPanelTitle={selected_type_solutions_label}
	>
		{#snippet leftSidebar()}
			{#if problem && mode === 'iterate'}
				<AppSidebar
					{problem}
					preferenceTypes={[PREFERENCE_TYPES.Classification]}
					showNumSolutions={true}
					numSolutions={current_num_iteration_solutions}
					typePreferences={type_preferences}
					preferenceValues={current_preference}
					objectiveValues={Object.values(selected_iteration_objectives)}
					isIterationAllowed={is_iteration_allowed()}
					isCalculating={calculating}
					minNumSolutions={1}
					maxNumSolutions={4}
					lastIteratedPreference={last_iterated_preference}
					onPreferenceChange={handle_preference_change}
					onIterate={handle_iterate}
					isFinishButton={false}
				/>
			{:else if problem && mode === 'intermediate'}
				<div class="flex flex-col">
					<IntermediateSidebar
						currentSolutions={selected_solutions_for_intermediate}
						bind:numSolutions={current_num_intermediate_solutions}
						minNumSolutions={1}
						maxNumSolutions={4}
						onClick={handle_intermediate}
					/>
				</div>
			{/if}
		{/snippet}

		{#snippet explorerControls()}
			<SegmentedControl
				bind:value={mode}
				options={[
					{ value: 'iterate', label: 'Iterate' },
					{ value: 'intermediate', label: 'Find intermediate' }
				]}
				class="mr-10"
			/>
			<span>View: </span>
			<Combobox
				options={frameworks}
				defaultSelected={selected_type_solutions}
				onChange={handle_type_solutions_change}
			/>

			<span
				class="inline-block"
				title={selectedIndexes.length !== 1
					? 'Please select exactly one solution to finish with it.'
					: 'Select final solution and finish the NIMBUS method with it'}
			>
				<Button
					onclick={selectedIndexes.length === 1 ? confirm_finish : undefined}
					disabled={selectedIndexes.length !== 1}
					variant="destructive"
					class="ml-10"
				>
					Finish
				</Button>
			</span>
		{/snippet}

		{#snippet visualizationArea()}
			{#if problem && current_state}
				<!-- Resizable layout for visualizations side by side -->
				<div class="h-full">
					<Resizable.PaneGroup direction="horizontal" class="h-full">
						<!-- Left side: VisualizationsPanel with constrained height -->
						<Resizable.Pane defaultSize={65} minSize={40} maxSize={80} class="h-full">
							<!-- Visualization panel that adapts to current mode -->
							<VisualizationsPanel
								{problem}
								previousPreferenceValues={last_iterated_preference}
								currentPreferenceValues={current_preference}
								previousPreferenceType={type_preferences}
								currentPreferenceType={type_preferences}
								solutionsObjectiveValues={problem
									? mapSolutionsToObjectiveValues(chosen_solutions, problem)
									: []}
								previousObjectiveValues={selected_type_solutions === 'current'
									? processPreviousObjectiveValues(current_state, problem)
									: []}
								externalSelectedIndexes={selectedIndexes}
								onSelectSolution={handle_solution_click}
							/>
						</Resizable.Pane>

						{#if mode === 'iterate' && hasUtopiaMetadata}
							<!-- Resizable handle between panels -->
							<ResizableHandle withHandle class=" border-4 border-gray-200 shadow-sm" />

							<!-- Right side: Decision space placeholder, for UTOPIA it is a map -->
							<Resizable.Pane defaultSize={35} minSize={20} class="h-full">
								<UtopiaMap
									{mapOptions}
									bind:selectedPeriod
									{yearlist}
									{geoJSON}
									{mapName}
									{mapDescription}
								/>
							</Resizable.Pane>
						{/if}
					</Resizable.PaneGroup>
				</div>
			{:else}
				<div class="flex h-full items-center justify-center text-gray-500">
					No problem data available for visualization
				</div>
			{/if}
		{/snippet}
		{#snippet numericalValues()}
			{#if problem && chosen_solutions.length > 0}
				<SolutionTable
					{problem}
					solverResults={chosen_solutions}
					selectedSolutions={selectedIndexes}
					{handle_save}
					{handle_change}
					handle_remove_saved={confirm_remove_saved}
					handle_row_click={handle_solution_click}
					{isSaved}
					{selected_type_solutions}
					previousObjectiveValues={selected_type_solutions === 'current'
						? problem
							? [
									// Add previous_objectives if it exists
									...(current_state.previous_objectives ? [current_state.previous_objectives] : []),
									// Add reference_solution_1 if it exists
									...(current_state.reference_solution_1
										? [current_state.reference_solution_1]
										: []),
									// Add reference_solution_2 if it exists
									...(current_state.reference_solution_2
										? [current_state.reference_solution_2]
										: [])
								]
							: []
						: []}
				/>
			{/if}
		{/snippet}
	</BaseLayout>
{/if}

<ConfirmationDialog
	bind:open={dialogConfig.open}
	title={dialogConfig.title}
	description={dialogConfig.description}
	confirmText={dialogConfig.confirmText}
	cancelText={dialogConfig.cancelText}
	onConfirm={dialogConfig.onConfirm}
	onCancel={dialogConfig.onCancel}
	confirmVariant={dialogConfig.confirmVariant}
/>

<InputDialog
	bind:open={show_rename_dialog}
	title="Rename Solution"
	description="Enter a name for this solution."
	confirmText="Save"
	cancelText="Cancel"
	initialValue={solution_initial_name}
	placeholder="Solution name"
	onConfirm={(name) => {
		if (solution_to_rename) {
			handle_save(solution_to_rename, name);
		}
	}}
	onCancel={() => {
		// Reset the solution to rename
		solution_to_rename = null;
	}}
/>
