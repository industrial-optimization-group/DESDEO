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
	import Table from '$lib/components/ui/table/table.svelte';
	import TableBody from '$lib/components/ui/table/table-body.svelte';
	import TableRow from '$lib/components/ui/table/table-row.svelte';
	import TableHead from '$lib/components/ui/table/table-head.svelte';
	import TableCell from '$lib/components/ui/table/table-cell.svelte';
	import ConfirmationDialog from '$lib/components/custom/confirmation-dialog.svelte';
	import SolutionTable from '$lib/components/custom/solution-table/solution-table.svelte';
	import { PREFERENCE_TYPES } from '$lib/constants';
	import { formatNumber, formatNumberArray } from '$lib/helpers';

	type ProblemInfo = components['schemas']['ProblemInfo'];

	// Define a general type for any state with solver_results
	// TODO: This type will be rethought and not needed when API has changed (Vili is supposed to refactor responses).
	type StateWithResults = {
		solver_results: Array<{
			optimal_objectives: Record<string, number | number[]>;
			[key: string]: any;
		}>;
		[key: string]: any;
	};
	let finalChoiceState = $state(false);

	let problem: ProblemInfo | null = $state(null);
	const { data } = $props<{ data: ProblemInfo[] }>();
	let problem_list = data.problems ?? [];
	let selected_type_solutions = $state('current');

	// State for NIMBUS iteration management
	let previousState: StateWithResults | null = $state(null);
	let currentSolutionIndex: number = $state(0); // Which solution from previous results to use in sidebar

	// currentPreference is initialized from previous_preference or ideal values
	let currentPreference: number[] = $state([]);
	let currentNumSolutions: number = $state(1);
	// Selected objectives for the sidebar
	// TODO: selectedObjectives is used for both AppSidebar and iteration request,
	// but when intermediate-button is implemented, they cant be the same, since request needs two and AppSidebar still uses only one.
	// so updateSelectedObjectives() needs changes, selectedObjectives needs to be both a list for request and one objective for sidebar.
	// And requests (and button disabling) need to check how many items the list has.
	let selectedObjectives: Record<string, number> = $state({});
	// Store the last iterated preference values to show as "previous" in UI
	let lastIteratedPreference: number[] = $state([]);

	const frameworks = [
		{ value: 'current', label: 'Current solutions' },
		{ value: 'best', label: 'Best solutions' },
		{ value: 'all', label: 'All solutions' }
	];

	// Validation: iteration is allowed when at least one preference is better and one is worse than current objectives
	function isIterationAllowed(): boolean {
		console.log('Validation check:', {
			problem: !!problem,
			problemId: problem?.id,
			currentPreferenceLength: currentPreference.length,
			currentPreference: currentPreference,
			selectedObjectivesCount: Object.keys(selectedObjectives).length,
			selectedObjectives: selectedObjectives
		});

		if (
			!problem ||
			currentPreference.length === 0 ||
			Object.keys(selectedObjectives).length === 0
		) {
			console.error('Iteration not allowed: problem or preferences are not set');
			return false;
		}

		let hasImprovement = false;
		let hasWorsening = false;

		for (let i = 0; i < problem.objectives.length; i++) {
			const objective = problem.objectives[i];
			const preferenceValue = currentPreference[i];
			const currentValue = selectedObjectives[objective.symbol];

			console.log(
				`Checking preference for ${objective.symbol}: preference=${preferenceValue}, current=${currentValue}`
			);
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
	}

	function handleChange(event: { value: string }) {
		selected_type_solutions = event.value;
		console.log('Selected type of solutions:', selected_type_solutions);
	}

	// TODO: Handler for finishing the NIMBUS optimization process
	let showConfirmDialog: boolean = $state(false);

	function handlePressFinish() {
		showConfirmDialog = true;
	}

	async function handleFinish() {
		try {
			const response = await fetch('/interactive_methods/NIMBUS/?type=choose', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					problem_id: problem?.id,
					solution: currentSolutionIndex // Assuming single selection for final choice, need a check that the list only has one item
				})
			});

			const result = await response.json();

			if (result.success) {
				finalChoiceState = true;
				console.log(result.message);
			} else {
				console.error('Failed to save final choice:', result.error);
			}
		} catch (error) {
			console.error('Error calling mock endpoint:', error);
		}
	}

	// The optional unused values are kept for compatibility with the AppSidebar component
	async function handleIterate(data: {
		num_solutions: number;
		type_preferences: string;
		preference_values: number[];
		objective_values: number[];
	}) {
		if (!problem) {
			console.error('No problem selected');
			return;
		}
		if (currentPreference.length === 0) {
			console.error('No preferences set');
			return;
		}
		if (!isIterationAllowed()) {
			console.error('Iteration not allowed based on current preferences and objectives');
			return;
		}

		const sessionId = null;
		const parentStateId = null;
		const preference = {
			preference_type: 'reference_point',
			aspiration_levels: problem.objectives.reduce(
				(acc, obj, idx) => {
					acc[obj.symbol] = currentPreference[idx] || 0;
					return acc;
				},
				{} as Record<string, number>
			)
		};

		try {
			const response = await fetch('/interactive_methods/NIMBUS/?type=iterate', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					problem_id: problem.id,
					session_id: sessionId,
					parent_state_id: parentStateId,
					current_objectives: selectedObjectives,
					num_desired: currentNumSolutions,
					preference: preference
				})
			});

			const result = await response.json();
			if (result.success) {
				// Store the preference values that were just used for iteration
				lastIteratedPreference = [...currentPreference];
				previousState = result.data;
				updatePreferencesFromState(previousState);
				currentSolutionIndex = 0;
				updateSelectedObjectives(previousState);
				currentNumSolutions = result.data.num_desired ? result.data.num_desired : 1; // TODO: this will be just the number of recent solutions
				console.log('NIMBUS iteration successful:', result.data);
			} else {
				console.error('NIMBUS iteration failed:', result.error);
			}
		} catch (error) {
			console.error('Error calling NIMBUS iterate:', error);
		}
	}

	// Helper function to update current objectives from the current state
	// TODO: rethink and see if changes needed, after StateWithResults has changed (Vili)
	function updateSelectedObjectives(state: StateWithResults | null) {
		if (!problem) return;
		if (!state || !state.solver_results || state.solver_results.length === 0) return;
		const selectedSolution = state.solver_results[currentSolutionIndex];
		if (selectedSolution && selectedSolution.optimal_objectives) {
			// Convert optimal_objectives to the format expected by the API
			const newObjectives: Record<string, number> = {};
			for (const [key, value] of Object.entries(selectedSolution.optimal_objectives)) {
				newObjectives[key] = Array.isArray(value) ? value[0] : value;
			}
			selectedObjectives = newObjectives;
			console.log(
				`Updated current objectives from solution `,
				currentSolutionIndex + 1,
				`:`,
				selectedObjectives
			);
		} else {
			console.warn('Selected solution is invalid, falling back to calculated average');
		}
	}

	// Helper function to initialize preferences from previous state or ideal values
	// TODO: rethink and see if changes needed, after StateWithResults has changed (Vili)
	function updatePreferencesFromState(state: StateWithResults | null) {
		if (!problem) return;
		// Try to get previous preference from NIMBUS state
		if (state && 'previous_preference' in state && state.previous_preference) {
			// Extract aspiration levels from previous preference
			const previousPref = state.previous_preference as {
				aspiration_levels?: Record<string, number>;
			};
			if (previousPref.aspiration_levels) {
				currentPreference = problem.objectives.map(
					(obj) => previousPref.aspiration_levels![obj.symbol] ?? obj.ideal ?? 0
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
			problem = problem_list.find(
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
					'Content-Type': 'application/json'
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
				currentSolutionIndex = 0;
				updateSelectedObjectives(previousState);
				updatePreferencesFromState(previousState);
				currentNumSolutions = result.data.num_desired ? result.data.num_desired : 1; // TODO: of course this will be just the number of solutions: it always exists
			} else {
				console.error('NIMBUS initialization failed:', result.error);
			}
		} catch (error) {
			console.error('Error initializing NIMBUS:', error);
		}
	}

	// Convert data to match AppSidebar interface
	let type_preferences = $state(PREFERENCE_TYPES.Classification);

	// Add the missing callback that updates internal state
	function handlePreferenceChange(data: {
		num_solutions: number;
		type_preferences: string;
		preference_values: number[];
		objective_values: number[];
	}) {
		currentNumSolutions = data.num_solutions;
		type_preferences = data.type_preferences;
		currentPreference = [...data.preference_values];
		console.log('Preference changed:', data);
	}
</script>

{#if finalChoiceState}
	<div class="card">
		<div class="card-header">Solution Review</div>
		{#if problem && previousState?.solver_results[currentSolutionIndex]}
			<div class="card-body">
				<h3>Selected Solution Objectives:</h3>
				<Table>
					<TableBody>
						<TableRow>
							{#each problem.objectives as objective}
								<TableHead>
									{objective.name}
									{objective.unit ? `/ ${objective.unit}` : ''}
								</TableHead>
							{/each}
						</TableRow>
						<TableRow>
							{#each problem.objectives as objective}
								<TableCell>
									{previousState.solver_results[currentSolutionIndex].optimal_objectives[
										objective.symbol
									]}
								</TableCell>
							{/each}
						</TableRow>
					</TableBody>
				</Table>
				<div class="grid h-full w-full gap-4 xl:grid-cols-2">
					<div class="min-h-[50rem] flex-1 rounded bg-gray-100 p-4">
						<span>Objective space</span>
					</div>
					<div class="min-h-[50rem] flex-1 rounded bg-gray-100 p-4">
						<span>Decision space</span>
					</div>
				</div>
			</div>
		{:else}
			<div class="card-body">
				<p>Error: Unable to display the selected solution.</p>
			</div>
		{/if}
	</div>
{:else}
	<div class="flex min-h-[calc(100vh-3rem)]">
		{#if problem}
			<div class="flex flex-col">
				<AppSidebar
					{problem}
					preference_types={[PREFERENCE_TYPES.Classification]}
					showNumSolutions={true}
					num_solutions={currentNumSolutions}
					{type_preferences}
					preference_values={currentPreference}
					objective_values={Object.values(selectedObjectives)}
					isIterationAllowed={isIterationAllowed()}
					isFinishAllowed={true}
					minNumSolutions={1}
					maxNumSolutions={4}
					{lastIteratedPreference}
					onPreferenceChange={handlePreferenceChange}
					onIterate={handleIterate}
					onFinish={handleFinish}
				/>
			</div>
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
									defaultSelected={selected_type_solutions}
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
						<Tabs.Content value="numerical-values">
							{#if problem && previousState?.solver_results && previousState.solver_results.length > 0}
								<SolutionTable
									{problem}
									solverResults={previousState.solver_results}
									bind:selectedSolution={currentSolutionIndex}
									onRowClick={() => updateSelectedObjectives(previousState)}
								/>
							{/if}
						</Tabs.Content>
						<Tabs.Content value="saved-solutions">Visualize saved solutions</Tabs.Content>
					</Tabs.Root>
				</Resizable.Pane>
			</Resizable.PaneGroup>
		</div>
	</div>
{/if}

<ConfirmationDialog
	bind:open={showConfirmDialog}
	title="Confirm Final Choice"
	description="Are you sure you want to proceed with this solution as your final choice?"
	confirmText="Yes, Proceed"
	cancelText="Cancel"
	onConfirm={handleFinish}
	onCancel={() => console.log('Cancelled')}
/>
