<script lang="ts">
	// Layout and core components
	import { BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import { methodSelection } from '../../../stores/methodSelection';
	import { errorMessage, isLoading } from '../../../stores/uiState';
	import { onMount } from 'svelte';
	import LoadingSpinner from '$lib/components/custom/notifications/loading-spinner.svelte';
	import Alert from '$lib/components/custom/notifications/alert.svelte';

	// UI Components
	import { Combobox } from '$lib/components/ui/combobox';
	import { SegmentedControl } from '$lib/components/custom/segmented-control';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import ResizableHandle from '$lib/components/ui/resizable/resizable-handle.svelte';
	import Button from '$lib/components/ui/button/button.svelte';
	import { openConfirmDialog, openInputDialog } from '$lib/components/custom/dialogs/dialogs';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import Checkbox from '$lib/components/ui/checkbox/checkbox.svelte';

	// Shared components (reused from NIMBUS)
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import IntermediateSidebar from '$lib/components/custom/nimbus/intermediate-sidebar.svelte';
	import SolutionTable from '$lib/components/custom/nimbus/solution-table.svelte';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';
	import UtopiaMap from '$lib/components/custom/nimbus/utopia-map.svelte';
	import SolutionDescriptionPanel from '$lib/components/custom/nimbus/solution-description-panel.svelte';
	import { PREFERENCE_TYPES } from '$lib/constants';

	// Utility functions (reused from NIMBUS — logic is identical)
	import {
		checkUtopiaMetadata,
		checkSolutionDescription,
		mapSolutionsToObjectiveValues,
		updatePreferencesFromState,
		processPreviousObjectiveValues,
		updateSolutionNames
	} from '../NIMBUS/helper-functions';

	import type { ProblemInfo, Solution, SolutionType, MethodMode, PeriodKey } from '$lib/types';
	import type { Response, MapState } from './types';

	let current_state: Response = $state({} as Response);

	let problem: ProblemInfo | null = $state(null);
	const { data } = $props<{ data: ProblemInfo[] }>();
	let problem_list = $derived(data.problems ?? []);

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

	let selected_type_solutions_label = $derived.by(() => {
		const framework = frameworks.find((f) => f.value === selected_type_solutions);
		return framework ? framework.label : 'Solutions';
	});

	let mode: MethodMode = $state('iterate');
	let selected_iteration_index: number[] = $state([0]);
	const AVAILABLE_SCALARIZATIONS = [
		{ value: 'cumulonimbus', label: 'Cumulonimbus' },
		{ value: 'asf_partial_diff', label: 'ASF (differentiable)' },
		{ value: 'asf_partial_nondiff', label: 'ASF (non-differentiable)' }
	];

	let current_num_iteration_solutions: number = $state(1);
	let selected_scalarizations: string[] = $state(['cumulonimbus']);
	let selected_iteration_objectives: Record<string, number> = $state({});
	let selected_intermediate_indexes: number[] = $state([]);
	let current_num_intermediate_solutions: number = $state(1);
	let selected_solutions_for_intermediate: Solution[] = $state([]);

	let selectedIndexes = $derived.by(() => {
		if (mode === 'intermediate') {
			return selected_intermediate_indexes;
		} else {
			return selected_iteration_index;
		}
	});

	let current_preference: number[] = $state([]);
	let last_iterated_preference: number[] = $state([]);

	// Active objectives — symbols of objectives currently shown in the UI.
	// Populated on problem load; always holds the full set by default.
	let active_objective_symbols = $state(new Set<string>());
	let show_objectives_dialog = $state(false);
	let show_scalarizations_dialog = $state(false);

	$effect(() => {
		if (problem && active_objective_symbols.size === 0) {
			active_objective_symbols = new Set(problem.objectives.map((o) => o.symbol));
		}
	});

	// Indices into the full problem.objectives array that are currently active.
	let active_indices = $derived.by(() => {
		if (!problem) return [] as number[];
		return problem.objectives
			.map((o, i) => (active_objective_symbols.has(o.symbol) ? i : -1))
			.filter((i) => i >= 0);
	});

	// A copy of the problem containing only active objectives — passed to all display components.
	let filtered_problem = $derived.by(() => {
		if (!problem) return null;
		return {
			...problem,
			objectives: problem.objectives.filter((o) => active_objective_symbols.has(o.symbol))
		} as ProblemInfo;
	});

	// Preference and objective value arrays sliced to active objectives only.
	let filtered_preference = $derived(active_indices.map((i) => current_preference[i] ?? 0));
	let filtered_last_iterated_preference = $derived(
		active_indices.map((i) => last_iterated_preference[i] ?? 0)
	);
	let filtered_objective_values = $derived(
		active_indices.map((i) => {
			const sym = problem?.objectives[i]?.symbol;
			return sym ? (selected_iteration_objectives[sym] ?? 0) : 0;
		})
	);

	let hasUtopiaMetadata = $state(false);
	let hasSolutionDescription = $state(false);
	let solutionDescription = $state<string | null>(null);

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

	let is_iteration_allowed = $derived(() => {
		return problem !== null && current_preference.length > 0;
	});

	function handle_type_solutions_change(event: { value: string }) {
		change_solution_type_updating_selections(event.value as SolutionType);
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
		} else if (mode === 'intermediate') {
			if (selected_intermediate_indexes.includes(index)) {
				selected_intermediate_indexes = selected_intermediate_indexes.filter((i) => i !== index);
			} else if (selected_intermediate_indexes.length < 2) {
				selected_intermediate_indexes = [...selected_intermediate_indexes, index];
			}
			update_intermediate_selection(current_state);
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

	import {
		handle_intermediate as handleIntermediateRequest,
		handle_iterate as handleIterateRequest,
		handle_save as handleSaveRequest,
		handle_remove_saved as handleRemoveSavedRequest,
		handle_finish as handleFinishRequest,
		get_maps as getMapsRequest,
		get_solution_description as getSolutionDescriptionRequest,
		initialize_cumulus_state as initializeCumulusStateRequest
	} from './handlers';
	import EndStateView from '../GNIMBUS/components/EndStateView.svelte';

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
			filtered_problem ?? problem,
			filtered_preference,
			selected_iteration_objectives,
			current_num_iteration_solutions,
			selected_scalarizations
		);

		if (result) {
			current_state = result;

			current_state.all_solutions = updateSolutionNames(
				current_state.saved_solutions,
				current_state.all_solutions
			);

			selected_iteration_index = [0];
			change_solution_type_updating_selections('current');
			update_preferences_from_state(current_state);
			current_num_iteration_solutions = current_state.current_solutions.length;
		}
	}

	async function get_maps(solution: Solution, solutionIndex: number) {
		if (!problem) {
			console.error('No problem selected');
			return;
		}

		try {
			const data = await getMapsRequest(problem, solution);

			if (data) {
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

				for (let year of newMapState.yearlist) {
					if (data.options[year]?.tooltip?.formatterEnabled) {
						data.options[year].tooltip.formatter = function (params: any) {
							return `${params.name}`;
						};
					}
				}

				newMapState.mapOptions = {
					period1: data.options[newMapState.yearlist[0]] || {},
					period2: data.options[newMapState.yearlist[1]] || {},
					period3: data.options[newMapState.yearlist[2]] || {}
				} as Record<PeriodKey, Record<string, any>>;

				mapStates[solutionIndex] = newMapState;
				if (solutionIndex === selected_iteration_index[0]) {
					mapState = { ...newMapState };
				}
			}
		} catch (error) {
			console.error(`Failed to get maps for solution ${solutionIndex}:`, error);
		}
	}

	$effect(() => {
		if (hasUtopiaMetadata && chosen_solutions.length > 0) {
			mapStates = new Array(chosen_solutions.length);
			chosen_solutions.forEach((solution, index) => {
				get_maps(solution, index);
			});
		}
	});

	function update_iteration_selection(state: Response | null) {
		if (!problem) return;
		if (!state) return;
		if (chosen_solutions.length === 0) return;

		if (selected_iteration_index[0] >= chosen_solutions.length) {
			selected_iteration_index = [0];
		}

		const selectedSolution = chosen_solutions[selected_iteration_index[0]];
		selected_iteration_objectives = selectedSolution.objective_values || {};

		if (hasUtopiaMetadata && selected_iteration_index[0] >= 0 && mapStates[selected_iteration_index[0]]) {
			mapState = { ...mapStates[selected_iteration_index[0]] };
		}

		if (hasSolutionDescription && problem) {
			getSolutionDescriptionRequest(problem, selectedSolution).then((desc) => {
				solutionDescription = desc;
			});
		}
	}

	function update_preferences_from_state(state: Response | null) {
		if (!problem) return;
		current_preference = updatePreferencesFromState(state as any, problem);
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
		if ($methodSelection.selectedProblemId) {
			problem = problem_list.find(
				(p: ProblemInfo) => String(p.id) === String($methodSelection.selectedProblemId)
			);

			if (problem) {
				hasUtopiaMetadata = checkUtopiaMetadata(problem);
				hasSolutionDescription = !hasUtopiaMetadata && checkSolutionDescription(problem);

				await initialize_cumulus_state(problem.id);
			}
		}
	});

	async function initialize_cumulus_state(problem_id: number) {
		const result = await initializeCumulusStateRequest(problem_id);
		if (result) {
			let current_solutions = result.current_solutions || [];
			if (result.final_solution) {
				current_solutions = [result.final_solution];
			}
			current_state = {
				...result,
				current_solutions: current_solutions
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
			update_iteration_selection(current_state);
			update_preferences_from_state(current_state);
			current_num_iteration_solutions = current_state.current_solutions.length;
			if (current_state.response_type === 'cumulus.finalize') {
				mode = 'final';
			}
		}
	}

	let type_preferences = $state(PREFERENCE_TYPES.ReferencePoint);

	function handle_preference_change(data: {
		numSolutions: number;
		typePreferences: string;
		preferenceValues: number[];
		objectiveValues: number[];
	}) {
		current_num_iteration_solutions = data.numSolutions;
		type_preferences = data.typePreferences;
		// data.preferenceValues is indexed over active objectives only;
		// map the values back into the full-length current_preference array.
		const updated = [...current_preference];
		active_indices.forEach((fullIdx, filteredIdx) => {
			updated[fullIdx] = data.preferenceValues[filteredIdx];
		});
		current_preference = updated;
	}
</script>

<svelte:head>
	<title>CUMULUS | DESDEO</title>
	<meta name="description" content="This page implements the CUMULUS interactive multiobjective optimization method in DESDEO" />
</svelte:head>

{#if $isLoading}
	<LoadingSpinner />
{/if}

{#if $errorMessage}
	<Alert
		title="Error"
		message={$errorMessage}
		variant='destructive'
	/>
{/if}

{#if mode === 'final'}
	<BaseLayout showLeftSidebar={false} showRightSidebar={false} bottomPanelTitle="Final Solution">
		{#snippet visualizationArea()}
			{#if filtered_problem && selected_iteration_index.length > 0}
				<div class="h-full">
					<Resizable.PaneGroup direction="horizontal" class="h-full">
						<Resizable.Pane defaultSize={65} minSize={40} class="h-full">
							<VisualizationsPanel
								problem={filtered_problem}
								previousPreferenceValues={[filtered_last_iterated_preference]}
								previousPreferenceType={type_preferences}
								currentPreferenceValues={[]}
								currentPreferenceType={type_preferences}
								solutionsObjectiveValues={mapSolutionsToObjectiveValues(
									[chosen_solutions[selected_iteration_index[0]]],
									filtered_problem
								)}
								externalSelectedIndexes={selected_iteration_index}
								onSelectSolution={() => {}}
							/>
						</Resizable.Pane>

						{#if hasUtopiaMetadata}
							<ResizableHandle withHandle class="border-l border-gray-200 shadow-sm" />
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
						{:else if hasSolutionDescription}
							<ResizableHandle withHandle class="border-l border-gray-200 shadow-sm" />
							<Resizable.Pane defaultSize={35} minSize={20} class="h-full">
								<SolutionDescriptionPanel description={solutionDescription} />
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
		showRightSidebar={false}
		bottomPanelTitle={selected_type_solutions_label}
	>
		{#snippet leftSidebar()}
			{#snippet footerButtons()}
				<Button
					variant="outline"
					size="sm"
					onclick={() => (show_objectives_dialog = true)}
				>
					Choose Objectives
				</Button>
				<Button
					variant="outline"
					size="sm"
					onclick={() => (show_scalarizations_dialog = true)}
				>
					Scalarizations: {selected_scalarizations.length}
				</Button>
			{/snippet}

			{#if problem && mode === 'iterate'}
				<AppSidebar
					problem={filtered_problem ?? problem}
					preferenceTypes={[PREFERENCE_TYPES.ReferencePoint]}
					typePreferences={type_preferences}
					preferenceValues={filtered_preference}
					objectiveValues={filtered_objective_values}
					isIterationAllowed={is_iteration_allowed()}
					lastIteratedPreference={filtered_last_iterated_preference}
					onPreferenceChange={handle_preference_change}
					onIterate={handle_iterate}
					isFinishButton={false}
					footerExtra={footerButtons}
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
					: 'Select final solution and finish the CUMULUS method with it'}
			>
				<Button
					onclick={selectedIndexes.length === 1 ? confirm_finish : undefined}
					disabled={selectedIndexes.length !== 1 || current_state.response_type === 'cumulus.finalize'}
					variant="destructive"
					class="ml-10"
				>
					Finish
				</Button>
			</span>
		{/snippet}

		{#snippet visualizationArea()}
			{#if filtered_problem && current_state}
				<div class="h-full">
					<Resizable.PaneGroup direction="horizontal" class="h-full">
						<Resizable.Pane defaultSize={65} minSize={40} maxSize={80} class="h-full">
							<VisualizationsPanel
								problem={filtered_problem}
								previousPreferenceValues={[filtered_last_iterated_preference]}
								currentPreferenceValues={filtered_preference}
								previousPreferenceType={type_preferences}
								currentPreferenceType={type_preferences}
								solutionsObjectiveValues={mapSolutionsToObjectiveValues(chosen_solutions, filtered_problem)}
								previousObjectiveValues={selected_type_solutions === 'current'
									? processPreviousObjectiveValues(current_state, filtered_problem)
									: []}
								externalSelectedIndexes={selectedIndexes}
								onSelectSolution={handle_solution_click}
							/>
						</Resizable.Pane>

						{#if mode === 'iterate' && hasUtopiaMetadata}
							<ResizableHandle withHandle class=" border-4 border-gray-200 shadow-sm" />
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
						{:else if mode === 'iterate' && hasSolutionDescription}
							<ResizableHandle withHandle class="border-4 border-gray-200 shadow-sm" />
							<Resizable.Pane defaultSize={35} minSize={20} class="h-full">
								<SolutionDescriptionPanel description={solutionDescription} />
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
			{#if filtered_problem && chosen_solutions.length > 0}
				<SolutionTable
					problem={filtered_problem}
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
	</BaseLayout>
{/if}

<!-- Choose Objectives dialog -->
{#if problem}
	<Dialog.Root bind:open={show_objectives_dialog}>
		<Dialog.Portal>
			<Dialog.Overlay />
			<Dialog.Content class="max-w-sm">
				<Dialog.Header>
					<Dialog.Title>Choose Objectives</Dialog.Title>
					<Dialog.Description>
						Select which objectives to display in the interface. At least one must remain active.
					</Dialog.Description>
				</Dialog.Header>
				<div class="space-y-3 py-4">
					{#each problem.objectives as objective}
						{@const isActive = active_objective_symbols.has(objective.symbol)}
						{@const isLast = active_objective_symbols.size === 1 && isActive}
						{@const checkboxId = `obj-checkbox-${objective.symbol}`}
						<div class="flex items-center gap-3">
							<Checkbox
								id={checkboxId}
								checked={isActive}
								disabled={isLast}
								onCheckedChange={(checked) => {
									const next = new Set(active_objective_symbols);
									if (checked) next.add(objective.symbol);
									else next.delete(objective.symbol);
									active_objective_symbols = next;
								}}
							/>
							<label for={checkboxId} class="cursor-pointer text-sm {isLast ? 'text-gray-400' : ''}">
								{objective.name}
								<span class="text-gray-500">({objective.maximize ? 'max' : 'min'})</span>
							</label>
						</div>
					{/each}
				</div>
				<Dialog.Footer>
					<Dialog.Close>
						<Button variant="default">Done</Button>
					</Dialog.Close>
				</Dialog.Footer>
			</Dialog.Content>
		</Dialog.Portal>
	</Dialog.Root>
{/if}

<!-- Scalarization dialog -->
<Dialog.Root bind:open={show_scalarizations_dialog}>
	<Dialog.Portal>
		<Dialog.Overlay />
		<Dialog.Content class="max-w-sm">
			<Dialog.Header>
				<Dialog.Title>Scalarization</Dialog.Title>
				<Dialog.Description>
					Select which scalarization functions to use. At least one must remain active.
				</Dialog.Description>
			</Dialog.Header>
			<div class="space-y-3 py-4">
				{#each AVAILABLE_SCALARIZATIONS as sf}
					{@const isChecked = selected_scalarizations.includes(sf.value)}
					{@const isLast = selected_scalarizations.length === 1 && isChecked}
					{@const checkboxId = `sf-checkbox-${sf.value}`}
					<div class="flex items-center gap-3">
						<Checkbox
							id={checkboxId}
							checked={isChecked}
							disabled={isLast}
							onCheckedChange={(checked) => {
								selected_scalarizations = checked
									? [...selected_scalarizations, sf.value]
									: selected_scalarizations.filter((s) => s !== sf.value);
							}}
						/>
						<label for={checkboxId} class="cursor-pointer text-sm {isLast ? 'text-gray-400' : ''}">
							{sf.label}
						</label>
					</div>
				{/each}
			</div>
			<Dialog.Footer>
				<Dialog.Close>
					<Button variant="default">Done</Button>
				</Dialog.Close>
			</Dialog.Footer>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>
