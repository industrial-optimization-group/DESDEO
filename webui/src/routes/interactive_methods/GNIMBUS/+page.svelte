<script lang="ts">
	/**
	 * +page.svelte (GNIMBUS method)
	 *
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created September 2025
	 *
	 * @description
	 * This page implements the Group NIMBUS interactive multiobjective optimization method in DESDEO.
	 * GNIMBUS extends the NIMBUS method to support group decision making through voting and consensus building.
	 *
	 * The implementation follows a phase-based approach:
	 * 1. Learning: Users learn about the problem space and practice setting preferences
	 * 2. CRP (Collaborative Reference Point): Users collaborate to find preferred solutions
	 * 3. Decision: Group decides on the final solution
	 * 4. Compromise: Decision phase variant for different backend behaviour
	 *
	 * Each phase alternates between:
	 * - Optimization mode: Users set preferences to generate new solutions
	 * - Voting mode: Users vote on proposed solutions
	 *
	 * @props
	 * @property {Object} data - Server-loaded data containing problem and group information
	 * @property {ProblemInfo} data.problem - Problem definition and metadata
	 * @property {Group} data.group - Group information including members and roles
	 * @property {string} data.refreshToken - Token for WebSocket authentication
	 *
	 * @features
	 * - Real-time group collaboration via WebSocket
	 * - Role-based access control (owner vs decision maker)
	 * - Interactive preference setting and solution generation
	 * - Voting system for solution selection
	 * - Visualization of objective space
	 * - Map visualization for problems with geographical data (UTOPIA)
	 * - Phase-based group decision making process
	 *
	 * @dependencies
	 * - BaseLayout: Core layout component
	 * - AppSidebar: Preference setting interface
	 * - VisualizationsPanel: Objective space visualization
	 * - UtopiaMap: Geographical data visualization
	 * - WebSocketService: Real-time communication
	 */
	// Layout and core components
	import { BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import { auth } from '../../../stores/auth';
	import { onMount } from 'svelte';

	// UI Components
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import ResizableHandle from '$lib/components/ui/resizable/resizable-handle.svelte';
	import Button from '$lib/components/ui/button/button.svelte';
	import { Combobox } from '$lib/components/ui/combobox';

	// NIMBUS specific components
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';
	import UtopiaMap from '$lib/components/custom/nimbus/utopia-map.svelte';
	import { PREFERENCE_TYPES } from '$lib/constants';
	import { errorMessage, isLoading } from '../../../stores/uiState';
	import LoadingSpinner from '$lib/components/custom/notifications/loading-spinner.svelte';
	import Alert from '$lib/components/custom/notifications/alert.svelte';



	import type {
		ProblemInfo,
		Solution,
		AllIterations,
		Group,
		Response,
		Step,
		PeriodKey,
		MapState,
		TableData
	} from './types';

	import { WebSocketService } from './websocket-store';

	// Utility functions
	import {
		checkUtopiaMetadata,
		validateIterationAllowed,
		callGNimbusAPI,
		getStatusMessage,
		determineStep,
		createVisualizationData,
		createPreferenceData
	} from './helper-functions';
	import SolutionDisplay from './components/SolutionDisplay.svelte';
	import EndStateView from './components/EndStateView.svelte';

	let userId = $auth.user?.id;
	// State for NIMBUS iteration management
	let current_state: Response = $state({} as Response);
	let full_iterations: AllIterations = $state({} as AllIterations);

	// all solutions and preferences from all iterations in proper form:
	// TODO: works but is slow as heck and extremely messy. Refactor when possible.
	let history: {
		own_solutions: any[];
		common_solutions: any[];
		preferences: number[][];
		chosen_preference: number[];
	} = $derived.by(() => {
		let own_solutions = full_iterations.all_full_iterations.map((iteration, index) => {
			const iterationNumber = full_iterations.all_full_iterations.length - 1 - index; // Count backwards like header
			return {
				...iteration.user_results[(iteration.personal_result_index || 0)],
				iteration_number: iterationNumber
			}
		}
		);
		let common_solutions = full_iterations.all_full_iterations.flatMap((iteration, index) => {
			const iterationNumber = full_iterations.all_full_iterations.length - 1 - index; // Count backwards like header
			return (iteration.common_results ?? []).map(solution => ({
            ...solution,
            iteration_number: iterationNumber
        }));
		}
	);
		let all_preferences = full_iterations.all_full_iterations.map((iteration) => iteration.optimization_preferences);
		let all_pref_data = all_preferences.map((pref)=>{
		if (pref !== null) return pref.set_preferences;
		});
		let preferences = all_pref_data.map((data)=> {
			if (data && userId) {
				let pref_values = Object.values(data[userId].aspiration_levels);
				return pref_values;
			}
		}).filter((vals): vals is number[] => vals !== null && vals !== undefined);
		let chosen_preference = preferences.splice(selected_voting_index, 1)[0]; // remove the selected iteration's preferences
		
		return {
			own_solutions,
			common_solutions,
			preferences,
			chosen_preference
		};		
	});
	let problem: ProblemInfo | null = $state(null);
	const { data } = $props<{ data: { problem: ProblemInfo; group: Group; refreshToken: string } }>();

	// User role state
	let isOwner = $state(false);
	let isDecisionMaker = $state(false);

	// Define the base phases array for group owners phase change buttons
	const PHASE_CONFIGS = [
		{ id: 'learning', label: 'Learning' },
		{ id: 'crp', label: 'CRP' },
		{ id: 'decision', label: 'Decision' },
		{ id: 'compromise', label: 'Compromise' }
	] as const;

	// Helper function to determine button variant for group owners phase change buttons
	function getVariant(phaseId: typeof PHASE_CONFIGS[number]['id'], currentPhase: string) {
	if (currentPhase === 'init' ) currentPhase = 'learning';
	return currentPhase === phaseId ? 'default' : 
		'outline' as 'outline' | 'default' | 'secondary';
	}

	// Derived phases with variants
	let PHASES = $derived.by(() => 
		PHASE_CONFIGS.map(phase => ({
			...phase,
			variant: getVariant(phase.id, current_state.phase)
		}))
	);
	// the options shown in the drop-down for selecting solution types:
	const frameworks = [
		{ value: 'current', label: 'Current iteration' },
		{ value: 'all_own', label: 'All own solutions and preferences' },
		{ value: 'all_group', label: 'All group solutions' }
	];
	
	// this is what drop-down selection is bound to:
	let selected_type_solutions = $state('current');
	// These functions are all here so this should be easy to refactor later. Just in case 'current', do what solution_options does, and rename stuff accordingly.

	// TODO: this has no meaning now, just something to start working on,
	// this was used to define the selected_type_solutions_label in NIMBUS.
	let random_text_based_on_dropbar = $derived.by(() => {
		const framework = frameworks.find((f) => f.value === selected_type_solutions);
		return framework ? framework.label : 'Solutions';
	});

	// if showHistory, read solution_options from chosen_history. Ongoing TODO.
	// the solutions we want to show in UI are different depending on the step of iteration.
	// in the optimization step we want to show the final result,
	// and in the voting step we want to show the common results.
	let solution_options = $derived.by(() => {
		if (!current_state) return [];
		if (selected_type_solutions === 'all_group') {
			return history.common_solutions;
		}
		if (selected_type_solutions === 'all_own') {
			return history.own_solutions;
		}
		switch (step) {
			case 'optimization':
				return current_state.final_result?.objective_values ? [current_state.final_result] : [];
			case 'voting':
				return current_state.common_results ?? [];
			case 'finish':
				return current_state.common_results ?? []; // TODO: make sure this is right. 
				// I mean, it works but could I make this more logical? Does the final solution have structure where I could also use final solution?
			default:
				return [];
		}
			
	});
	function handle_type_solutions_change(event: { value: string }) {
		change_solution_type_updating_selections(event.value as 'current' | 'all_own' | 'all_group');
	}
	// Helper function to change solution type and update selections TODO: this is in the wrong place, history thing
	function change_solution_type_updating_selections(newType: 'current' | 'all_own' | 'all_group') {
		// Update the internal state
		selected_type_solutions = newType;
		console.log('Changed solution type to:', newType);
		// TODO: when changing back to current, reset selections. If step is optimization, select index 0.
		// If voting, what? User may have voted, so if I do -1, it might confuse them.
		// Then update UI and data
		// update_iteration_selection(current_state);
		// update_intermediate_selection(current_state);
	}

	// Get the label for the selected solution type from frameworks TODO
	let selected_type_solutions_label = $derived.by(() => {
		if (current_state.phase === 'init') return 'Initial solution';
		if ((current_state.phase === 'decision' ||current_state.phase === 'compromise') && step === 'voting')
			return 'Suggestion for a final solution';
		if (step === 'optimization') return 'Voted solution';
		if (step === 'voting') return 'Solutions to vote from';
		if (step === 'finish') return '';
		return 'Solutions';
	});

	// variable for handling different steps (view and possible actions are defined by step)
	let step: Step = $state('optimization');

	// variable for tracking if the user did the action for the ongoing step, used in defining what instruction is shown to user
	let isActionDone: boolean = $state(false);

	// variables needed for voting: index of voted solution and the objectives extracted from that solution
	let selected_voting_index: number = $state(0); // Index of solution from previous results to use in sidebar.
	let selected_voting_objectives: Record<string, number> = $state({}); // actual objectives of the selected solution in iteration mode

	// currentPreference is initialized from previous preference or ideal values
	let current_preference: number[] = $state([]);
	// Store the last iterated preference values to show as "previous" in UI
	let last_iterated_preference: number[] = $state([]);

	// Variable to track if problem has utopia metadata
	let hasUtopiaMetadata = $state(false);

	// Variables for showing the map for UTOPIA - stores maps for all solutions
	let mapStates: MapState[] = $state([]);
	let mapState: MapState = $state({
		mapOptions: {
			period1: {},
			period2: {},
			period3: {}
		},
		yearlist: [],
		selectedPeriod: 'period1' as PeriodKey,
		geoJSON: undefined,
		mapName: undefined,
		mapDescription: undefined
	});

	// Message handling
	let wsService: WebSocketService;
	let message: string | undefined = $state(undefined);
	let socketError: string | undefined = $state(undefined);
	let messageTimeout: number | undefined;
	let alerts = $derived.by(() => [
        { message: $errorMessage ?? undefined, variant: 'destructive' as const},
        { message: socketError, variant: 'destructive' as const},
        { message: message, variant: 'default' as const}
    ].filter(alert => alert.message));

	function showTemporaryMessage(msg: string, duration: number = 5000) {
		// Clear any existing timeout
		if (messageTimeout) {
			clearTimeout(messageTimeout);
		}
		if (msg.includes('ERROR')) {
			socketError = msg;
			messageTimeout = window.setTimeout(() => {
				socketError = undefined;
			}, duration);
		}
		message = msg;
		// Clear message after duration
		messageTimeout = window.setTimeout(() => {
			message = undefined;
		}, duration);
	}

	// Main function to fetch and update state
	async function getResultsAndUpdate(group_id: number) {
		const fullResult = await callGNimbusAPI<AllIterations>('get_all_iterations', {
			group_id: group_id
		});

		if (!fullResult.success || !fullResult.data) {
			console.error('Failed to fetch the full response:', fullResult.error);
			return fullResult;
		}

		// Update full history
		full_iterations = fullResult.data;

		const latestIteration = fullResult.data.all_full_iterations[0];
		if (!latestIteration) return fullResult;

		// Get the current phase (since all_iterations might have outdated phase)
		const phaseResult = await callGNimbusAPI<Response>('get_phase', {
			group_id: group_id
		});
		let phase = phaseResult.success && phaseResult.data ? phaseResult.data.phase : latestIteration.phase
		if (latestIteration.phase === 'init') phase = 'init';
		// Update current state with correct phase
		current_state = {
			...latestIteration,
			phase
		};
		step = determineStep(current_state);

		// Update preferences if user is a decision maker
		if (userId && isDecisionMaker && problem) {
			if (!latestIteration.optimization_preferences) {
				// Use ideal values if no previous preferences
				current_preference = problem.objectives.map((obj) => obj.ideal ?? 0);
			} else {
				// Use previous preferences
				current_preference =
					problem.objectives.map(
						(obj) =>
							latestIteration.optimization_preferences!.set_preferences[userId].aspiration_levels[
								obj.symbol
							]
					) || [];
			}
		}

		// Update selection state
		selected_voting_index =
			(latestIteration.phase === 'decision' || latestIteration.phase == 'compromise') ? 0 : step === 'optimization' ? 0 : -1;

		// Update dependent states
		update_voting_selection(current_state);
		last_iterated_preference = [...current_preference];
		isActionDone = false;
		console.log('Fetch result:', fullResult);

		return fullResult;
	}

	// Validation: iteration is allowed when at least one preference is better and one is worse than current objectives
	let is_iteration_allowed = $derived.by(() => {
		// Use the imported utility function to validate if iteration is allowed
		return validateIterationAllowed(problem, current_preference, selected_voting_objectives);
	});

	function handle_solution_click(index: number) {
		if (selected_voting_index === index) {
			return; // Already selected, do nothing
		}
		// Iterate mode: always select just one solution
		selected_voting_index = index;
		update_voting_selection(current_state);
	}

	// Handle voting
	async function handle_vote(int = 0) {
		if (!problem) {
			console.error('No problem selected');
			return;
		}

		if (selected_voting_index === -1) {
			console.error('No solution set');
			return;
		}
		const success = await wsService.sendMessage(JSON.stringify(int));
		if (success) {
			// showTemporaryMessage('Vote submitted');
			isActionDone = true;
		}
	}

	// function for handling the iteration of the optimization step. Sends the preferences as a message to websocket
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
		const success = await wsService.sendMessage(JSON.stringify(preference));
		if (success) {
			showTemporaryMessage('Preferences submitted');
			isActionDone = true;
		}
	}

	// Fetch maps data for UTOPIA visualization for one solution
	async function get_maps(solution: Solution, solutionIndex: number) {
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

		try {
			const result = await callGNimbusAPI<MapsResponse>('get_maps', {
				problem_id: problem.id,
				solution: solutionInfo
			});

			if (result.success && result.data) {
				const data = result.data;

				// Create new map state for this solution
				const newMapState: MapState = {
					mapOptions: {
						period1: {},
						period2: {},
						period3: {}
					},
					yearlist: data.years,
					selectedPeriod: 'period1' as PeriodKey,
					geoJSON: data.map_json,
					mapName: data.map_name,
					mapDescription: data.description
				};

				// Apply the formatter function client-side
				for (let year of newMapState.yearlist) {
					if (data.options[year].tooltip.formatterEnabled) {
						data.options[year].tooltip.formatter = function (params: any) {
							return `${params.name}`;
						};
					}
				}

				// Assign map options for each period
				newMapState.mapOptions = {
					period1: data.options[newMapState.yearlist[0]] || {},
					period2: data.options[newMapState.yearlist[1]] || {},
					period3: data.options[newMapState.yearlist[2]] || {}
				} as Record<PeriodKey, Record<string, any>>;

				// Store the map state at the correct index
				mapStates[solutionIndex] = newMapState;
				if (solutionIndex === selected_voting_index) {
					mapState = { ...newMapState };
					console.log('Updated map state for selected solution:', mapState);
				}
			}
		} catch (error) {
			console.error(`Failed to get maps for solution ${solutionIndex}:`, error);
		}
	}

	// Pre-fetch maps for all solutions when solution_options changes
	$effect(() => {
		if (hasUtopiaMetadata && solution_options.length > 0) {
			// Initialize mapStates array with the correct length
			mapStates = new Array(solution_options.length);
			
			// Fetch maps for each solution without waiting
			solution_options.forEach((solution, index) => {
				get_maps(solution, index);
			});
		}
	});

	// Helper function to update objectives of selected solution from the current state
	function update_voting_selection(state: Response | null) {
		if (!problem) return;
		if (!state) return;

		if (solution_options.length === 0) return;

		// Make sure the selected index is within bounds of the chosen solutions
		if (selected_voting_index >= solution_options.length) {
			selected_voting_index = step === 'optimization' ? 0 : -1; // If index out of bounds, reset to first solution or none
		}

		const selectedSolution = solution_options[selected_voting_index];
		selected_voting_objectives =
			selectedSolution && selectedSolution.objective_values
				? selectedSolution.objective_values
				: {};
		console.log("selected voting index:", selected_voting_index);
		// Update current map state from pre-fetched maps if available
		if (hasUtopiaMetadata && selected_voting_index >= 0 && mapStates[selected_voting_index]) {
			mapState = { ...mapStates[selected_voting_index] };
			console.log('Updated map state for selected solution:', mapState);
		}
	}

	async function handlePhaseClick(phaseId: typeof PHASE_CONFIGS[number]['id']) {		
		try {
			// Switch to the new phase
			const switchResult = await callGNimbusAPI<Response>('switch_phase', {
				group_id: data.group.id,
				new_phase: phaseId
			});

			if (!switchResult.success) {
				if (switchResult.error === 'wrong_step') {
					showTemporaryMessage('Wrong step for phase change!');
				}
				return;
			}

			// Get the updated phase state
			const phaseResult = await callGNimbusAPI<Response>('get_phase', {
				group_id: data.group.id
			});

			if (phaseResult.success && phaseResult.data) {
				// Update the current state with the new phase
				current_state = { ...current_state, phase: phaseResult.data.phase };
				
			}

		} catch (err) {
			console.error('Phase switch error:', err);
			showTemporaryMessage('Failed to switch phase');
		}
	}

	async function initializeGNIMBUS(groupId: number) {
		try {
			const result = await callGNimbusAPI<Response>('initialize', { group_id: groupId });
			if (!result.success) {
				throw new Error(result.error);
			}
			return result;
		} catch (error) {
			console.error('Failed to initialize GNIMBUS:', error);
			return null;
		}
	}

	onMount(async () => {
		// Set user roles
		if (userId) {
			isOwner = userId === data.group.owner_id;
			isDecisionMaker = data.group.user_ids.includes(userId);
		}

		if (!data.problem) {
			console.error('No problem data available!');
			return;
		}

		// Set problem and check metadata
		problem = data.problem;
		hasUtopiaMetadata = checkUtopiaMetadata(problem);

		// Initialize WebSocket
		wsService = new WebSocketService(data.group.id, 'gnimbus', data.refreshToken);
		wsService.messageStore.subscribe((store) => {
			// Filters for specific messages. 
			// TODO: when API is updated, all messages should include keyword UPDATE if update in UI needed,
			// and keyword ERROR if msg is error message. Other checks can be removed
			// this is because socket messages are simple strings and there is no other way to differentiate them.
			let msg = store.message;
			if (
				msg.includes('UPDATE:') ||
				msg.includes('Please fetch') ||
				msg.includes('Voting has concluded')
			) {
				// Don't show these messages, but instead update state
				getResultsAndUpdate(data.group.id);
				return;
			}
			
			// Replace "compromise" with "decision" in messages for non-owners
			let displayMessage = !isOwner ? msg.replace(/compromise/gi, 'decision') : msg;
			
			// Filter out "same phase to same phase" messages for non-owners TODO: ASK which one is good, show this or not. Because user will see the spinner!
			if (!isOwner && /from (\w+) to \1/i.test(displayMessage)) {
				// Don't show "changed from X to X" messages to non-owners, but still update state
				getResultsAndUpdate(data.group.id);
				return;
			}
			
			// Show the processed message
			showTemporaryMessage(displayMessage);
		});

		// Try to get existing results from backend
		const result = await getResultsAndUpdate(data.group.id);
		// Initialize only if there are no results beforehand
		if (!result?.success && result?.error === 'not_initialized') {
			console.log('GNIMBUS not initialized, initializing...');
			const initResult = await initializeGNIMBUS(data.group.id);
			if (initResult) {
				getResultsAndUpdate(data.group.id);
			}
		}
	});

	// type preferences for AppSidebar and Visualization panel. In gnimbus, they are always classification.
	let type_preferences = $state(PREFERENCE_TYPES.Classification);

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

	// Derived value for solution table data
	let tableData: TableData[] = $derived.by(() =>
		solution_options.map((solution, i) => ({
			state_id: solution.state_id,
			solution_index: i,
			name: null,
			objective_values: solution.objective_values,
			variable_values: solution.variable_values,
			iteration_number: solution.iteration_number ?? null
		}))
	);

	let userSolutionsObjectives = $derived.by(() => {
		if (step !== 'voting' || !problem) return [];
		return current_state.user_results
			.map((result) => result.objective_values)
			.filter((obj): obj is { [key: string]: number } => obj !== null && obj !== undefined);
	});

	let visualizationPreferences = $derived.by(() => {
		if (selected_type_solutions === "current") return createPreferenceData(step, last_iterated_preference, current_preference)
		// show preference history if user selected to see their own history, 
		// otherwise show no preferenes
		return {
			previousValues: selected_type_solutions === 'all_own' ? history.preferences: [],
			currentValues: selected_type_solutions === 'all_own' ? history.chosen_preference: []
		}
	}
	);

	let visualizationObjectives = $derived.by(() =>
		createVisualizationData(problem, step, current_state, solution_options)
	);
</script>

{#if $isLoading}
	<LoadingSpinner />
{/if}

{#each alerts as alert}
    <Alert 
        message={alert.message} 
        variant={alert.variant}
    />
{/each}

<BaseLayout
	showLeftSidebar={!!problem}
	showRightSidebar={false}
	bottomPanelTitle={selected_type_solutions_label}
>

	{#snippet explorerTitle()}
		<span class="font-bold">
			{#if step === 'finish'}
				Final Solution
			{:else}
				{current_state.phase === 'crp' ? 'Consensus Reaching Phase' : 
				current_state.phase === 'init' ? 'Learning Phase' :
				current_state.phase === 'learning' ? 'Learning Phase' :
				current_state.phase === 'decision' ? 'Decision Phase' :
				current_state.phase === 'compromise' ? 'Decision Phase' :
				''}
			{/if}
		</span>
		{@const iter = full_iterations.all_full_iterations?.length ? 
			((step === 'optimization') ? 
				full_iterations.all_full_iterations?.length 
				:full_iterations.all_full_iterations?.length-1 ) 
			: "0"}
		<span> / Iteration {iter}</span>
		{#if problem && selected_type_solutions === 'current'}
			{@const statusMessage = getStatusMessage({
				isOwner,
				isDecisionMaker,
				step,
				isActionDone
			})}
			<span class="left-0 p-4 font-normal">
				{statusMessage}
			</span>
		{/if}
	{/snippet}

	{#snippet explorerControls()}
		{#if isOwner && step === 'optimization'}
		<span class="left-0 p-4">Change phase: </span>
			{#each PHASES as phase}
                    <Button
                        variant={phase.variant}
                        onclick={() => handlePhaseClick(phase.id)}
                    >
                        {phase.label}
                    </Button>
			{/each}
		{/if}
		<span class="left-0 p-4">View: </span>
		<Combobox
			options={frameworks}
			defaultSelected={selected_type_solutions}
			onChange={handle_type_solutions_change}
		/>
	{/snippet}

	{#snippet leftSidebar()}
		{#if problem && step === 'optimization' && isDecisionMaker && selected_type_solutions === 'current'}
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

	{#snippet visualizationArea()}
		{#if problem && current_state && solution_options.length > 0}
			<!-- Resizable layout for visualizations side by side -->
			<div class="h-full">
				<Resizable.PaneGroup direction="horizontal" class="h-full">
					<!-- Left side: VisualizationsPanel with constrained height -->
					<Resizable.Pane defaultSize={65} minSize={40} maxSize={80} class="h-full">
						<!-- Visualization panel that adapts to current mode -->
						<VisualizationsPanel
							{problem}
							previousPreferenceValues={visualizationPreferences?.previousValues}
							currentPreferenceValues={visualizationPreferences?.currentValues}
							previousPreferenceType={type_preferences}
							currentPreferenceType={type_preferences}
							solutionsObjectiveValues={visualizationObjectives.solutions}
							previousObjectiveValues={visualizationObjectives.previous}
							otherObjectiveValues={visualizationObjectives.others}
							externalSelectedIndexes={[selected_voting_index]}
							onSelectSolution={handle_solution_click}
							lineLabels={Object.fromEntries(
								visualizationObjectives.solutions.map((_, i) => [
									i, 
									visualizationObjectives.solutions.length === 1 
										? 'Group solution' 
										: `Group solution ${i + 1}`
								])
							)}
							referenceDataLabels={{
								previousRefLabel: 'Your previous preference',
								currentRefLabel: 'Your current preference',
								previousSolutionLabels:['Your individual solution'],
								otherSolutionLabels: visualizationObjectives.others.map((_, i) => isDecisionMaker ? `Another user's solution`:`User ${i + 1}'s solution`),
							}}
						/>
					</Resizable.Pane>

					{#if hasUtopiaMetadata}
						<!-- Resizable handle between panels -->
						<ResizableHandle withHandle class=" border-4 border-gray-200 shadow-sm" />

						<!-- Right side: Decision space placeholder, for UTOPIA it is a map -->
						<Resizable.Pane defaultSize={35} minSize={20} class="h-full">
							<UtopiaMap
								mapOptions={mapState.mapOptions}
								bind:selectedPeriod={mapState.selectedPeriod}
								yearlist={mapState.yearlist}
								geoJSON={mapState.geoJSON}
								mapName={mapState.mapName}
								mapDescription={mapState.mapDescription}
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
			{#if step === 'finish'}
				<EndStateView {problem} {tableData} />
			{:else}
				<SolutionDisplay
					{problem}
					{step}
					{current_state}
					{tableData}
					{selected_type_solutions}
					{selected_voting_index}
					userSolutionsObjectives={userSolutionsObjectives}
					{isDecisionMaker}
					onVote={handle_vote}
					onRowClick={handle_solution_click}
				/>
			{/if}
		{/if}
	{/snippet}
</BaseLayout>
