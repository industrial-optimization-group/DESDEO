<script lang="ts">
	/**
	 * +page.svelte (Explainable NIMBUS method)
	 *
	 * @author Stina (Functionality) <palomakistina@gmail.com>
	 * @author Giomara Larraga (Base structure)<glarragw@jyu.fi>
	 * @created July 2025
	 *
	 * All the functionality is based on the NIMBUS UI created by Stina.
	 */
	import { ExplainableLayout as BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import { methodSelection } from '../../../stores/methodSelection';
	import { errorMessage, isLoading } from '../../../stores/uiState';
	import { onDestroy, onMount } from 'svelte';
	import LoadingSpinner from '$lib/components/custom/notifications/loading-spinner.svelte';
	import Alert from '$lib/components/custom/notifications/alert.svelte';

	import { Combobox } from '$lib/components/ui/combobox';
	import { SegmentedControl } from '$lib/components/custom/segmented-control';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import ResizableHandle from '$lib/components/ui/resizable/resizable-handle.svelte';
	import Button from '$lib/components/ui/button/button.svelte';
	import { openConfirmDialog, openInputDialog, openHelpDialog } from '$lib/components/custom/dialogs/dialogs';

	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import IntermediateSidebar from '$lib/components/custom/nimbus/intermediate-sidebar.svelte';
	import SolutionTable from '$lib/components/custom/nimbus/solution-table.svelte';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';

	import { PREFERENCE_TYPES } from '$lib/constants';
	import UtopiaMap from '$lib/components/custom/nimbus/utopia-map.svelte';

	import {
		checkUtopiaMetadata,
		mapSolutionsToObjectiveValues,
		updatePreferencesFromState,
		validateIterationAllowed,
		processPreviousObjectiveValues,
		updateSolutionNames,
		isInitialState
	} from './helper-functions';
	import AdvancedSidebar from '$lib/components/custom/preferences-bar/advanced-sidebar.svelte';

	import type { ProblemInfo, Solution, SolutionType, MethodMode, PeriodKey } from '$lib/types';
	import type { Response } from './types';
	import EndStateView from '../GNIMBUS/components/EndStateView.svelte';

	import {
		handle_intermediate as handleIntermediateRequest,
		handle_iterate as handleIterateRequest,
		handle_save as handleSaveRequest,
		handle_remove_saved as handleRemoveSavedRequest,
		handle_finish as handleFinishRequest,
		get_maps as getMapsRequest,
		initialize_nimbus_state as initializeNimbusStateRequest,
		handle_get_multipliers as handleGetMultipliersRequest
	} from './handlers';

	// State for NIMBUS iteration management
	let current_state: Response = $state({} as Response);

	let problem: ProblemInfo | null = $state(null);
	const { data } = $props<{ data: ProblemInfo[] }>();
	let problem_list = $derived(data.problems ?? []);
	let selected_type_solutions = $state('current');
	const frameworks = [
		{ value: 'current', label: 'Current solutions' },
		{ value: 'best', label: 'Saved solutions' },
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
	let selected_type_solutions_label = $derived.by(() => {
		const framework = frameworks.find((f) => f.value === selected_type_solutions);
		return framework ? framework.label : 'Solutions';
	});
	let mode: MethodMode = $state('iterate');
	let selected_iteration_index: number[] = $state([0]);
	let current_num_iteration_solutions: number = $state(1);
	let selected_iteration_objectives: Record<string, number> = $state({});
	let selected_intermediate_indexes: number[] = $state([]);
	let current_num_intermediate_solutions: number = $state(1);
	let selected_solutions_for_intermediate: Solution[] = $state([]);

	let selected_objective_symbol: string | null = $state(null);
	let selected_tradeoff_symbol: string | null = $state(null);

	const steps = [
		{ title: "Input preferences", text: "Use the sliders to set your preferences. You can also enter a numerical value in the text boxes next to each slider." },
		{ title: "Input number of solutions", text: "Enter the number of solutions you want to generate." },
		{ title: "Click on iterate", text: "Click the 'Iterate' button to generate solutions. The solutions will be visualized in the plot and table in the main view." },
		{ title: "Select a solution", text: "Click on a solution in the table or plot to select it." },
		{ title: "Iterate", text: "If you want to generate more solutions, adjust your preferences and click 'Iterate' again. If you are satisfied with the selected solution, click 'Finish'." }
	];

	// Reset selected tradeoff when selected objective changes
	$effect(() => {
		selected_objective_symbol;
		selected_tradeoff_symbol = null;
	});

	let selectedIndexes = $derived.by(() => {
		if (mode === 'intermediate') {
			return selected_intermediate_indexes;
		} else {
			return selected_iteration_index;
		}
	});
	let current_preference: number[] = $state([]);
	let last_iterated_preference: number[] = $state([]);
	let current_multipliers: Array<Record<string, number> | null> | null = $state(null);
	let current_tradeoffs: Array<Record<string, Record<string, number>> | null> | null = $state(null);
	let current_active_objectives: Array<Array<string>> = $state([]);
	let current_objective_values: Record<string, number> | null = $state(null);

	let hasUtopiaMetadata = $state(false);

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

	let is_iteration_allowed = $derived(() => {
		return validateIterationAllowed(problem, current_preference, selected_iteration_objectives);
	});

	function handle_type_solutions_change(event: { value: string }) {
		change_solution_type_updating_selections(event.value as SolutionType);
	}

	function handle_selected_objective_change(event: { value: string }) {
		selected_objective_symbol = event.value;
	}

	function handle_selected_tradeoff_change(event: { value: string }) {
		selected_tradeoff_symbol = event.value;
	}

	function change_solution_type_updating_selections(newType: SolutionType) {
		selected_type_solutions = newType;
		update_iteration_selection(current_state);
		update_intermediate_selection(current_state);
	}

	function handle_solution_click(index: number) {
		if (mode === 'iterate') {
			if (selected_iteration_index[0] === index) {
				return;
			}
			selected_iteration_index = [index];
			update_iteration_selection(current_state);
			selected_objective_symbol = null;
		} else if (mode === 'intermediate') {
			if (selected_intermediate_indexes.includes(index)) {
				selected_intermediate_indexes = selected_intermediate_indexes.filter((i) => i !== index);
			} else if (selected_intermediate_indexes.length < 2) {
				selected_intermediate_indexes = [...selected_intermediate_indexes, index];
			}
			update_intermediate_selection(current_state);
			selected_objective_symbol = null;
		}
	}

	function confirm_finish() {
		const selectedSolution = chosen_solutions[selectedIndexes[0]];
		const final_solution = { ...selectedSolution };
		const solutionName = selectedSolution.name || `Solution #${selectedIndexes[0] + 1}`;

		openConfirmDialog({
			title: 'Confirm Final Choice',
			description: `Are you sure you want to proceed with "${solutionName}" as your final choice?`,
			confirmText: 'Yes, Proceed',
			cancelText: 'Cancel',
			confirmVariant: 'destructive',
			onConfirm: () => handle_finish(final_solution, selectedIndexes[0])
		});
	}

	async function handle_finish(final_solution: Solution, index: number) {
		if (!current_state.previous_preference) {
			console.error('No previous preference values found for finishing.');
			return;
		}
		const response = await handleFinishRequest(problem, final_solution, current_state.previous_preference);
		if (response) {
			selected_iteration_index = [index];
			mode = 'final';
		}
	}

	async function handle_intermediate() {
		const result = await handleIntermediateRequest(
			problem,
			selected_solutions_for_intermediate,
			current_num_intermediate_solutions
		);

		if (result) {
			current_state = result;
			current_state.all_solutions = updateSolutionNames(
				current_state.saved_solutions,
				current_state.all_solutions
			);
			mode = 'iterate';
			selected_iteration_index = [0];
			change_solution_type_updating_selections('current');
		}
	}

	function handle_change(solution: Solution): void {
		openInputDialog({
			title: 'Rename Solution',
			description: 'Enter a name for this solution.',
			confirmText: 'Save',
			cancelText: 'Cancel',
			initialValue: solution.name || '',
			placeholder: 'Solution name',
			onConfirm: (name) => handle_save(solution, name)
		});
	}

	async function handle_save(solution: Solution, name: string | undefined) {
		const solutionToSave = { ...solution, name: name || null };

		const success = await handleSaveRequest(problem, solution, name);

		if (success) {
			const updateSolutionInList = (list: Solution[]) =>
				list.map((item) =>
					item.state_id === solution.state_id && item.solution_index === solution.solution_index
						? { ...solutionToSave, name: solutionToSave.name ?? null }
						: { ...item, name: item.name ?? null }
				);
			const existingIndex = current_state.saved_solutions.findIndex(
				(saved) =>
					saved.state_id === solution.state_id && saved.solution_index === solution.solution_index
			);
			let updatedSavedSolutions;
			if (existingIndex !== -1) {
				updatedSavedSolutions = [...current_state.saved_solutions];
				updatedSavedSolutions[existingIndex] = {
					...updatedSavedSolutions[existingIndex],
					name: name || null
				};
			} else {
				updatedSavedSolutions = [...current_state.saved_solutions, solutionToSave];
			}

			current_state = {
				...current_state,
				current_solutions: updateSolutionInList(current_state.current_solutions),
				saved_solutions: updatedSavedSolutions,
				all_solutions: updateSolutionInList(current_state.all_solutions)
			};
		}
	}

	function show_help_dialog() {
		openHelpDialog({
			title: 'How Explainable NIMBUS works',
			steps: steps,
			nextText: 'Next',
			cancelText: 'Close',
		});
	}

	function confirm_remove_saved(solution: Solution) {
		openConfirmDialog({
			title: 'Remove Saved Solution',
			description: `Are you sure you want to remove ${solution.name || 'this solution'} from saved solutions?`,
			confirmText: 'Remove',
			cancelText: 'Cancel',
			onConfirm: () => handle_remove_saved(solution)
		});
	}

	async function handle_remove_saved(solution: Solution) {
		const success = await handleRemoveSavedRequest(problem, solution);

		if (success) {
			const updatedSavedSolutions = current_state.saved_solutions.filter(
				(saved) =>
					!(
						saved.state_id === solution.state_id && saved.solution_index === solution.solution_index
					)
			);

			current_state = {
				...current_state,
				saved_solutions: updatedSavedSolutions
			};
		}
	}

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

		const result = await handleIterateRequest(
			problem,
			current_preference,
			selected_iteration_objectives,
			current_num_iteration_solutions
		);

		if (result) {
			current_state = result;
			current_state.all_solutions = updateSolutionNames(
				current_state.saved_solutions,
				current_state.all_solutions
			);
			selected_iteration_index = [0];
			selected_objective_symbol = null;
			change_solution_type_updating_selections('current');
			update_preferences_from_state(current_state, problem);
			current_num_iteration_solutions = current_state.current_solutions.length;

			// Fetch multipliers for the current solutions
			fetch_multipliers();
		}
	}

	async function fetch_multipliers() {
		if (!current_state || !current_state.state_id) {
			return;
		}
		const objective_symbols = problem?.objectives.map((obj) => obj.symbol) || [];

		const data = await handleGetMultipliersRequest(current_state.state_id, objective_symbols);
		if (data) {
			current_multipliers = data.lagrange_multipliers;
			current_tradeoffs = data.tradeoffs_matrix;
			current_active_objectives = data.active_objectives;
		} else {
			current_multipliers = null;
			current_tradeoffs = null;
			current_active_objectives = [];
		}
	}

	async function get_maps(solution: Solution) {
		if (!problem) {
			return;
		}

		const data = await getMapsRequest(problem, solution);

		if (data) {
			yearlist = data.years;
			mapOptions = {
				period1: data.options[yearlist[0]] || {},
				period2: data.options[yearlist[1]] || {},
				period3: data.options[yearlist[2]] || {}
			} as Record<PeriodKey, Record<string, any>>;
			geoJSON = data.map_json;
			mapName = data.map_name;
			mapDescription = data.description;
			compensation = Math.round(data.compensation * 100) / 100;
		}
	}

	function update_iteration_selection(state: Response | null) {
		if (!problem) return;
		if (!state) return;
		if (chosen_solutions.length === 0) return;
		if (selected_iteration_index[0] >= chosen_solutions.length) {
			selected_iteration_index = [0];
		}

		const selectedSolution = chosen_solutions[selected_iteration_index[0]];
		selected_iteration_objectives = selectedSolution.objective_values || {};
		selected_objective_symbol = null;

		if (hasUtopiaMetadata) {
			get_maps(selectedSolution);
		}
	}

	function update_preferences_from_state(state: Response | null, prob: ProblemInfo | null) {
		if (!prob) return;
		current_preference = updatePreferencesFromState(state, prob);
		last_iterated_preference = [...current_preference];
	}

	function update_intermediate_selection(state: Response | null) {
		if (!problem) return;
		if (!state) return;
		if (chosen_solutions.length === 0) return;

		const validIndexes = selected_intermediate_indexes.filter((i) => i < chosen_solutions.length);
		if (validIndexes.length !== selected_intermediate_indexes.length) {
			selected_intermediate_indexes = validIndexes;
		}

		selected_solutions_for_intermediate = selected_intermediate_indexes.map(
			(i) => chosen_solutions[i]
		);
	}

	function isSaved(solution: Solution): boolean {
		return current_state.saved_solutions.some(
			(saved) =>
				saved.state_id === solution.state_id && saved.solution_index === solution.solution_index
		);
	}

	onMount(async () => {
		methodSelection.set($methodSelection.selectedProblemId, 'Explainable NIMBUS');
		if ($methodSelection.selectedProblemId) {
			problem = problem_list.find(
				(p: ProblemInfo) => String(p.id) === String($methodSelection.selectedProblemId)
			);

			if (problem) {
				hasUtopiaMetadata = checkUtopiaMetadata(problem);
				await initialize_nimbus_state(problem.id);
			}
		}
	});

	onDestroy(() => {
		methodSelection.set(null, null);
	});

	async function initialize_nimbus_state(problem_id: number) {
		const result = await initializeNimbusStateRequest(problem_id);
		if (result) {
			let current_solutions = result.current_solutions || [];
			if (result.final_solution) {
				current_solutions = [result.final_solution]
			}
			current_state = {
				...result,
				current_solutions: current_solutions,
			};
			current_state.current_solutions = updateSolutionNames(
				current_state.saved_solutions,
				current_state.current_solutions
			);
			current_state.all_solutions = updateSolutionNames(
				current_state.saved_solutions,
				current_state.all_solutions
			);

			selected_iteration_index = [0];
			selected_objective_symbol = null;
			update_iteration_selection(current_state);
			update_preferences_from_state(current_state, problem);
			current_num_iteration_solutions = current_state.current_solutions.length;
		}
	}

	let type_preferences = $state(PREFERENCE_TYPES.Classification);

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

	export function areAllObjectivesTwiceDifferentiable(problem: ProblemInfo | null): boolean {
		if (!problem || !problem.objectives || problem.objectives.length === 0) {
			return false;
		}
		return problem.objectives.every((objective) => objective.is_twice_differentiable === true);
	}
</script>

{#if $isLoading}
	<LoadingSpinner />
{/if}

{#if $errorMessage}
	<Alert title="Error" message={$errorMessage} variant="destructive" />
{/if}

{#if mode === 'final'}
	<BaseLayout showLeftSidebar={false} showRightSidebar={false} bottomPanelTitle="Final Solution">
		{#snippet visualizationArea(height)}
			{#if problem && selected_iteration_index.length > 0}
				<div class="h-full">
					<Resizable.PaneGroup direction="horizontal" class="h-full">
						<Resizable.Pane defaultSize={65} minSize={40} class="h-full">
							<VisualizationsPanel
								{problem}
								previousPreferenceValues={[last_iterated_preference]}
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

						{#if hasUtopiaMetadata}
							<ResizableHandle withHandle class="border-l border-gray-200 shadow-sm" />
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
				<EndStateView {problem} tableData={[chosen_solutions[selected_iteration_index[0]] as any]} />
			{/if}
		{/snippet}
	</BaseLayout>
{:else}
	<BaseLayout
		showLeftSidebar={!!problem}
		showRightSidebar={areAllObjectivesTwiceDifferentiable(problem)}
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
			<span class="inline-block mr-0 ml-1">
				<Button onclick={show_help_dialog} variant="ghost" class="font-semibold text-primary underline">
					Quick Start
				</Button>
			</span>
			<SegmentedControl
				bind:value={mode}
				options={[
					{ value: 'iterate', label: 'Iterate' },
					{ value: 'intermediate', label: 'Find intermediate' }
				]}
				class="ml-0"
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
					class="ml-0"
				>
					Finish
				</Button>
			</span>
		{/snippet}

		{#snippet visualizationArea(height)}
			{#if problem && current_state}
				<div class="h-full">
					<Resizable.PaneGroup direction="horizontal" class="h-full">
						<Resizable.Pane defaultSize={65} minSize={40} maxSize={80} class="h-full">
							<VisualizationsPanel
								{problem}
								previousPreferenceValues={[last_iterated_preference]}
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
							<ResizableHandle withHandle class=" border-4 border-gray-200 shadow-sm" />
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
					secondaryObjectiveValues={selected_type_solutions === 'current'
						? problem
							? [
									...(current_state.previous_objectives ? [current_state.previous_objectives] : []),
									...(current_state.reference_solution_1
										? [current_state.reference_solution_1]
										: []),
									...(current_state.reference_solution_2
										? [current_state.reference_solution_2]
										: [])
								]
							: []
						: []}
				/>
			{/if}
		{/snippet}
		{#snippet rightSidebar()}
			{#if problem && chosen_solutions.length > 0 && selected_type_solutions === 'current'}
				<AdvancedSidebar
					{problem}
					preferenceValues={current_preference}
					solutions={chosen_solutions}
					multipliers={current_multipliers ? current_multipliers[selectedIndexes[0]] : null}
					tradeoffs={current_tradeoffs ? current_tradeoffs[selectedIndexes[0]] : null}
					activeObjectives={current_active_objectives ? current_active_objectives[selectedIndexes[0]] : []}
					currentObjectiveValues={current_objective_values}
					selectedSolutions={selectedIndexes}
					selectedObjectiveSymbol={selected_objective_symbol}
					handleObjectiveClick={handle_selected_objective_change}
					selectedTradeoffSymbol={selected_tradeoff_symbol}
					handleTradeoffClick={handle_selected_tradeoff_change}
				/>
			{/if}
		{/snippet}
	</BaseLayout>
{/if}
