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
	 * - Solution tables with saving functionality.
	 * - Support for intermediate solution generation between two selected solutions.
	 *
	 * @dependencies
	 * - BaseLayout: Layout component for the method view.
	 * - AppSidebar: Sidebar component for preferences and problem info.
	 * - IntermediateSidebar: Sidebar for intermediate solution generation.
	 * - SolutionTable: Table component for displaying solutions.
	 * - VisualizationsPanel: Component for displaying objective space visualizations.
	 * - UtopiaMap: Component for displaying maps (for problems with utopia metadata).
	 * - ToggleGroup/ToggleGroupItem: For mode selection UI.
	 * - ConfirmationDialog: For confirming actions with unsaved changes.
	 * - methodSelection: Svelte store for the currently selected problem.
	 *
	 * @notes
	 * - The selected problem is determined from the methodSelection store.
	 * - Maps are only displayed for problems with utopia metadata.
	 */
	import { BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import type { components } from '$lib/api/client-types';
	import { onMount } from 'svelte';
	import { Combobox } from '$lib/components/ui/combobox';

	import IntermediateSidebar from '$lib/components/custom/nimbus/intermediate-sidebar.svelte';
	import { ToggleGroup, ToggleGroupItem } from '$lib/components/ui/toggle-group';

	import ConfirmationDialog from '$lib/components/custom/confirmation-dialog.svelte';
	import SolutionTable from '$lib/components/custom/nimbus/solution-table.svelte';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';

	import { PREFERENCE_TYPES } from '$lib/constants';
	import UtopiaMap from '$lib/components/custom/nimbus/utopia-map.svelte';
	
	// Import utility functions
	import { 
		checkUtopiaMetadata,
		mapSolutionsToObjectiveValues,
		updatePreferencesFromState,
		validateIterationAllowed,
		callNimbusAPI
	} from './helper-functions';	
	type ProblemInfo = components['schemas']['ProblemInfo'];
	// Define a general type combining all three responses that NIMBUS can return
	// TODO: NIMBUSIntermediateResponse is in the making
	type Solution = components['schemas']['UserSavedSolutionAddress'];
	type NIMBUSClassificationResponse = components['schemas']['NIMBUSClassificationResponse'];
	type NIMBUSInitializationResponse = components['schemas']['NIMBUSInitializationResponse'];
	type IntermediateSolutionResponse = components['schemas']['IntermediateSolutionResponse'];
	type BaseResponse = NIMBUSClassificationResponse | NIMBUSInitializationResponse | IntermediateSolutionResponse;
	type Response = BaseResponse &{
		current_solutions: Solution[],
		saved_solutions: Solution[],
		all_solutions: Solution[],
	};

	// State for NIMBUS iteration management
	let current_state: Response = $state({} as Response);
	
	let problem: ProblemInfo | null = $state(null);
	const { data } = $props<{ data: ProblemInfo[] }>();
	let problem_list = data.problems ?? [];
	// user can choose from three types of solutions: current, best, or all
	let selected_type_solutions = $state('current');
	
	// variables for handling different modes (iteration, intermediate, save, finish)
	// and chosen solutions that are separate for every mode
	let mode: "iterate" | "final" | "intermediate" = $state("iterate");
	// iteration mode
	let selected_iteration_index: number[] = $state([0]); // Index of solution from previous results to use in sidebar. List for consistency, but always has one element
	let current_num_iteration_solutions: number = $state(1); // how many solutions user wants when making the iteration
	let selected_iteration_objectives: Record<string, number> = $state({}); // actual objectives of the selected solution in iteration mode
	// intermediate mode
	let selected_intermediate_indexes: number[] = $state([]);
	let current_num_intermediate_solutions: number = $state(1);
	let selected_solutions_for_intermediate: Solution[] = $state([]); // actual objectives, but it is a list unlike for iteration, since user should choose two solutions

	// Reactive variable for selected indexes based on current mode
	let selectedIndexes = $derived(() => {
		if (mode === "intermediate") {
			return selected_intermediate_indexes;
		} else {
			// Both "iterate" and "final" modes use the same index list
			return selected_iteration_index
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
	let selectedPeriod = $state<PeriodKey>("period1");
	let geoJSON = $state<object | undefined>(undefined);
	let mapName = $state<string | undefined>(undefined);
	let mapDescription = $state<string | undefined>(undefined);
	let compensation = $state(0.0);

	const frameworks = [
		{ value: 'current', label: 'Current solutions' },
		{ value: 'best', label: 'Best solutions' },
		{ value: 'all', label: 'All solutions' }
	];
	
	// Variables for handling unsaved changes confirmation
	let show_save_confirm_dialog: boolean = $state(false);
	let pending_selection_target: number = $state(-1); // Store the target row that was clicked
	let has_unsaved_changes: boolean = $state(false); // Store result from solution table
	
	// Validation: iteration is allowed when at least one preference is better and one is worse than current objectives
	let is_iteration_allowed = $derived(() => {
		// Use the imported utility function to validate if iteration is allowed
		return validateIterationAllowed(problem, current_preference, selected_iteration_objectives);
	})

	function handle_type_solutions_change(event: { value: string }) {
		selected_type_solutions = event.value;
	}
	function handle_solution_click(index: number) {
		// If there are unsaved changes, show confirmation dialog
		if (mode ==="iterate"){
			if(selected_iteration_index[0] === index) {
				return; // Already selected, do nothing
			}
			if (has_unsaved_changes) {
				// Store the target index for use after confirmation
				pending_selection_target = index;
				// Show the confirmation dialog
				show_save_confirm_dialog = true;
				return;
			}
            // Iterate mode: always select just one solution
            selected_iteration_index = [index];
			update_iteration_selection(current_state);
        } else if (mode === "intermediate") {
            // Intermediate mode: allow selecting up to 2 rows
            if (selected_intermediate_indexes.includes(index)) {
                // If already selected, deselect it, checking unsaved changes first
				if (has_unsaved_changes) {
					// Store the target index for use after confirmation
					pending_selection_target = index;
					// Show the confirmation dialog
					show_save_confirm_dialog = true;
					return;
				}
                selected_intermediate_indexes = selected_intermediate_indexes.filter(i => i !== index);
            } else if (selected_intermediate_indexes.length < 2) {
                // Only add if we haven't reached the limit of 2, checking unsaved changes first
				if (has_unsaved_changes) {
					// Store the target index for use after confirmation
					pending_selection_target = index;
					// Show the confirmation dialog
					show_save_confirm_dialog = true;
					return;
				}
                selected_intermediate_indexes = [...selected_intermediate_indexes, index];
            }
			update_intermediate_selection(current_state);
        }
	}
								
	// This function handles the selection change after confirmation dialog
	function handle_solution_click_after_pop_up() {
		// Apply the pending selection if there was one
		if (pending_selection_target >= 0) {
			const index = pending_selection_target;
			
			if (mode === "iterate") {
				selected_iteration_index = [index];
				update_iteration_selection(current_state);
			} else if (mode === "intermediate") {
				// Intermediate mode: allow selecting up to 2 rows
				if (selected_intermediate_indexes.includes(index)) {
					// If already selected, deselect
					selected_intermediate_indexes = selected_intermediate_indexes.filter(i => i !== index);
				} else if (selected_intermediate_indexes.length < 2) {
					// Only add if we haven't reached the limit of 2
					selected_intermediate_indexes = [...selected_intermediate_indexes, index];
				}
				update_intermediate_selection(current_state);
			}
		}
		// Reset pending selection
		pending_selection_target = -1;
	}

	let show_confirm_dialog: boolean = $state(false);
	function handle_press_finish() {
		show_confirm_dialog = true;
	}
	// TODO: find out if there is an endpoint or some actual functionality needed; now the endpoint is mocked
	async function handle_finish() {
		interface FinishResponse {
			success: boolean;
		}
		
		const result = await callNimbusAPI<FinishResponse>('choose', {
			problem_id: problem?.id,
			solution: selected_iteration_index[0]
		});

		if (result.success) {
			mode = "final";
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
			// Switch back to iterate mode after generating intermediate solutions
			mode = "iterate";
			// Select the first solution by default
			selected_iteration_index = [0];
			// Update the UI with the selected solution
			update_iteration_selection(current_state);
		} else {
			console.error('Failed to solve intermediate solutions:', result.error);
		}
	}

	// Save a solution with an optional name
	// TODO: Handle the situation where there is already very similar solution saved. 
	// Should inform user, make it possible for user to compare decision variables and decide if they want so save the new one too.
	// Accuracy of comparison should be display accuracy, because that is what the user sees.
	async function handle_save(solution: Solution, name: string | undefined) {		
		// Create a copy of the solution with the name
		const solutionToSave = {
			...solution,
			name: name
		};
		
		// save the solution to the server. Endpoint checks if the exact solution is already saved and changes the name.
		interface SaveResponse {
			success: boolean;
		}
		
		const result = await callNimbusAPI<SaveResponse>('save', {
			problem_id: problem?.id,
			solutions: [solutionToSave],
		});

		if (result.success) {
			// Update the solution in all lists after it is successfully saved in the backend
			const updateSolutionInList = (list: Solution[]) => 
				list.map(item => 
					(item.address_state === solution.address_state && item.address_result === solution.address_result) 
						? solutionToSave 
						: item
				);
			// Check if the solution already exists in saved_solutions
			const existingIndex = current_state.saved_solutions.findIndex(
				saved => saved.address_state === solution.address_state && saved.address_result === solution.address_result
			);
			let updatedSavedSolutions;
			if (existingIndex !== -1) {
				// If exists in saved, update only the name
				updatedSavedSolutions = [...current_state.saved_solutions];
				updatedSavedSolutions[existingIndex] = {
					...updatedSavedSolutions[existingIndex],
					name: name
				};
			} else {
				// Add to saved_solutions
				updatedSavedSolutions = [...current_state.saved_solutions, solutionToSave];
			}
			
			current_state = {
				...current_state,
				current_solutions: updateSolutionInList(current_state.current_solutions),
				saved_solutions: updatedSavedSolutions,
				all_solutions: updateSolutionInList(current_state.all_solutions),
			};
		} else {
			console.error('Failed to save solution:', result.error);
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

		const result = await callNimbusAPI<Response>('iterate', {
			problem_id: problem.id,
			session_id: null,
			parent_state_id: null,
			current_objectives: selected_iteration_objectives,
			num_desired: current_num_iteration_solutions,
			preference: preference
		});

		if (result.success && result.data) {
			// Store the preference values that were just used for iteration
			last_iterated_preference = [...current_preference];
			current_state = result.data;
			selected_iteration_index = [0];
			update_iteration_selection(current_state);
			current_num_iteration_solutions = current_state.current_solutions.length
		} else {
			console.error('NIMBUS iteration failed:', result.error);
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
		if (!state || !state.current_solutions || state.current_solutions.length === 0) return;
			const selectedSolution = state.current_solutions[selected_iteration_index[0]]; 
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
	}

	// Helper function to update current intermediate objectives from the current state
	function update_intermediate_selection(state: Response | null) {
		if (!problem) return;
		if (!state || !state.current_solutions || state.current_solutions.length === 0) return;
		selected_solutions_for_intermediate = selected_intermediate_indexes.map((i) => state.current_solutions[i]); 
	}

	// helper function to check if a solution is saved (exists in savedSolutions)
	function isSaved(solution: Solution): boolean {
		return current_state.saved_solutions.some(
			saved => saved.address_state === solution.address_state && saved.address_result === solution.address_result
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
			current_state = result.data;
			selected_iteration_index = [0];
			update_iteration_selection(current_state);
			update_preferences_from_state(current_state);
			current_num_iteration_solutions = current_state.current_solutions.length;
			// update names in all current_solutions and all_solutions that are saved
			for (let solution of current_state.current_solutions) {
				const savedIndex = current_state.saved_solutions.findIndex(
					saved => saved.address_state === solution.address_state && saved.address_result === solution.address_result
				);
				if (savedIndex !== -1) {
					// Solution exists in saved_solutions, update the name
					solution.name = current_state.saved_solutions[savedIndex].name;
				}
			}
			for (let solution of current_state.all_solutions) {
				const savedIndex = current_state.saved_solutions.findIndex(
					saved => saved.address_state === solution.address_state && saved.address_result === solution.address_result
				);
				if (savedIndex !== -1) {
					solution.name = current_state.saved_solutions[savedIndex].name;
				}
			}
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

{#if mode === "final"}
	<BaseLayout showLeftSidebar={false} showRightSidebar={false}>
		{#snippet visualizationArea()}
			{#if problem && current_state && current_state.current_solutions && selected_iteration_index.length > 0}
				<!-- Grid layout to place visualizations side by side with fixed height -->
				<div class="flex gap-4 h-full">
					<!-- Left side: VisualizationsPanel with constrained height -->
					<div class="flex-1">
						<!-- Visualization panel showing only the final selected solution -->
						<VisualizationsPanel
							{problem}
							previousPreferenceValues={last_iterated_preference}
							previousPreferenceType={type_preferences}
							currentPreferenceValues={current_preference}
							currentPreferenceType={type_preferences}
							solutionsObjectiveValues={problem ? 
								mapSolutionsToObjectiveValues([current_state.current_solutions[selected_iteration_index[0]]], problem) : []}
							externalSelectedIndexes={selected_iteration_index} 
							onSelectSolution={() => {}}
						/>
					</div>
					<!-- Right side: Decision space placeholder, only shown for problems with utopia metadata -->
					{#if hasUtopiaMetadata}
						<UtopiaMap 
							{mapOptions}
							bind:selectedPeriod={selectedPeriod}
							{yearlist}
							{geoJSON}
							{mapName}
							{mapDescription}
						/>
					{/if}
				</div>
			{:else}
				<div class="flex h-full items-center justify-center text-gray-500">
					No problem data available for visualization
				</div>
			{/if}
		{/snippet}
		{#snippet numericalValues()}
			{#if problem && current_state?.current_solutions && current_state.current_solutions.length > 0 && selected_iteration_index.length > 0}
				<SolutionTable
					{problem}
					solverResults={[current_state.current_solutions[selected_iteration_index[0]]]}
					isSaved={isSaved}
					bind:selectedSolutions={selected_iteration_index}
					handle_save={handle_save}
					handle_row_click={() => {}}
					bind:has_unsaved_changes={has_unsaved_changes}
				/>
			{/if}
		{/snippet}
	</BaseLayout>
{:else}
	<BaseLayout showLeftSidebar={!!problem} showRightSidebar={false}>
		{#snippet leftSidebar()}
			<div class="mt-4">
				<ToggleGroup type="single" bind:value={mode}>
					<ToggleGroupItem value="iterate">Iterate or finish</ToggleGroupItem>
					<ToggleGroupItem value="intermediate">Find intermediate</ToggleGroupItem>
				</ToggleGroup>
			</div>
			{#if problem && mode==="iterate"}
				<AppSidebar
					{problem}
					preferenceTypes={[PREFERENCE_TYPES.Classification]}
					showNumSolutions={true}
					numSolutions={current_num_iteration_solutions}
					typePreferences={type_preferences}
					preferenceValues={current_preference}
					objectiveValues={Object.values(selected_iteration_objectives)}
					isIterationAllowed={is_iteration_allowed()}
					isFinishAllowed={true}
					minNumSolutions={1}
					maxNumSolutions={4}
					lastIteratedPreference={last_iterated_preference}
					onPreferenceChange={handle_preference_change}
					onIterate={handle_iterate}
					onFinish={handle_press_finish}
				/>
			{:else if problem && mode ==="intermediate"}
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
			<span>View: </span>
			<Combobox
				options={frameworks}
				defaultSelected={selected_type_solutions}
				onChange={handle_type_solutions_change}
			/>
		{/snippet}

		{#snippet visualizationArea()}
			{#if problem && current_state && current_state.current_solutions}
				<!-- Grid layout to place visualizations side by side with fixed height -->
				<div class="flex gap-4 h-full">
					<!-- Left side: VisualizationsPanel with constrained height -->
					<div class="flex-1">
						<!-- Visualization panel that adapts to current mode -->
						<VisualizationsPanel
							{problem}
							previousPreferenceValues={last_iterated_preference}
							previousPreferenceType={type_preferences}
							currentPreferenceValues={current_preference}
							currentPreferenceType={type_preferences}
							solutionsObjectiveValues={problem ? mapSolutionsToObjectiveValues(current_state.current_solutions, problem) : []}
							externalSelectedIndexes={selectedIndexes()}
							onSelectSolution={handle_solution_click}
						/>
					</div>
					{#if mode === "iterate" && hasUtopiaMetadata}
					<!-- Right side: Decision space placeholder, for UTOPIA it is a map-->
						<UtopiaMap 
							{mapOptions}
							bind:selectedPeriod={selectedPeriod}
							{yearlist}
							{geoJSON}
							{mapName}
							{mapDescription}
						/>
					{/if}
				</div>
			{:else}
				<div class="flex h-full items-center justify-center text-gray-500">
					No problem data available for visualization
				</div>
			{/if}
		{/snippet}
		{#snippet numericalValues()}
			{#if problem && current_state?.current_solutions && current_state.current_solutions.length > 0}
				{#if mode === "iterate"}
					<SolutionTable
						{problem}
						solverResults={current_state.current_solutions}
						isSaved={isSaved}
						bind:selectedSolutions={selected_iteration_index}
						handle_save={handle_save}
						handle_row_click={handle_solution_click}
						bind:has_unsaved_changes={has_unsaved_changes}
					/>
				{:else if mode === "intermediate"}
					<SolutionTable
						{problem}
						solverResults={current_state.current_solutions}
						isSaved={isSaved}
						bind:selectedSolutions={selected_intermediate_indexes}
						handle_save={handle_save}
						handle_row_click={handle_solution_click}
						bind:has_unsaved_changes={has_unsaved_changes}
					/>
				{/if}
			{/if}
		{/snippet}
	</BaseLayout>
{/if}

<ConfirmationDialog
	bind:open={show_confirm_dialog}
	title="Confirm Final Choice"
	description="Are you sure you want to proceed with this solution as your final choice?"
	confirmText="Yes, Proceed"
	cancelText="Cancel"
	onConfirm={handle_finish}
	onCancel={() => {}}
/>
<ConfirmationDialog
	bind:open={show_save_confirm_dialog}
	title="Unsaved Changes"
	description="You have unsaved changes to solution names. Do you want to discard these changes and select another solution?"
	confirmText="Discard Changes"
	cancelText="Keep Editing"
	onConfirm={handle_solution_click_after_pop_up}
	onCancel={() => {
		// Selection change cancelled, continuing editing
		show_save_confirm_dialog = false;
		// Reset pending selection without making any changes
		pending_selection_target = -1;
	}}
/>
