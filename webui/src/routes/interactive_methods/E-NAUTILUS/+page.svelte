<script lang="ts">
	import { onMount } from 'svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import type { MethodSelectionState } from '../../../stores/methodSelection';
	import { type ENautilusRepresentativeSolutionsResponse, type InteractiveSessionBase } from '$lib/gen/models';
	import { isLoading, errorMessage } from '../../../stores/uiState';

	import BaseLayout from '$lib/components/custom/method_layout/base-layout.svelte';
	import Button from '$lib/components/ui/button/button.svelte';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';
	import * as Resizable from '$lib/components/ui/resizable';
	import * as Tabs from '$lib/components/ui/tabs';
	import { DecisionTree } from '$lib/components/custom/decision-tree';
	import Combobox from '$lib/components/ui/combobox/combobox.svelte';
	import { EndStateView } from '$lib/components/custom/end-state-view';
	import { DecisionJourney } from '$lib/components/custom/decision-journey';
	import type { ENautilusSessionTreeResponse } from '$lib/gen/models';

	import type {
		ENautilusStepRequest,
		ENautilusStepResponse,
		ProblemGetRequest,
		ProblemInfo
	} from '$lib/gen/models';
	import {
		step_enautilus,
		fetch_problem_info,
		initialize_enautilus_state,
		points_to_list,
		fetch_enautilus_state,
		fetch_representative_solutions,
		fetch_session_tree,
		fetch_sessions,
		create_session
	} from './handler';

	import {
		type ColumnDef,
		type Column,
		type SortingState,
		getCoreRowModel,
		getSortedRowModel
	} from '@tanstack/table-core';
	import { createSvelteTable } from '$lib/components/ui/data-table/data-table.svelte.js';
	import FlexRender from '$lib/components/ui/data-table/flex-render.svelte';
	import * as Table from '$lib/components/ui/table/index.js';
	import { renderSnippet } from '$lib/components/ui/data-table/render-helpers.js';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors.js';
	import { getDisplayAccuracy, formatNumber } from '$lib/helpers';
	import ArrowUpIcon from '@lucide/svelte/icons/arrow-up';
	import ArrowDownIcon from '@lucide/svelte/icons/arrow-down';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';

	type IntermediatePoint = Record<string, number>;

	type ENautilusMode = "iterate" | "final";
	type FinalView = "visualization" | "journey" | "map";
	let mode = $state<ENautilusMode>("iterate");
	let finalView = $state<FinalView>("visualization");
	let representative = $state<ENautilusRepresentativeSolutionsResponse | null>(null);
	let final_selected_index = $state<number>(0);

	let selection = $state<MethodSelectionState>({ selectedProblemId: null, selectedMethod: null, selectedSessionId: null, selectedSessionInfo: null
	});
	let problem_info = $state<ProblemInfo | null>(null);
	let previous_request = $state<ENautilusStepRequest | null>(null);
	let previous_response = $state<ENautilusStepResponse | null>(null);
	let selected_point_index = $state<number | null>(null);
	let previous_objective_values = $state<number[]>([]);
	let number_intermediate_points = $state<number>(3);
	let iterations_left_override = $state<number | null>(null);
	let initial_intermediate_points = $state<number | null>(null);
	let initial_iterations_left = $state<number | null>(null);
	let has_initialized = $state<boolean>(false);
	let showTree = $state<boolean>(false);
	let sessionTree = $state<ENautilusSessionTreeResponse | null>(null);
	let sessions = $state<InteractiveSessionBase[]>([]);
	let newSessionInfo = $state<string>('');
	let initSessionTree = $state<ENautilusSessionTreeResponse | null>(null);

	let is_initial_ready = $derived.by(() => {
		return (
			initial_iterations_left != null &&
			initial_iterations_left > 0 &&
			initial_intermediate_points != null &&
			initial_intermediate_points > 0
		);
	});

	let sessionOptions = $derived(
		sessions.filter(s => s.id != null).map(s => ({
			value: String(s.id),
			label: `#${s.id}${s.info ? ' — ' + s.info : ''}`
		}))
	);

	let selectedSessionString = $derived(
		selection.selectedSessionId != null ? String(selection.selectedSessionId) : ''
	);

	let initTreeHasNodes = $derived(
		initSessionTree?.nodes.some(n => n.node_id > 0) ?? false
	);

	let objective_keys = $derived.by(() => {
		if (!previous_response || previous_response.intermediate_points.length === 0) return [];

		const first = previous_response.intermediate_points[0] as Record<string, number>;
		return Object.keys(first);
	});

	let objective_labels = $derived.by(() => {
		if (!problem_info) return objective_keys;

		const names = problem_info.objectives?.map((o) => o.name) ?? [];

		return objective_keys.map((key, i) => names[i] ?? key);
	});



	let currentIntermediatePoints = $derived.by(() => {
		if (!previous_response) {
			return [];
		}

		return points_to_list(previous_response.intermediate_points);
	});

	let currentReachableBestBounds = $derived.by(() => {
		if (!previous_response) {
			return [];
		}

		return points_to_list(previous_response.reachable_best_bounds);
	});

	let currentReachableWorstBounds = $derived.by(() => {
		if (!previous_response) {
			return [];
		}

		return points_to_list(previous_response.reachable_worst_bounds);
	});

	let effective_iterations_left = $derived.by(() => {
		// Prefer override if provided; else use backend state; else fallback for init
		if (iterations_left_override != null) return iterations_left_override;
		return previous_response?.iterations_left ?? initial_iterations_left ?? 0;
	});

	let representativeObjectiveValues = $derived.by(() => {
		if (!representative || objective_keys.length === 0) return [];

		return representative.solutions.map((sol) => objective_keys.map((k) => (sol.optimal_objectives as any)[k] as number));
	});

	let finalSolution = $derived.by(() => {
		if (!representative) return null;
		return representative.solutions[final_selected_index] ?? null;
	})

	// SolverResults values may be number | number[]; unwrap arrays to plain numbers.
	function unwrapSolverRecord(record: Record<string, unknown>): { [key: string]: number } {
		const out: { [key: string]: number } = {};
		for (const [k, v] of Object.entries(record)) {
			out[k] = Array.isArray(v) ? v[0] : (v as number);
		}
		return out;
	}

	let finalTableData = $derived.by(() => {
		if (!representative) return [];
		const sol = representative.solutions[final_selected_index];
		if (!sol) return [];
		return [{
			objective_values: unwrapSolverRecord(sol.optimal_objectives),
			variable_values: unwrapSolverRecord(sol.optimal_variables),
			name: null,
			solution_index: final_selected_index
		}];
	});

	// -- Table state for intermediate points --
	let displayAccuracy = $derived(getDisplayAccuracy(problem_info));
	let tableSorting = $state<SortingState>([]);
	let tableRows: IntermediatePoint[] = $derived(previous_response?.intermediate_points ?? []);

	const tableColumns: ColumnDef<IntermediatePoint>[] = $derived.by(() => {
		if (!problem_info) return [];
		return [
			{
				id: 'row_number',
				header: '#',
				cell: ({ row }: { row: any }) => String(row.index + 1),
				enableSorting: false
			},
			{
				id: 'closeness',
				accessorFn: (_row: IntermediatePoint, index: number) =>
					previous_response?.closeness_measures?.[index] ?? 0,
				header: ({ column }: { column: Column<IntermediatePoint> }) =>
					renderSnippet(ColumnHeader, { column, title: 'Closeness' }),
				cell: ({ row }: { row: any }) =>
					renderSnippet(ObjectiveCell, {
						value: previous_response?.closeness_measures?.[row.index] ?? 0,
						accuracy: 4
					}),
				enableSorting: true
			},
			...problem_info.objectives.map((objective, idx) => ({
				accessorKey: objective.symbol,
				header: ({ column }: { column: Column<IntermediatePoint> }) =>
					renderSnippet(ColumnHeader, {
						column,
						title: `${objective.name} (${objective.maximize ? 'max' : 'min'})`,
						colorIdx: idx
					}),
				cell: ({ row }: { row: any }) =>
					renderSnippet(ObjectiveCell, {
						value: row.original[objective.symbol],
						accuracy: displayAccuracy[idx],
						best: (previous_response?.reachable_best_bounds?.[row.index] as Record<string, number> | undefined)?.[objective.symbol] ?? null
					}),
				enableSorting: true
			}))
		];
	});

	const table = createSvelteTable({
		get data() { return tableRows; },
		get columns() { return tableColumns; },
		state: {
			get sorting() { return tableSorting; }
		},
		onSortingChange: (updater) => {
			if (typeof updater === 'function') {
				tableSorting = updater(tableSorting);
			} else {
				tableSorting = updater;
			}
		},
		getCoreRowModel: getCoreRowModel(),
		getSortedRowModel: getSortedRowModel()
	});

	$effect(() => {
		$inspect('enautilus_state', previous_response);
		$inspect('currentIntermediatePoints', currentIntermediatePoints);
		$inspect('currently_selected_point', selected_point_index);
		$inspect('currentReachableBestBounds', currentReachableBestBounds);
		$inspect('currentReachableWorst', currentReachableWorstBounds);
		$inspect('previous_objective_values', previous_objective_values);
	});

	onMount(() => {
		const unsubscribe = methodSelection.subscribe((v) => (selection = v));

		(async () => {
			if (selection.selectedProblemId === null) {
				console.log('No problem selected for E-NAUTILUS.');
				return;
			}

			try {
				isLoading.set(true);

				// fetch problem info
				const request: ProblemGetRequest = { problem_id: selection.selectedProblemId };
				const response = await fetch_problem_info(request);

				if (response === null) {
					console.log('Could not fetch problem.');
					errorMessage.set('could not fetch problem information for E-NAUTILUS.');
					return;
				}

				problem_info = response;

				// Fetch all sessions
				const fetchedSessions = await fetch_sessions();
				sessions = fetchedSessions ?? [];

				// If a session is already selected, pre-fetch its tree
				if (selection.selectedSessionId != null) {
					initSessionTree = await fetch_session_tree(selection.selectedSessionId);
				}
			} catch (err) {
				console.log('Error during initialization of the E-NAUTILUS method', err);
				errorMessage.set('Unexpected error during E-NAUTILUS initialization.');
			} finally {
				isLoading.set(false);
			}
		})();

		return unsubscribe;
	});

	async function handleSessionSelect(value: string) {
		const id = Number(value);
		const session = sessions.find(s => s.id === id);
		if (!session) return;
		methodSelection.setSession(id, session.info ?? null);
		initSessionTree = await fetch_session_tree(id);
	}

	async function handleCreateSession() {
		const trimmed = newSessionInfo.trim();

		try {
			isLoading.set(true);
			const created = await create_session(trimmed || null);

			// Always refresh sessions list from server
			const fetchedSessions = await fetch_sessions();
			if (fetchedSessions) sessions = fetchedSessions;

			if (created && created.id != null) {
				methodSelection.setSession(created.id, created.info ?? null);
			} else {
				// Session may have been created despite an unexpected response.
				// Try to find it in the refreshed list.
				const found = sessions.find(s => s.info === trimmed);
				if (found && found.id != null) {
					methodSelection.setSession(found.id, found.info ?? null);
				} else {
					errorMessage.set('Failed to create session.');
					return;
				}
			}

			newSessionInfo = '';
			initSessionTree = null;
		} catch (err) {
			console.error('Error creating session:', err);
			errorMessage.set('Failed to create session.');
		} finally {
			isLoading.set(false);
		}
	}

	async function handleInitTreeNodeClick(nodeId: number) {
		await handleTreeNodeClick(nodeId);
		has_initialized = true;
		sessionTree = initSessionTree;
	}

	async function initialize_enautilus() {
		if (selection.selectedProblemId === null) {
			errorMessage.set('No problem selected.');
			return;
		}

		if (selection.selectedSessionId === null) {
			errorMessage.set('Please select a session before starting E-NAUTILUS.');
			return;
		}

		if (initial_intermediate_points == null || initial_iterations_left == null) {
			errorMessage.set('Please enter the initial number of iterations and intermediate points.');
			return;
		}

		if (initial_iterations_left <= 0 || initial_intermediate_points <= 0) {
			errorMessage.set('Initial iterations and intermediate points must be greater than zero.');
			return;
		}

		try {
			isLoading.set(true);

			const stepRequest: ENautilusStepRequest = {
				problem_id: selection.selectedProblemId,
				representative_solutions_id: 1,
				current_iteration: 0,
				iterations_left: initial_iterations_left,
				selected_point: {},
				reachable_point_indices: [],
				number_of_intermediate_points: initial_intermediate_points,
				session_id: selection.selectedSessionId
				// parent_state_id
			};

			const stepResponse = await initialize_enautilus_state(stepRequest);

			if (stepResponse === null) {
				console.log('E-NAUTILUS initialization failed (empty response).');
				errorMessage.set('Failed to initialize E-NAUTILUS.');
				return;
			}

			number_intermediate_points = initial_intermediate_points;
			previous_request = stepRequest;
			previous_response = stepResponse;
			iterations_left_override = null;
			selected_point_index = null;
			has_initialized = true;
		} catch (err) {
			console.log('Error during initialization of the E-NAUTILUS method', err);
			errorMessage.set('Unexpected error during E-NAUTILUS initialization.');
		} finally {
			isLoading.set(false);
		}
	}

	async function handle_iteration() {
		try {
			isLoading.set(true);

			if (previous_request === null) {
				errorMessage.set('Previous request is null.');
				return;
			}

			if (previous_response === null) {
				errorMessage.set('Previous response is null.');
				return;
			}

			if (selection.selectedProblemId === null) {
				errorMessage.set('No problem selected.');
				return;
			}

			if (selection.selectedSessionId === null) {
				errorMessage.set('No session selected.');
				return;
			}

			if (selected_point_index == null) {
				errorMessage.set('No point selected.')
				return;
			}

			const next_bundle = await step_enautilus(
				previous_response,
				selected_point_index,
				selection.selectedProblemId,
				number_intermediate_points,
				effective_iterations_left,
				previous_request.representative_solutions_id,
				selection.selectedSessionId
			);

			if (!next_bundle) {
				errorMessage.set('Failed to iterate E-NAUTILUS');
				return;
			}

			previous_objective_values = selected_point_index != null ? currentIntermediatePoints[selected_point_index] : [];
			previous_response = next_bundle.response;
			previous_request = next_bundle.request;

			// reset user selections
			selected_point_index = null;
			iterations_left_override = null;

		} catch (err) {
			console.error('Error during E-NAUTILUS step', err);
			errorMessage.set('Unexpected error during E-NAUTILUS step.');
		} finally {
			isLoading.set(false);
		}
	}

	async function handle_back() {
		try {
			isLoading.set(true);

			if (!previous_request) return;

			const parent_id = previous_request.parent_state_id ?? null;
			if (parent_id == null) return;

			const state_resp = await fetch_enautilus_state(parent_id);

			if (!state_resp) {
				errorMessage.set("Failed to fetch previous E-NAUTILUS state.");
				return;
			}

			previous_request = state_resp.request;
			previous_response = state_resp.response;

			selected_point_index = null;
			iterations_left_override = null;

			previous_objective_values = [];

		} catch (err) {
			console.error("Error going back one E-NAUTILUS state", err);
			errorMessage.set("Unexpected error while going back.")
		} finally {
			isLoading.set(false);
		}
	}

	async function finalize_enautilus() {
		try {
			errorMessage.set(null);
			isLoading.set(true);

			if (!previous_response || previous_response.state_id == null) {
				errorMessage.set("Final state is missing state_id.");
				return;
			}

			if (previous_response.iterations_left !== 0) {
				errorMessage.set("E-NAUTILUS is not yet at the final iteration.")
				return;
			}

			const response = await fetch_representative_solutions(previous_response.state_id);
			if (!response) {
				errorMessage.set("Failed to fetch representative solutions.")
				return;
			}

			representative = response;
			final_selected_index = selected_point_index ?? 0;
			mode = 'final';

		} catch(err) {
			console.error("Failed to finalize E-NAUTILUS", err);
			errorMessage.set("Unexpected error during finalization.");
		} finally {
			isLoading.set(false);
		}
	}

	async function refreshTree() {
		if (selection.selectedSessionId == null) return;
		try {
			sessionTree = await fetch_session_tree(selection.selectedSessionId);
		} catch (err) {
			console.error("Failed to refresh decision tree", err);
		}
	}

	async function handleTreeNodeClick(nodeId: number) {
		try {
			isLoading.set(true);

			const state_resp = await fetch_enautilus_state(nodeId);
			if (!state_resp) {
				errorMessage.set("Failed to load tree node state.");
				return;
			}

			previous_request = state_resp.request;
			previous_response = state_resp.response;
			selected_point_index = null;
			iterations_left_override = null;
			previous_objective_values = [];
			mode = 'iterate';
		} catch (err) {
			console.error("Error navigating to tree node", err);
			errorMessage.set("Failed to navigate to selected node.");
		} finally {
			isLoading.set(false);
		}
	}

	// Refresh tree whenever the response changes (new iteration completed)
	$effect(() => {
		if (previous_response && has_initialized) {
			refreshTree();
		}
	});
</script>

{#snippet ColumnHeader({ column, title, colorIdx }: { column: Column<IntermediatePoint>; title: string; colorIdx?: number })}
	<div
		class="flex items-center"
		style={colorIdx != null
			? `border-bottom: 6px solid ${COLOR_PALETTE[colorIdx % COLOR_PALETTE.length]}; width: 100%; padding: 0.5rem;`
			: ''}
	>
		{#if column.getCanSort()}
			<Button
				variant="ghost"
				size="sm"
				onclick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
				class="-ml-3 h-8"
			>
				<span>{title}</span>
				{#if column.getIsSorted() === 'desc'}
					<ArrowDownIcon class="ml-2 h-4 w-4" />
				{:else if column.getIsSorted() === 'asc'}
					<ArrowUpIcon class="ml-2 h-4 w-4" />
				{:else}
					<ChevronsUpDownIcon class="ml-2 h-4 w-4 opacity-50" />
				{/if}
			</Button>
		{:else}
			<span class="px-2 py-1">{title}</span>
		{/if}
	</div>
{/snippet}

{#snippet ObjectiveCell({ value, accuracy, best }: { value: number | null | undefined; accuracy: number; best?: number | null })}
	<div class="pr-4 text-right">
		{value != null ? formatNumber(value, accuracy) : '-'}
		{#if best != null}
			<div class="text-[10px] text-gray-400">[best: {formatNumber(best, accuracy)}]</div>
		{/if}
	</div>
{/snippet}

<h1 class="mt-10 text-center text-2xl font-semibold">E-NAUTILUS method</h1>
<p class="mb-4 text-center text-sm text-gray-600">
	Selected problem id: {$methodSelection.selectedProblemId}; method: {$methodSelection.selectedMethod};
	session:
	{#if $methodSelection.selectedSessionId != null}
		{$methodSelection.selectedSessionId}
		{#if $methodSelection.selectedSessionInfo}
			({$methodSelection.selectedSessionInfo})
		{/if}
	{:else}
		none
	{/if}
</p>

{#if $isLoading}
	<p class="text-center text-gray-500">Loading E-NAUTILUS data…</p>
{:else}
	<p class="text-center text-gray-500">Waiting for user input.</p>
{/if}


{#if $errorMessage}
	<p class="text-center text-red-600">{$errorMessage}</p>
{/if}

{#if mode === 'final'}
	<BaseLayout showLeftSidebar={false} showRightSidebar={false} bottomPanelTitle="">
		{#snippet explorerTitle()}{/snippet}
		{#snippet explorerControls()}
			<div class="flex items-center gap-4">
				<Tabs.Root bind:value={finalView}>
					<Tabs.List>
						<Tabs.Trigger value="visualization">Solution</Tabs.Trigger>
						<Tabs.Trigger value="journey">Decision Journey</Tabs.Trigger>
						<Tabs.Trigger value="map">Map</Tabs.Trigger>
					</Tabs.List>
				</Tabs.Root>

				<span class="inline-block" title="Return to the last E-NAUTILUS iteration view.">
					<Button onclick={() => (mode = 'iterate')} variant="secondary">
						Back to iterations
					</Button>
				</span>
			</div>
		{/snippet}

		{#snippet visualizationArea()}
			{#if problem_info && representative && representativeObjectiveValues.length > 0}
				<div class="relative h-full">
					{#if finalView === 'map'}
					<div class="flex h-full items-center justify-center text-sm text-gray-400">
						Map visualization coming soon.
					</div>
				{:else if finalView === 'journey'}
						{#if sessionTree && previous_response?.state_id != null}
							<DecisionJourney
								sessionTree={sessionTree}
								leafNodeId={previous_response.state_id}
								problem={problem_info}
								finalSolutionPoint={finalSolution ? unwrapSolverRecord(finalSolution.optimal_objectives) : null}
							/>
						{:else}
							<div class="flex h-full items-center justify-center text-gray-500">
								Session tree not available.
							</div>
						{/if}
					{:else}
						<VisualizationsPanel
							problem={problem_info as any}
							previousPreferenceValues={[]}
							currentPreferenceValues={[]}
							previousPreferenceType={''}
							currentPreferenceType={''}
							solutionsObjectiveValues={representativeObjectiveValues.length > 0 ? [representativeObjectiveValues[final_selected_index]] : []}
							previousObjectiveValues={[]}
							externalSelectedIndexes={[0]}
						/>
					{/if}
				</div>
			{:else}
				<div class="flex h-full items-center justify-center text-gray-500">
					Final solution not available.
				</div>
			{/if}
		{/snippet}

		{#snippet numericalValues()}
			{#if finalView === 'visualization' && problem_info && finalTableData.length > 0}
				<EndStateView
					problem={problem_info}
					tableData={finalTableData}
					showVariables={true}
					title="Representative solution"
				/>
			{/if}
		{/snippet}
	</BaseLayout>
{:else if !previous_response && !has_initialized}
	<div class="mx-auto mt-8 flex w-full max-w-3xl flex-col gap-4 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
		<div>
			<h2 class="text-lg font-semibold">Start E-NAUTILUS</h2>
			<p class="text-sm text-gray-600">
				Choose session and initial parameters.
			</p>
		</div>

		<div>
			<span class="mb-1 block text-sm font-medium text-gray-700">Session</span>
			<div class="flex items-center gap-2">
				<div class="flex-1">
					{#key selectedSessionString}
						<Combobox
							options={sessionOptions}
							defaultSelected={selectedSessionString}
							onChange={(e) => handleSessionSelect(e.value)}
							placeholder="Select a session..."
							showSearch={true}
						/>
					{/key}
				</div>
				<input
					type="text"
					bind:value={newSessionInfo}
					placeholder="New session name"
					class="rounded border border-gray-300 px-3 py-2 text-sm"
					onkeydown={(e) => { if (e.key === 'Enter') handleCreateSession(); }}
				/>
				<Button variant="outline" onclick={handleCreateSession}>+ New</Button>
			</div>
		</div>

		{#if initTreeHasNodes && selection.selectedSessionId != null}
			<div>
				<span class="mb-1 block text-sm font-medium text-gray-700">Resume from previous state</span>
				<div class="max-h-64 overflow-auto rounded border border-gray-200 bg-gray-50 p-2">
					<DecisionTree
						treeData={initSessionTree}
						activeNodeId={null}
						onSelectNode={handleInitTreeNodeClick}
						problem={problem_info}
					/>
				</div>
				<p class="mt-1 text-xs text-gray-500">Click a node to resume from that point.</p>
			</div>

			<div class="flex items-center gap-4">
				<div class="h-px flex-1 bg-gray-200"></div>
				<span class="text-xs text-gray-400">Or start fresh</span>
				<div class="h-px flex-1 bg-gray-200"></div>
			</div>
		{/if}

		<div class="grid gap-4 md:grid-cols-2">
			<div>
				<label class="mb-1 block text-sm font-medium text-gray-700" for="initial-iterations">
					Iterations
				</label>
				<input
					id="initial-iterations"
					type="number"
					min="1"
					bind:value={initial_iterations_left}
					class="w-full rounded border border-gray-300 px-3 py-2 text-sm"
					placeholder="e.g. 5"
				/>
			</div>

			<div>
				<label class="mb-1 block text-sm font-medium text-gray-700" for="initial-intermediate">
					Intermediate points
				</label>
				<input
					id="initial-intermediate"
					type="number"
					min="1"
					max="10"
					bind:value={initial_intermediate_points}
					class="w-full rounded border border-gray-300 px-3 py-2 text-sm"
					placeholder="e.g. 3"
				/>
			</div>
		</div>

		<div class="flex flex-wrap items-center justify-between gap-3">
			<p class="text-xs text-gray-500">
				You can adjust intermediate points and remaining iterations later in the iteration controls.
			</p>
			<Button
				onclick={initialize_enautilus}
				disabled={$isLoading ||
					selection.selectedProblemId == null ||
					selection.selectedSessionId == null ||
					!is_initial_ready}
			>
				Start E-NAUTILUS
			</Button>
		</div>
	</div>
{:else}
	<BaseLayout
		showLeftSidebar={false}
		showRightSidebar={showTree}
		rightSidebarWidth="320px"
		bottomPanelTitle="E-NAUTILUS: initial intermediate points"
	>
		{#snippet explorerControls()}
			<div class="flex items-center gap-6">
				<div class="flex items-center gap-2">
					<span class="text-sm text-gray-700">Intermediate points:</span>
					<input
						type="number"
						min="1"
						max="10"
						bind:value={number_intermediate_points}
						class="w-20 rounded border border-gray-300 px-2 py-1 text-sm"
					/>
				</div>

				<div class="flex items-center gap-2">
					<span class="text-sm text-gray-700">Iterations left:</span>
					<input
						type="number"
						min="0"
						placeholder="auto"
						value={iterations_left_override ?? ''}
						oninput={(e) => {
							const v = (e.target as HTMLInputElement).value;
							iterations_left_override = v === '' ? null : Number(v);
						}}
						class="w-20 rounded border border-gray-300 px-2 py-1 text-sm"
					/>
				</div>

				<span class="text-xs text-gray-500">
					Auto: {previous_response?.iterations_left ?? '—'}
				</span>

				<span
					class="inline-block"
					title={selected_point_index == null
						? 'Select exactly one intermediate point to advance the E-NAUTILUS method.'
						: 'Advance the E-NAUTILUS method using the selected intermediate point.'}
				>
					<Button
						onclick={selected_point_index != null ? handle_iteration : undefined}
						disabled={selected_point_index == null ||
							!previous_response ||
							previous_response.iterations_left <= 0}
						variant="default"
						class="ml-10"
					>
						Next iteration
					</Button>
				</span>

				<span
					class="inline-block"
					title={previous_request?.parent_state_id == null ? 'No previous state available.' : 'Go back to the previous iteration.'}
				>
					<Button
						onclick={previous_request?.parent_state_id != null ? handle_back : undefined}
						disabled={$isLoading || !previous_request || previous_request.parent_state_id == null}
						variant="secondary"
					>
						Back
					</Button>
				</span>

				<span
					class="inline-block"
					title={
						!previous_response || previous_response.iterations_left !== 0
							? 'Finish becomes available after the last iteration (iterations left = 0).'
							: selected_point_index == null
								? 'Select an intermediate point first.'
								: 'Finalize with the selected solution.'
					}
				>
					<Button
						onclick={finalize_enautilus}
						disabled={!previous_response || previous_response.iterations_left !== 0 || previous_response.state_id == null || selected_point_index == null}
						variant="destructive"
						class="ml-10"
					>
						Finish
					</Button>
				</span>

				<span class="inline-block" title="Toggle the decision tree panel">
					<Button
						onclick={() => (showTree = !showTree)}
						variant={showTree ? 'default' : 'outline'}
						class="ml-4"
					>
						Tree
					</Button>
				</span>
			</div>
		{/snippet}
		{#snippet visualizationArea()}
			{#if problem_info && previous_response && currentIntermediatePoints.length > 0}
				<div class="h-full">
					<Resizable.PaneGroup direction="horizontal" class="h-full">
						<Resizable.Pane defaultSize={100} minSize={40} class="h-full">
							<VisualizationsPanel
								problem={problem_info as any}
								previousPreferenceValues={selected_point_index != null ? [currentReachableBestBounds[selected_point_index]] : undefined}
								currentPreferenceValues={[]}
								previousPreferenceType={''}
								currentPreferenceType={''}
								solutionsObjectiveValues={currentIntermediatePoints}
								previousObjectiveValues={[previous_objective_values]}
								externalSelectedIndexes={selected_point_index != null ? [selected_point_index] : []}
								onSelectSolution={(index: number) => {
									selected_point_index = index;
								}}
							/>
						</Resizable.Pane>
					</Resizable.PaneGroup>
				</div>
			{:else}
				<div class="flex h-full items-center justify-center text-gray-500">
					No E-NAUTILUS data available yet.
					{currentIntermediatePoints.length}
				</div>
			{/if}
		{/snippet}
		{#snippet numericalValues()}
		{#if previous_response && currentIntermediatePoints.length > 0 && objective_keys.length > 0}
			<div class="h-full overflow-auto">
				<Table.Root>
					<Table.Header>
						{#each table.getHeaderGroups() as headerGroup (headerGroup.id)}
							<Table.Row>
								{#each headerGroup.headers as header (header.id)}
									<Table.Head colspan={header.colSpan}>
										{#if !header.isPlaceholder}
											<FlexRender
												content={header.column.columnDef.header}
												context={header.getContext()}
											/>
										{/if}
									</Table.Head>
								{/each}
							</Table.Row>
						{/each}
					</Table.Header>
					<Table.Body>
						{#each table.getRowModel().rows as row (row.id)}
							<Table.Row
								onclick={() => (selected_point_index = row.index)}
								class="cursor-pointer {selected_point_index === row.index ? 'bg-gray-300' : ''}"
								title="Click to select this intermediate point"
							>
								{#each row.getVisibleCells() as cell, cellIndex (cell.id)}
									<Table.Cell
										class={cellIndex === 0
											? selected_point_index === row.index
												? 'border-l-10 border-blue-600'
												: 'border-l-10'
											: ''}
									>
										<FlexRender content={cell.column.columnDef.cell} context={cell.getContext()} />
									</Table.Cell>
								{/each}
							</Table.Row>
						{:else}
							<Table.Row>
								<Table.Cell colspan={tableColumns.length} class="h-24 text-center">
									No intermediate points available.
								</Table.Cell>
							</Table.Row>
						{/each}
					</Table.Body>
				</Table.Root>
			</div>
		{:else}
			<div class="flex h-full items-center justify-center text-gray-500">
				No numerical values available.
			</div>
		{/if}
		{/snippet}

		{#snippet rightSidebar()}
			<div class="h-full overflow-auto p-2">
				<DecisionTree
					treeData={sessionTree}
					activeNodeId={previous_response?.state_id ?? null}
					onSelectNode={handleTreeNodeClick}
					problem={problem_info}
				/>
			</div>
		{/snippet}

	</BaseLayout>
{/if}
