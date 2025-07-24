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
	import { BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import type { components } from '$lib/api/client-types';
	import { onMount } from 'svelte';
	import { Combobox } from '$lib/components/ui/combobox';
	import Table from '$lib/components/ui/table/table.svelte';
	import TableBody from '$lib/components/ui/table/table-body.svelte';
	import TableRow from '$lib/components/ui/table/table-row.svelte';
	import TableHead from '$lib/components/ui/table/table-head.svelte';
	import TableCell from '$lib/components/ui/table/table-cell.svelte';
	import ConfirmationDialog from '$lib/components/custom/confirmation-dialog.svelte';
	import SolutionTable from '$lib/components/custom/solution-table/solution-table.svelte';
	import { PREFERENCE_TYPES } from '$lib/constants';

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

	let final_choice_state = $state(false);

	let problem: ProblemInfo | null = $state(null);
	const { data } = $props<{ data: ProblemInfo[] }>();
	let problem_list = data.problems ?? [];
	let selected_type_solutions = $state('current');

	// State for NIMBUS iteration management
	let previous_state: StateWithResults | null = $state(null);
	let current_solution_index: number = $state(0); // Which solution from previous results to use in sidebar

	// currentPreference is initialized from previous_preference or ideal values
	let current_preference: number[] = $state([]);
	let current_num_solutions: number = $state(1);
	// Selected objectives for the sidebar
	// TODO: selectedObjectives is used for both AppSidebar and iteration request,
	// but when intermediate-button is implemented, they cant be the same, since request needs two and AppSidebar still uses only one.
	// so updateSelectedObjectives() needs changes, selectedObjectives needs to be both a list for request and one objective for sidebar.
	// And requests (and button disabling) need to check how many items the list has.
	let selected_objectives: Record<string, number> = $state({});
	// Store the last iterated preference values to show as "previous" in UI
	let last_iterated_preference: number[] = $state([]);

	const frameworks = [
		{ value: 'current', label: 'Current solutions' },
		{ value: 'best', label: 'Best solutions' },
		{ value: 'all', label: 'All solutions' }
	];

	// Validation: iteration is allowed when at least one preference is better and one is worse than current objectives
	function is_iteration_allowed(): boolean {
		console.log('Validation check:', {
			problem: !!problem,
			problemId: problem?.id,
			currentPreferenceLength: current_preference.length,
			currentPreference: current_preference,
			selectedObjectivesCount: Object.keys(selected_objectives).length,
			selectedObjectives: selected_objectives
		});

		if (
			!problem ||
			current_preference.length === 0 ||
			Object.keys(selected_objectives).length === 0
		) {
			console.error('Iteration not allowed: problem or preferences are not set');
			return false;
		}

		let has_improvement = false;
		let has_worsening = false;

		for (let i = 0; i < problem.objectives.length; i++) {
			const objective = problem.objectives[i];
			const preference_value = current_preference[i];
			const current_value = selected_objectives[objective.symbol];

			console.log(
				`Checking preference for ${objective.symbol}: preference=${preference_value}, current=${current_value}`
			);
			if (preference_value === undefined || current_value === undefined) {
				continue;
			}

			// Check if preference differs from current value.
			// It does not matter what actually is better or worse as long as there is both
			if (preference_value > current_value) {
				has_improvement = true;
			} else if (preference_value < current_value) {
				has_worsening = true;
			}
		}

		// Need both improvement and worsening for valid NIMBUS classification
		return has_improvement && has_worsening;
	}

	function handle_change(event: { value: string }) {
		selected_type_solutions = event.value;
		console.log('Selected type of solutions:', selected_type_solutions);
	}

	// TODO: Handler for finishing the NIMBUS optimization process
	let show_confirm_dialog: boolean = $state(false);

	function handle_press_finish() {
		show_confirm_dialog = true;
	}

	async function handle_finish() {
		try {
			const response = await fetch('/interactive_methods/NIMBUS/?type=choose', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					problem_id: problem?.id,
					solution: current_solution_index // Assuming single selection for final choice, need a check that the list only has one item
				})
			});

			const result = await response.json();

			if (result.success) {
				final_choice_state = true;
				console.log(result.message);
			} else {
				console.error('Failed to save final choice:', result.error);
			}
		} catch (error) {
			console.error('Error calling mock endpoint:', error);
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

		const session_id = null;
		const parent_state_id = null;
		const preference = {
			// TODO: change this to PREFERENCE_TYPES.CLASSIFICATION
			preference_type: 'reference_point',
			aspiration_levels: problem.objectives.reduce(
				(acc, obj, idx) => {
					acc[obj.symbol] = current_preference[idx] || 0;
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
					session_id: session_id,
					parent_state_id: parent_state_id,
					current_objectives: selected_objectives,
					num_desired: current_num_solutions,
					preference: preference
				})
			});

			const result = await response.json();
			if (result.success) {
				// Store the preference values that were just used for iteration
				last_iterated_preference = [...current_preference];
				previous_state = result.data;
				update_preferences_from_state(previous_state);
				current_solution_index = 0;
				update_selected_objectives(previous_state);
				current_num_solutions = result.data.num_desired ? result.data.num_desired : 1; // TODO: this will be just the number of recent solutions
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
	function update_selected_objectives(state: StateWithResults | null) {
		if (!problem) return;
		if (!state || !state.solver_results || state.solver_results.length === 0) return;
		const selected_solution = state.solver_results[current_solution_index];
		if (selected_solution && selected_solution.optimal_objectives) {
			// Convert optimal_objectives to the format expected by the API
			const new_objectives: Record<string, number> = {};
			for (const [key, value] of Object.entries(selected_solution.optimal_objectives)) {
				new_objectives[key] = Array.isArray(value) ? value[0] : value;
			}
			selected_objectives = new_objectives;
			console.log(
				`Updated current objectives from solution `,
				current_solution_index + 1,
				`:`,
				selected_objectives
			);
		} else {
			console.warn('Selected solution is invalid, falling back to calculated average');
		}
	}

	// Helper function to initialize preferences from previous state or ideal values
	// TODO: rethink and see if changes needed, after StateWithResults has changed (Vili)
	function update_preferences_from_state(state: StateWithResults | null) {
		if (!problem) return;
		// Try to get previous preference from NIMBUS state
		if (state && 'previous_preference' in state && state.previous_preference) {
			// Extract aspiration levels from previous preference
			const previous_pref = state.previous_preference as {
				aspiration_levels?: Record<string, number>;
			};
			if (previous_pref.aspiration_levels) {
				current_preference = problem.objectives.map(
					(obj) => previous_pref.aspiration_levels![obj.symbol] ?? obj.ideal ?? 0
				);
				console.log('Initialized preferences from previous state:', current_preference);
				return;
			}
		}
		// Fallback to ideal values
		current_preference = problem.objectives.map((obj) => obj.ideal ?? 0);
		console.log('Initialized preferences from ideal values:', current_preference);
	}

	onMount(async () => {
		if ($methodSelection.selectedProblemId) {
			problem = problem_list.find(
				(p: ProblemInfo) => String(p.id) === String($methodSelection.selectedProblemId)
			);

			if (problem) {
				// Initialize NIMBUS state from the API
				await initialize_nimbus_state(problem.id);
			}
		}
	});

	// Initialize NIMBUS state by calling the API endpoint
	async function initialize_nimbus_state(problem_id: number) {
		try {
			const response = await fetch('/interactive_methods/NIMBUS/?type=initialize', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					problem_id: problem_id,
					session_id: null, // Use active session
					parent_state_id: null, // No parent for initialization
					solver: null // Use default solver
				})
			});

			const result = await response.json();

			if (result.success) {
				previous_state = result.data;
				current_solution_index = 0;
				update_selected_objectives(previous_state);
				update_preferences_from_state(previous_state);
				current_num_solutions = result.data.num_desired ? result.data.num_desired : 1; // TODO: of course this will be just the number of solutions: it always exists
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
	function handle_preference_change(data: {
		numSolutions: number;
		typePreferences: string;
		preferenceValues: number[];
		objectiveValues: number[];
	}) {
		current_num_solutions = data.numSolutions;
		type_preferences = data.typePreferences;
		current_preference = [...data.preferenceValues];
		console.log('Preference changed:', data);
	}
</script>

{#if final_choice_state}
	<div class="card">
		<div class="card-header">Solution Review</div>
		{#if problem && previous_state?.solver_results[current_solution_index]}
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
									{previous_state.solver_results[current_solution_index].optimal_objectives[
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
	<BaseLayout showLeftSidebar={!!problem} showRightSidebar={false}>
		{#snippet leftSidebar()}
			{#if problem}
				<AppSidebar
					{problem}
					preferenceTypes={[PREFERENCE_TYPES.Classification]}
					showNumSolutions={true}
					numSolutions={current_num_solutions}
					typePreferences={type_preferences}
					preferenceValues={current_preference}
					objectiveValues={Object.values(selected_objectives)}
					isIterationAllowed={is_iteration_allowed()}
					isFinishAllowed={true}
					minNumSolutions={1}
					maxNumSolutions={4}
					lastIteratedPreference={last_iterated_preference}
					onPreferenceChange={handle_preference_change}
					onIterate={handle_iterate}
					onFinish={handle_press_finish}
				/>
			{/if}
		{/snippet}

		{#snippet explorerControls()}
			<span>View: </span>
			<Combobox
				options={frameworks}
				defaultSelected={selected_type_solutions}
				onChange={handle_change}
			/>
		{/snippet}

		{#snippet visualizationArea()}
			<div class="grid h-full w-full grid-cols-2 gap-6">
				<div class="w-full rounded border bg-gray-50 p-4">
					<span class="font-medium">Objective space</span>
				</div>
				<div class="w-full rounded border bg-gray-50 p-4">
					<span class="font-medium">Decision space</span>
				</div>
			</div>
		{/snippet}

		{#snippet numericalValues()}
			{#if problem && previous_state?.solver_results && previous_state.solver_results.length > 0}
				<SolutionTable
					{problem}
					solverResults={previous_state.solver_results}
					bind:selectedSolution={current_solution_index}
					onRowClick={() => update_selected_objectives(previous_state)}
				/>
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
	onCancel={() => console.log('Cancelled')}
/>
