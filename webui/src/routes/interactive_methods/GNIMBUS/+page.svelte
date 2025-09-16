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
	 * @property {ProblemInfo} data.problem - Problem of the group.
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
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import ResizableHandle from '$lib/components/ui/resizable/resizable-handle.svelte';
	import Button from '$lib/components/ui/button/button.svelte';

	// NIMBUS specific components
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import SolutionTable from '$lib/components/custom/nimbus/solution-table.svelte';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';
	import UtopiaMap from '$lib/components/custom/nimbus/utopia-map.svelte';
	import { PREFERENCE_TYPES } from '$lib/constants';

	import { WebSocketService } from './websocket-store';

	// Utility functions
	import { 
		checkUtopiaMetadata,
		validateIterationAllowed,
		callGNimbusAPI,
	} from '../NIMBUS/helper-functions';
	type ProblemInfo = components['schemas']['ProblemInfo'];
	type Solution = components["schemas"]["SolutionReference"]
	type Response = {
		method: "optimization" | "voting";
		phase: string;
		common_results: Solution[];
		user_results: Solution[];
		personal_result_index: number | null;
		preferences: components["schemas"]["VotingPreference"] | components["schemas"]["OptimizationPreference"];
	}

	// State for NIMBUS iteration management
	let current_state: Response = $state({} as Response);
	
	let problem: ProblemInfo | null = $state(null);
	const { data } = $props<{ data: { problem: ProblemInfo; groupId: number; refreshToken: string } }>();
	let problem_data = data.problem ?? null;
	// user can choose from three types of solutions: current, best, or all, TODO: they CAN'T now obviously
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
			return current_state.common_results || [];
			case 'best':
			return current_state.common_results || [];
			case 'all':
			return current_state.common_results || [];
			default:
			return current_state.common_results || [];
		}
	});
	
	// Get the label for the selected solution type from frameworks
	let selected_type_solutions_label = $derived.by(() => {
		const framework = frameworks.find(f => f.value === selected_type_solutions);
		return framework ? framework.label : "Solutions";
	});
	// variables for handling different modes (iteration, intermediate, save, finish)
	// and chosen solutions that are separate for every mode
	let mode: "optimization" | "voting" = $state("optimization");
	let isActionDone: boolean = $state(false);
	// iteration mode
	let selected_voting_index: number = $state(0); // Index of solution from previous results to use in sidebar.
	let selected_voting_objectives: Record<string, number> = $state({}); // actual objectives of the selected solution in iteration mode

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


	// socket things
	let wsService: WebSocketService;
	let message = $state("");

	$effect(() => {
		if (message === "Please fetch results.") {
			getResults(data.groupId);
		}
		if (message === "Voting has concluded.") {
			// getFullResponse(data.groupId); // TODO: for what?
			getResults(data.groupId);
		}
	});


	/**
	 * Maps solutions objective values to arrays suitable for visualization components
	 * COPIED from helper-functions because differnt types. 
	 * Maybe try again to use that one, I am not sure if the Solution[] is so different now?
	 * @param solutions Array of solutions with objective values
	 * @param problem The problem containing objective definitions
	 * @returns Array of arrays with objective values in the order defined by the problem
	 */
	function mapSolutionsToObjectiveValues(solutions: Solution[], problem: ProblemInfo) {
		return solutions.map(result => {
			return problem.objectives.map(obj => {
				const value = result.objective_values && result.objective_values[obj.symbol];
				return Array.isArray(value) ? value[0] : value;
			});
		});
	}

	async function getResults(group_id: number) {
		const result = await callGNimbusAPI<Response>('get_latest_results', { group_id });
		if (result.success && result.data) {
			console.log("FETCH RESULTS:", result.data);
			// const { 
			// 	method,
			// 	phase,
			//  preferences,
			// 	common_results,
			// 	user_results,
			// 	personal_result_index
			// } = result.data;
			
			// Update current state with the new results
			current_state = result.data;
			// Set UI mode to the opposite of what was just completed
			mode = result.data.method === "voting" ? "optimization" : "voting";
			// Reset selection based on the new mode
			selected_voting_index = mode === "optimization" ? 0 : -1;
			change_solution_type_updating_selections('current');
			update_preferences_from_state(current_state);
			isActionDone = false;
		} else {
			console.error('Failed to FETCH RESULTS:', result.error);
		}
		// TODO: is there a step where previous preferences come from backend? full results?
		// Point is, I think I shouldn't have to do this in getResults, ever, if I end up calling getResults ony in voting phase.
		// But right now I am always calling it so I need this.
		// there is this update_preferences_from_state()-function, think of that at this point.
		// current_preference = current_state.common_results[0].objective_values
		// 	? Object.values(current_state.common_results[0].objective_values)
		// 	: [];
		return result;
	}
	
	// Validation: iteration is allowed when at least one preference is better and one is worse than current objectives
	let is_iteration_allowed = $derived.by(() => {
		// Use the imported utility function to validate if iteration is allowed
		return validateIterationAllowed(problem, current_preference, selected_voting_objectives);
	})

	function handle_type_solutions_change(event: { value: string }) {
		change_solution_type_updating_selections(event.value as 'current' | 'best' | 'all');
	}

	// Helper function to change solution type and update selections
	function change_solution_type_updating_selections(newType: 'current' | 'best' | 'all') {
		// Update the internal state
		selected_type_solutions = newType;
		// Then update UI and data
		update_voting_selection(current_state);
	}

	function handle_solution_click(index: number) {
		if(selected_voting_index === index) {
			return; // Already selected, do nothing
		}
		// Iterate mode: always select just one solution
		selected_voting_index = index;
		update_voting_selection(current_state);        
	}

	// Handle voting
	async function handle_vote() { 
		if (!problem) {
			console.error('No problem selected');
			return;
		}
		if (selected_voting_index === -1) {
			console.error('No solution set');
			return;
		}
		wsService.sendMessage(JSON.stringify(selected_voting_index));
		isActionDone = true;
	}

		// The optional unused values are kept for compatibility with the AppSidebar component
	async function handle_iterate() {
			if (!problem) {
				console.error('No problem selected');
				return;
			}
			if (current_preference.length === 0) {
				console.error('No preferences set');
				return;
			}
			if (!is_iteration_allowed) {
				console.error('Iteration not allowed based on current preferences and objectives');
				return;
			}
	
			const preference = {
				aspiration_levels: problem.objectives.reduce(
					(acc, obj, idx) => {
						acc[obj.symbol] = current_preference[idx];
						return acc;
					},
					{} as Record<string, number>
				)
			};
			console.log(preference)
			wsService.sendMessage(JSON.stringify(preference));
			isActionDone = true;
	}

	// Fetch maps data for UTOPIA visualization for one solution
	// TODO
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
		
		const solutionInfo = {
			state_id: solution.state_id,
			solution_index: solution.solution_index,
			name: solution.name
		};

		const result = await callGNimbusAPI<MapsResponse>('get_maps', {
			problem_id: problem.id,
			solution: solutionInfo
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
	function update_voting_selection(state: Response | null) {
		if (!problem) return;
		if (!state) return;
		
		// Use chosen_solutions instead of hardcoding current_solutions
		if (chosen_solutions.length === 0) return;
		
		// Make sure the selected index is within bounds of the chosen solutions
		if ( selected_voting_index >= chosen_solutions.length) {
			selected_voting_index = mode === "optimization" ? 0 : -1; // If index out of bounds, reset to first solution or none
		}
		
		const selectedSolution = chosen_solutions[selected_voting_index]; 
		selected_voting_objectives = selectedSolution && selectedSolution.objective_values ? selectedSolution.objective_values : {};
				
		// Only fetch maps if problem has utopia metadata
		if (hasUtopiaMetadata) {
			get_maps(selectedSolution);
		}
	}
	
	// Helper function to initialize preferences from previous state or ideal values
	// TODO: when is this used, do I need this? Used in getResult and getFullResponse.
	// Should probably be used so that these are whatever when it is iteration step,
	// but in voting step, last_iterated_preference could be either all the users preferences, only the oneusers,
	// or are they "previous solutions"? Question is, are they circles or lines in graph?
	function update_preferences_from_state(state: Response | null) {
		if (!problem) return;
		// current_preference = updatePreferencesFromState(state, problem);
		last_iterated_preference = [...current_preference];

	}

	onMount(async () => {
		wsService = new WebSocketService(data.groupId, "gnimbus", data.refreshToken);
		wsService.messageStore.subscribe((msg) => {
			message = msg;
		});
		problem = problem_data;
		
		if (problem) {
			hasUtopiaMetadata = checkUtopiaMetadata(problem);
			
			// Try to get results first
			const result = await getResults(data.groupId);
			
			// If we get not_initialized error, initialize and try again
			// TODO: initialization can only be done by the owner of group so  this is a little... fragile
			if (!result.success && result.error === 'not_initialized') {
				console.log('GNIMBUS not initialized, initializing...');
				const initResult = await callGNimbusAPI<Response>('initialize', { group_id: data.groupId });
				
				if (initResult.success) {
					// After successful initialization, try getting results again
					await getResults(data.groupId);
				} else {
					console.error('Failed to initialize GNIMBUS:', initResult.error);
				}
			}
		} else {
			console.error("No problem data available!");
		}
	});

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
		type_preferences = data.typePreferences;
		current_preference = [...data.preferenceValues];
	}

	async function getFullResponse(group_id: number=1) {
		const result = await callGNimbusAPI<Response>('get_full_iteration', {
			group_id: group_id
		});

		if (result.success && result.data) {
			// Update the current state with the full response
			current_state = result.data;
			
			// Initialize other state after receiving the response
			selected_voting_index = 0;
			change_solution_type_updating_selections('current');
			
			// Update UI selections based on new state
			update_voting_selection(current_state);
			update_preferences_from_state(current_state);
		} else {
			console.error('Failed to fetch the full response:', result.error);
		}
	}
</script>

<BaseLayout showLeftSidebar={!!problem} showRightSidebar={false} bottomPanelTitle={selected_type_solutions_label}>
	{#snippet leftSidebar()}

		{#if problem && mode==="optimization"}
			<AppSidebar
				{problem}
				preferenceTypes={[PREFERENCE_TYPES.Classification]}
				numSolutions={4}
				typePreferences={type_preferences}
				preferenceValues={current_preference}
				objectiveValues={Object.values(selected_voting_objectives)}
				isIterationAllowed={is_iteration_allowed}
				lastIteratedPreference={last_iterated_preference}
				onPreferenceChange={handle_preference_change}
				onIterate={handle_iterate}
				isFinishButton={false}
			/>
		{/if}
	{/snippet}

	{#snippet explorerControls()}
		<div class="p-4 rounded-lg bg-gray-50 text-sm">
			{#if message && !message.includes("Please fetch results") && !message.includes("Voting has concluded")}
				<!-- Show websocket messages that aren't handled automatically -->
				<span class="text-blue-600">{message}</span>
			{:else if mode === "voting"}
				{#if isActionDone}
					<span class="text-gray-600">
						Waiting for other users to finish voting. You can still change your vote by selecting another solution.
					</span>
				{:else}
					<span class="text-blue-600">
						Please vote for your preferred solution by selecting it from the table below.
					</span>
				{/if}
			{:else if mode === "optimization"}
				{#if isActionDone}
					<span class="text-gray-600">
						Waiting for other users to finish their iterations. You can still modify your preferences and iterate again.
					</span>
				{:else}
					<span class="text-blue-600">
						Please set your preferences for the current solution using the classification interface on the left.
					</span>
				{/if}
			{/if}
		</div>		
		<!-- <span>View: </span>
		<Combobox
		options={frameworks}
		defaultSelected={selected_type_solutions}
		onChange={handle_type_solutions_change}
		/> -->
	{/snippet}

	{#snippet visualizationArea()}
		{#if problem && current_state }
			<!-- Resizable layout for visualizations side by side -->
			<div class="h-full">
				<Resizable.PaneGroup direction="horizontal" class="h-full">
					<!-- Left side: VisualizationsPanel with constrained height -->
					<Resizable.Pane defaultSize={65} minSize={40} maxSize={80} class="h-full">
						<!-- Visualization panel that adapts to current mode -->
						<VisualizationsPanel
							{problem}
							previousPreferenceValues={mode==="optimization" ? last_iterated_preference : []}
							currentPreferenceValues={mode==="optimization" ? current_preference : []}
							previousPreferenceType={type_preferences}
							currentPreferenceType={type_preferences}
							solutionsObjectiveValues={problem ? mapSolutionsToObjectiveValues(chosen_solutions, problem) : []}
							previousObjectiveValues={(problem && mode==="voting") ? mapSolutionsToObjectiveValues(current_state.user_results, problem) : []}
							externalSelectedIndexes={[selected_voting_index]}
							onSelectSolution={handle_solution_click}
						/>
					</Resizable.Pane>
					
					{#if hasUtopiaMetadata}
						<!-- Resizable handle between panels -->
						<ResizableHandle withHandle class=" border-gray-200 shadow-sm border-4" />
						
						<!-- Right side: Decision space placeholder, for UTOPIA it is a map -->
						<Resizable.Pane defaultSize={35} minSize={20} class="h-full">
							<UtopiaMap 
								{mapOptions}
								bind:selectedPeriod={selectedPeriod}
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
			{#if mode === "voting"}
				<Button disabled={selected_voting_index === -1} onclick= {handle_vote}>Vote</Button>
			{/if}
			<SolutionTable
			{problem}
			personalResultIndex={current_state.personal_result_index}
			solverResults={chosen_solutions.map((solution, i) => ({
				state_id: 0,
				solution_index: i,
				name: null,
				objective_values: solution.objective_values,
				variable_values: solution.variable_values
			}))}
			selectedSolutions={[selected_voting_index]}
			savingEnabled={false}
			handle_row_click={handle_solution_click}
			selected_type_solutions={selected_type_solutions}
			previousObjectiveValuesType = "user_results"
			previousObjectiveValues={
				(selected_type_solutions === 'current') ? 
				(problem ? 
				current_state.user_results
					.map(result => result.objective_values)
					.filter((obj): obj is { [key: string]: number } => obj !== null && obj !== undefined)
				: 
				[]) : 
				[]
			}
			/>
		{/if}
	{/snippet}
</BaseLayout>


<!-- 
_/ remove saved and all solutions? Component is hidden, might be enough

_/ show websocket (error)messages better. No lingering, show in console.

get prev pref jostain

now there is a preference; for optimization its a pref.point and fov voting a number,
I mean it includes method

REACT TO THESE LATEST CHANGES:

I modified the GroupIterations and the PreferenceResult types,
so that the PreferenceResults are only preferences now,
there to collect the preferences from the users. 
The results are stored in states. GroupIteration now has a state_id field to store its ID.

(solutionReference in gnimbus result has state)

Also, UserPublic, instead of returning the group's name,
returns as a list the ID's of the groups that the user is part of.

The newest iteration response model now returns:
the method (optimization, voting)
and phase (learning, decision).
The responses now also include the references to the corresponding state and solver result,
so for example Utopia endpoint should be ok to use with GNIMBUS also.

Added an GNIMBUS endpoint that returns info on all iterations. 
One optimization and one voting iteration are combined into one complete, full iteration.
The endpoint returns a list of those. If the system requires voting preferences,
i.e. the last step was optimization, the endpoint returns an incomplete full iteration as the first element.
-->