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
	import { auth } from '../../../stores/auth';
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
		mapSolutionsToObjectiveValues,
	} from './helper-functions';
	type ProblemInfo = components['schemas']['ProblemInfo'];
	type Solution = components["schemas"]["SolutionReference"]
	type AllIterations = components["schemas"]["GNIMBUSAllIterationsResponse"]
	type Group = components["schemas"]["GroupPublic"]
	type Response = components["schemas"]["FullIteration"]
	let userId = $auth.user?.id;
	// State for NIMBUS iteration management
	let current_state: Response = $state({} as Response);
	let full_iterations: AllIterations = $state({} as AllIterations);
	
	let problem: ProblemInfo | null = $state(null);
	const { data } = $props<{ data: { problem: ProblemInfo; group: Group; refreshToken: string } }>();
	let problem_data = data.problem ?? null;

	// User role state
	let isOwner = $state(false);
	let isDecisionMaker = $state(false);

	let solution_options = $derived.by(() => {
		if (!current_state) return [];
		if (current_state.phase === "init" || mode === "optimization") { // init phase does not have structure to define mode
			return current_state.final_result?.objective_values ? [current_state.final_result] : [];
		} else { // mode === "voting"
			// Make sure common_results exists and each result has objective_values
			if (!current_state.common_results?.length) return [];
			return current_state.common_results;
		}
	});
	
	// Get the label for the selected solution type from frameworks

	let selected_type_solutions_label = $derived.by(() => {
		if (current_state.phase === "init") return "Initial solution";
		if (current_state.phase === "decision" && mode === "voting") return "Suggestion for a final solution";
		if (mode === "optimization") return "Voted solution";
		if (mode === "voting") return "Solutions to vote from";
		return "Solutions";
	});

	// variables for handling different modes (optimization, voting)
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

	// Message handling
	let wsService: WebSocketService;
	let message = $state("");
	let messageTimeout: number | undefined;

	function showTemporaryMessage(msg: string, duration: number = 5000) {
		// Clear any existing timeout
		if (messageTimeout) {
			clearTimeout(messageTimeout);
		}
		message = msg;
		// Clear message after duration
		messageTimeout = window.setTimeout(() => {
			message = "";
		}, duration);
	}

	$effect(() => {
		if (message === "Please fetch results.") {
			getResultsAndUpdate(data.group.id);
		}
		if (message === "Voting has concluded.") {
			getResultsAndUpdate(data.group.id);
		 }
	});

		async function getResultsAndUpdate(group_id: number) {
		const fullResult = await callGNimbusAPI<AllIterations>('get_all_iterations', {
			group_id: group_id
		});

		if (fullResult.success && fullResult.data) {
			// Update full history
			full_iterations = fullResult.data;
			// Update current state with user-specific information
			
			// Get the last iteration for context ??
			const latestIteration = fullResult.data.all_full_iterations[0];
			if (!latestIteration) return;
			current_state = latestIteration;

			// Set mode based on current state; Set UI mode to the opposite of what was just completed
			if (latestIteration.phase === "init") mode = "optimization";
			else mode = (latestIteration.voting_preferences !== null) ? "optimization" : "voting";
			
			function hasOptimizationPreferences(iteration: Response): iteration is Response & { optimization_preferences: NonNullable<Response['optimization_preferences']> } {
				return iteration.optimization_preferences !== null;
			}
			if (
				userId && isDecisionMaker
			) {
				// Update preferences based on the current state and method
				if (!hasOptimizationPreferences(latestIteration)) {
					// Handle null case with starting_result
					if (problem) {
						current_preference = problem.objectives.map(obj => 
							obj.ideal ?? 0
						);
					}
				}
				else {
					// TypeScript now knows optimization_preferences is not null
					current_preference = problem?.objectives.map(obj =>
						latestIteration.optimization_preferences.set_preferences[userId].aspiration_levels[obj.symbol]
					) || [];
				}
			}
			
			// Reset selection based on the new mode
			if (current_state.phase ==="decision") selected_voting_index = 0;
			else selected_voting_index = mode === "optimization" ? 0 : -1;
			update_voting_selection(current_state);
			last_iterated_preference = [...current_preference];
			isActionDone = false;
		} else {
			console.error('Failed to fetch the full response:', fullResult.error);
		} 
		return fullResult;
	}
	
	// Validation: iteration is allowed when at least one preference is better and one is worse than current objectives
	let is_iteration_allowed = $derived.by(() => {
		// Use the imported utility function to validate if iteration is allowed
		return validateIterationAllowed(problem, current_preference, selected_voting_objectives);
	})

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
			wsService.sendMessage(JSON.stringify(preference));
			isActionDone = true;
	}

	// Fetch maps data for UTOPIA visualization for one solution
	async function get_maps(solution: Solution) {
		if (!problem) {
			console.error('No problem selected');
			return;
		}
		if (selected_voting_index === -1) {
			console.log('No solution selected');
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
		} else {
			console.error('Failed to get maps:', result.error);
		}
	}

	// Helper function to update current iteration objectives from the current state
	function update_voting_selection(state: Response | null) {
		if (!problem) return;
		if (!state) return;
		
		// Use chosen_solutions instead of hardcoding current_solutions
		if (solution_options.length === 0) return;
		
		// Make sure the selected index is within bounds of the chosen solutions
		if ( selected_voting_index >= solution_options.length) {
			selected_voting_index = mode === "optimization" ? 0 : -1; // If index out of bounds, reset to first solution or none
		}
		
		const selectedSolution = solution_options[selected_voting_index]; 
		selected_voting_objectives = selectedSolution && selectedSolution.objective_values ? selectedSolution.objective_values : {};
				
		// Only fetch maps if problem has utopia metadata
		if (hasUtopiaMetadata) {
			get_maps(selectedSolution);
		}
	}

	// Function to handle phase switching
	async function handle_phase_switch(new_phase: "learning" | "decision" | "crp") {

		const result = await callGNimbusAPI<Response>('switch_phase', { 
			group_id: data.group.id,
			new_phase
		});

		if (!result || (!result.success && result.error === 'wrong_step')) {
			showTemporaryMessage("Wrong step for phase change!");
			// Revert the UI selection back to current state
		} else {
			// Update will happen via websocket notification
			message = "Phase switched to "+new_phase;
			console.log('Phase change requested successfully');
		}
	}

	onMount(async () => {
		// Determine user roles based on group ownership and membership
		if (userId) {
			isOwner = userId === data.group.owner_id;
			isDecisionMaker = data.group.user_ids.includes(userId);
		}

		wsService = new WebSocketService(data.group.id, "gnimbus", data.refreshToken);
		wsService.messageStore.subscribe((msg) => {
			if (messageTimeout) {
				clearTimeout(messageTimeout);
				messageTimeout = undefined;
			}
			message = msg;
		});
		problem = problem_data;
		
		if (problem) {
			hasUtopiaMetadata = checkUtopiaMetadata(problem);
			
			// Try to get results first
			const result = await getResultsAndUpdate(data.group.id);
			console.log(result?.data?.all_full_iterations)

			// If we get not_initialized error, initialize and try again
			// TODO: understand when the await is needed, when not and what it causes here
			if (!result || (!result.success && result.error) === 'not_initialized') {
				console.log('GNIMBUS not initialized, initializing...');
				const initResult = await callGNimbusAPI<Response>('initialize', { group_id: data.group.id });
				
				if (initResult.success) {
					// After successful initialization, try getting results again
					await getResultsAndUpdate(data.group.id);
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
</script>

<BaseLayout showLeftSidebar={!!problem} showRightSidebar={false} bottomPanelTitle={selected_type_solutions_label}>
	{#snippet leftSidebar()}

		{#if problem && mode==="optimization" && isDecisionMaker}
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
		{#if isOwner && mode === "optimization"}
			<span>Switch phase: </span>
			<Button onclick={()=>handle_phase_switch("learning")}>Learning</Button>
			<Button onclick={()=>handle_phase_switch("crp")}>CRP</Button>
			<Button onclick={()=>handle_phase_switch("decision")}>Decision</Button>
		{/if}
		<div class="p-4 rounded-lg bg-gray-50 text-sm">
			{#if message && !message.includes("Please fetch results") && !message.includes("Voting has concluded")}
				<!-- Show websocket messages that aren't handled automatically -->
				<span class="text-gray-600">{message}</span>
			{:else if isOwner && !isDecisionMaker}
				{#if mode === "optimization"}
					<span class="text-gray-600">
						Viewing current solutions in {current_state.phase} phase. Phase can be switched during optimization steps.
					</span>
				{:else}
					<span class="text-gray-600">
						Viewing solutions in {current_state.phase} phase. Please wait for voting to complete.
					</span>
				{/if}
			{:else if mode === "voting" && isDecisionMaker}
				{#if isActionDone}
					<span class="text-gray-600">
						Waiting for other users to finish voting. You can still change your vote by selecting another solution.
					</span>
				{:else}
					<span class="text-blue-600">
						Please vote for your preferred solution by selecting it from the table below.
					</span>
				{/if}
			{:else if mode === "optimization" && isDecisionMaker}
				{#if isActionDone}
					<span class="text-gray-600">
						Waiting for other users to finish their iterations. You can still modify your preferences and iterate again.
					</span>
				{:else}
					<span class="text-blue-600">
						Please set your preferences for the current solution using the classification interface on the left.
					</span>
				{/if}
			{:else}
				<span class="text-gray-600">
					Viewing group progress.
				</span>
			{/if}
		</div>		
	{/snippet}

	{#snippet visualizationArea()}
		{#if problem && current_state && solution_options.length > 0 }
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
							solutionsObjectiveValues={problem ? mapSolutionsToObjectiveValues(solution_options, problem) : []}
							previousObjectiveValues={(problem && mode==="voting" && current_state.personal_result_index !== null) ? mapSolutionsToObjectiveValues([current_state.user_results[current_state.personal_result_index]], problem) : []}
							otherObjectiveValues={(problem && mode==="voting") ? mapSolutionsToObjectiveValues(current_state.user_results, problem) : []}
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
		{#if problem && solution_options.length > 0}
			<div class="flex flex-col h-full">
				{#if mode === "voting" && isDecisionMaker}
					{#if current_state.phase === "decision"}
						<div class="flex-none mb-2">
							<Button
								variant="default"
								onclick={() => {
									handle_vote();
									console.log("true");
								}}
							>
								Select as the final solution
							</Button>
							<Button
								variant="destructive"
								onclick={() => console.log("false")}
							>
								Continue to next iteration
							</Button>
						</div>
					{:else}
						<div class="flex-none mb-2">
							<Button disabled={selected_voting_index === -1} onclick= {handle_vote}>Vote</Button>
						</div>
					{/if}
				{/if}
				<div class="flex-1 min-h-0">
					<SolutionTable
						{problem}
						personalResultIndex={current_state.personal_result_index}
						solverResults={solution_options.map((solution, i) => ({
							state_id: solution.state_id,
							solution_index: i,
							name: null,
							objective_values: solution.objective_values,
							variable_values: solution.variable_values
						}))}
						selectedSolutions={[selected_voting_index]}
						savingEnabled={false}
						handle_row_click={handle_solution_click}
						selected_type_solutions={"current"}
						previousObjectiveValuesType = "user_results"
						previousObjectiveValues={
							(mode === "voting") ? 
							(problem ? 
							current_state.user_results
								.map(result => result.objective_values)
								.filter((obj): obj is { [key: string]: number } => obj !== null && obj !== undefined)
							: 
							[]) : 
							[]
						}
					/>
				</div>
			</div>
		{/if}
	{/snippet}
</BaseLayout>