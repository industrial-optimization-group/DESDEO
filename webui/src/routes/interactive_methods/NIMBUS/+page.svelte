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
	 * @props
	 * @property {Object} data - Contains a list of optimization problems fetched from the server.
	 * @property {ProblemInfo[]} data.problems - List of problems.
	 *
	 * @features
	 * - Sidebar with problem information and preference types.
	 * - Solution explorer with a combobox to select between "Current", "Best", and "All" solutions.
	 * - Responsive, resizable layout using PaneGroup and Pane components.
	 * - Visualization placeholders for objective and decision spaces.
	 * - Tabbed interface for numerical values and saved solutions.
	 *
	 * @dependencies
	 * - AppSidebar: Sidebar component for preferences and problem info.
	 * - Combobox: Custom combobox component for solution type selection.
	 * - Resizable: UI components for resizable panes.
	 * - Tabs: UI components for tabbed content.
	 * - methodSelection: Svelte store for the currently selected problem.
	 * - OpenAPI-generated ProblemInfo type.
	 *
	 * @notes
	 * - The selected problem is determined from the methodSelection store.
	 * - Visualization and table content are placeholders and should be implemented as needed.
	 */
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import type { components } from '$lib/api/client-types';
	import { onMount } from 'svelte';
	import { Combobox } from '$lib/components/ui/combobox';
	import * as Tabs from '$lib/components/ui/tabs/index.js';

	type ProblemInfo = components['schemas']['ProblemInfo'];
	
	// Define a general type for any state with solver_results
	// TODO: This will be limited to NIMBUSClassificationState and NIMBUSInitializationState, after nimbus initialization works.
	type StateWithResults = {
		solver_results: Array<{
			optimal_objectives: Record<string, number | number[]>;
			[key: string]: any;
		}>;
		[key: string]: any;
	};
	
	let problem: ProblemInfo | null = $state(null);
	const { data } = $props<{ data: ProblemInfo[] }>();
	let problemList = data.problems ?? [];
	let selectedTypeSolutions = $state('current');

	// State for NIMBUS iteration management
	let previousState: StateWithResults | null = $state(null);
	let selectedSolutionIndex: number = $state(0); // Which solution from previous results to use

	// currentPreference is initialized from previous_preference or ideal values
	let currentPreference: number[] = $state([]);
	let currentNumSolutions: number = $state(1);
	// Current objectives for the sidebar - either from selected solution or calculated average
	let currentObjectives: Record<string, number> = $state({});
	// Store the last iterated preference values to show as "previous" in UI
	let lastIteratedPreference: number[] = $state([]);

	const frameworks = [
		{ value: 'current', label: 'Current solutions' },
		{ value: 'best', label: 'Best solutions' },
		{ value: 'all', label: 'All solutions' }
	];

	// Validation: iteration is allowed when at least one preference is better and one is worse than current objectives
	let isIterationAllowed = $derived(() => {
		if (!problem || currentPreference.length === 0 || Object.keys(currentObjectives).length === 0) {
			return false;
		}

		let hasImprovement = false;
		let hasWorsening = false;

		for (let i = 0; i < problem.objectives.length; i++) {
			const objective = problem.objectives[i];
			const preferenceValue = currentPreference[i];
			const currentValue = currentObjectives[objective.symbol];

			if (preferenceValue === undefined || currentValue === undefined) {
				continue;
			}

			// Check if preference differs from current value. 
			// It does not matter what actually is better or worse as long as there is both
			if (preferenceValue > currentValue) {
				hasImprovement = true;
			} else if (preferenceValue < currentValue) {
				hasWorsening = true;
			}
		}

		// Need both improvement and worsening for valid NIMBUS classification
		return hasImprovement && hasWorsening;
	});

	function handleChange(event: { value: string }) {
		selectedTypeSolutions = event.value;
		console.log('Selected type of solutions:', selectedTypeSolutions);
	}


	// TODO: Handler for finishing the NIMBUS optimization process
	async function handleFinish(referencePointValues?: any) {
		console.log("TODO")
	}

	// The optional unused values are kept for compatibility with the AppSidebar component
	async function handleIterate(selectedPreference?: any, referencePointValues?: any) {
		if (!problem) {
			console.error('No problem selected');
			return;
		}
		if (currentPreference.length === 0) {
			console.error('No preferences set');
			return;
		}
		if (isIterationAllowed() === false) {
			console.error('Iteration not allowed based on current preferences and objectives');
			return;
		}	
		// TODO: are sessionId and parentStateId needed in some situations, and where should they come from?
		const sessionId = null;
		const parentStateId = null;
		const preference = {
			preference_type: "reference_point",
			aspiration_levels: problem.objectives.reduce((acc, obj, idx) => {
				acc[obj.symbol] = currentPreference[idx] || 0;
				return acc;
			}, {} as Record<string, number>)
		};
		try {
			const response = await fetch('/interactive_methods/NIMBUS/?type=iterate', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					problem_id: problem.id,
					session_id: sessionId,
					parent_state_id: parentStateId,
					current_objectives: currentObjectives,
					num_desired: currentNumSolutions,
					preference: preference,
				})
			});
			const result = await response.json();
			if (result.success) {
				// Store the preference values that were just used for iteration
				lastIteratedPreference = [...currentPreference];
				previousState = result.data
				updatePreferencesFromState(previousState);
				updateCurrentObjectivesFromState(previousState);
				currentNumSolutions = result.data.num_desired;
				console.log('NIMBUS iteration successful:', result.data);
			} else {
				console.error('NIMBUS iteration failed:', result.error);
			}
		} catch (error) {
			console.error('Error calling NIMBUS iterate:', error);
		}
	}

	// Helper function to update current objectives from the current state
	// TODO: rethink if-statements when state initialization works and StateWithResults changed
	function updateCurrentObjectivesFromState(state: StateWithResults | null) {
		if (!problem) return;
		if (!state || !state.solver_results || state.solver_results.length === 0) return;
			const selectedSolution = state.solver_results[0];
			if (selectedSolution && selectedSolution.optimal_objectives) {
				// Convert optimal_objectives to the format expected by the API
				const newObjectives: Record<string, number> = {};
				for (const [key, value] of Object.entries(selectedSolution.optimal_objectives)) {
					newObjectives[key] = Array.isArray(value) ? value[0] : value;
				}
				currentObjectives = newObjectives;
				console.log(`Updated current objectives from solution 1:`, currentObjectives);
			} else {
				console.warn('Selected solution is invalid, falling back to calculated average');
			}
	}

	// Helper function to initialize preferences from previous state or ideal values
	// TODO: rethink if-statements when state initialization works and StateWithResults changed
	function updatePreferencesFromState(state: StateWithResults | null) {
		if (!problem) return;
		// Try to get previous preference from NIMBUS state
		if (state && 'previous_preference' in state && state.previous_preference) {
			// Extract aspiration levels from previous preference
			const previousPref = state.previous_preference as { aspiration_levels?: Record<string, number> };
			if (previousPref.aspiration_levels) {
				currentPreference = problem.objectives.map(obj => 
					previousPref.aspiration_levels![obj.symbol] ?? obj.ideal ?? 0
				);
				console.log('Initialized preferences from previous state:', currentPreference);
				return;
			}
		}
		// Fallback to ideal values
		currentPreference = problem.objectives.map((obj) => obj.ideal ?? 0);
		console.log('Initialized preferences from ideal values:', currentPreference);
	}

	onMount(async () => {
		if ($methodSelection.selectedProblemId) {
			problem = problemList.find(
				(p: ProblemInfo) => String(p.id) === String($methodSelection.selectedProblemId)
			);

			if (problem) {
				// Initialize NIMBUS state from the API
				await initializeNimbusState(problem.id);
			}
		}
	});

	// Initialize NIMBUS state by calling the API endpoint
	async function initializeNimbusState(problemId: number) {
		try {
			const response = await fetch('/interactive_methods/NIMBUS/?type=initialize', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					problem_id: problemId,
					session_id: null, // Use active session
					parent_state_id: null, // No parent for initialization
					solver: null // Use default solver
				})
			});

			const result = await response.json();
			
			if (result.success) {
				previousState = result.data;
				updateCurrentObjectivesFromState(previousState);
				updatePreferencesFromState(previousState);
				currentNumSolutions = result.data.num_desired;
			} else {
				console.error('NIMBUS initialization failed:', result.error);
			}
		} catch (error) {
			console.error('Error initializing NIMBUS:', error);
		}
	}
</script>

<div class="flex min-h-[calc(100vh-3rem)]">	
	{#if problem}
		<AppSidebar 
			{problem} 
			preference_types={['Classification']} 
			showNumSolutions={true} 
			bind:preference={currentPreference}
			bind:numSolutions={currentNumSolutions}
			currentObjectives={currentObjectives}
			isIterationAllowed={isIterationAllowed()}
			minNumSolutions={1}
			maxNumSolutions={4}
			lastIteratedPreference={lastIteratedPreference}
			onIterate={handleIterate}
			onFinish={handleFinish}
		/>
	{/if}
	<div class="flex-1">
		<Resizable.PaneGroup direction="vertical">
			<Resizable.Pane class="p-2">
				<div class="flex-row">
					<div class="flex flex-row items-center justify-between gap-4 pb-2">
						<div class="font-semibold">Solution explorer</div>
						<div>
							<span>View: </span>
							<Combobox
								options={frameworks}
								defaultSelected={selectedTypeSolutions}
								onChange={handleChange}
							/>
						</div>
					</div>

					<div class="h-full w-full">
						<!-- Desktop: two columns, Mobile: two rows -->
						<div class="grid h-full w-full gap-4 xl:grid-cols-2">
							<div class="min-h-[50rem] flex-1 rounded bg-gray-100 p-4">
								<span>Objective space</span>
							</div>
							<div class="min-h-[50rem] flex-1 rounded bg-gray-100 p-4">
								<span>Decision space</span>
							</div>
						</div>
					</div>
				</div>
			</Resizable.Pane>
			<Resizable.Handle />
			<Resizable.Pane class="p-2">
				<Tabs.Root value="numerical-values">
					<Tabs.List>
						<Tabs.Trigger value="numerical-values">Numerical values</Tabs.Trigger>
						<Tabs.Trigger value="saved-solutions">Saved solutions</Tabs.Trigger>
					</Tabs.List>
					<Tabs.Content value="numerical-values">Table of solutions</Tabs.Content>
					<Tabs.Content value="saved-solutions">Visualize saved solutions</Tabs.Content>
				</Tabs.Root>
			</Resizable.Pane>
		</Resizable.PaneGroup>
	</div>
</div>
