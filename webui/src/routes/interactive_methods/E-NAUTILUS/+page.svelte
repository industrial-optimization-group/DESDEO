<script lang="ts">
	import { onMount } from 'svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import type { MethodSelectionState } from '../../../stores/methodSelection';
	import { type ENautilusRepresentativeSolutionsResponse} from '$lib/gen/models';
	import { isLoading, errorMessage } from '../../../stores/uiState';

	import BaseLayout from '$lib/components/custom/method_layout/base-layout.svelte';
	import Button from '$lib/components/ui/button/button.svelte';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';
	import * as Resizable from '$lib/components/ui/resizable';

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

		fetch_representative_solutions

	} from './handler';

	type ENautilusMode = "iterate" | "final";
	let mode = $state<ENautilusMode>("iterate");
	let representative = $state<ENautilusRepresentativeSolutionsResponse | null>(null);
	let final_selected_index = $state<number>(0);

	let selection = $state<MethodSelectionState>({ selectedProblemId: null, selectedMethod: null });
	let problem_info = $state<ProblemInfo | null>(null);
	let previous_request = $state<ENautilusStepRequest | null>(null);
	let previous_response = $state<ENautilusStepResponse | null>(null);
	let selected_point_index = $state<number | null>(null);
	let previous_objective_values = $state<number[]>([]);
	let number_intermediate_points = $state<number>(3);
	let iterations_left_override = $state<number | null>(null);

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
		return previous_response?.iterations_left ?? 5;
	});

	let representativeObjectiveValues = $derived.by(() => {
		if (!representative || objective_keys.length === 0) return [];

		return representative.solutions.map((sol) => objective_keys.map((k) => (sol.optimal_objectives as any)[k] as number));
	});

	let finalSolution = $derived.by(() => {
		if (!representative) return null;
		return representative.solutions[final_selected_index] ?? null;
	})

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

				// initial E-NAUTILUS problem step request
				// TODO: these parameters should be queried from the user
				// TODO: if we have a selected interactive session and state, we should pick up from there

				const stepRequest: ENautilusStepRequest = {
					problem_id: selection.selectedProblemId,
					representative_solutions_id: 1,
					current_iteration: 0,
					iterations_left: effective_iterations_left,
					selected_point: {},
					reachable_point_indices: [],
					number_of_intermediate_points: number_intermediate_points
					// session_id, parent_state_id
				};

				const stepResponse = await initialize_enautilus_state(stepRequest);

				if (stepResponse === null) {
					console.log('E-NAUTILUS initialization failed (empty response).');
					errorMessage.set('Failed to initialize E-NAUTILUS.');
					return;
				}

				previous_request = stepRequest;
				previous_response = stepResponse;
			} catch (err) {
				console.log('Error during initialization of the E-NAUTILUS method', err);
				errorMessage.set('Unexpected error during E-NAUTILUS initialization.');
			} finally {
				isLoading.set(false);
			}
		})();

		return unsubscribe;
	});

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
				previous_request.representative_solutions_id
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
</script>

<h1 class="mt-10 text-center text-2xl font-semibold">E-NAUTILUS method</h1>
<p class="mb-4 text-center text-sm text-gray-600">
	Selected problem id: {$methodSelection.selectedProblemId}; method: {$methodSelection.selectedMethod}
</p>

{#if $isLoading}
	<p class="text-center text-gray-500">Loading E-NAUTILUS data…</p>
{/if}

{#if $errorMessage}
	<p class="text-center text-red-600">{$errorMessage}</p>
{/if}

{#if mode === 'final'}
	<BaseLayout showLeftSidebar={false} showRightSidebar={false} bottomPanelTitle="Final solution">
		{#snippet explorerControls()}
			<span class="inline-block" title="Return to the last E-NAUTILUS iteration view.">
				<Button onclick={() => (mode = 'iterate')} variant="secondary">
					Back to iterations
				</Button>
			</span>
		{/snippet}

		{#snippet visualizationArea()}
			{#if problem_info && representative && representativeObjectiveValues.length > 0}
				<div class="h-full">
					<Resizable.PaneGroup direction="horizontal" class="h-full">
						<Resizable.Pane defaultSize={100} minSize={40} class="h-full">
							<VisualizationsPanel
								problem={problem_info as any}
								previousPreferenceValues={[]}
								currentPreferenceValues={[]}
								previousPreferenceType={''}
								currentPreferenceType={''}
								solutionsObjectiveValues={representativeObjectiveValues}
								previousObjectiveValues={[]}
								externalSelectedIndexes={[final_selected_index]}
								onSelectSolution={(index: number) => {
									final_selected_index = index;
								}}
							/>
						</Resizable.Pane>
					</Resizable.PaneGroup>
				</div>
			{:else}
				<div class="flex h-full items-center justify-center text-gray-500">
					Final solution not available.
				</div>
			{/if}
		{/snippet}

		{#snippet numericalValues()}
			{#if finalSolution}
				<!-- Minimal numeric display for SolverResults -->
				<div class="h-full overflow-auto p-2 text-sm">
					<div class="mb-2 font-semibold">Representative solution #{final_selected_index + 1}</div>

					<div class="mb-3">
						<div class="text-xs font-semibold text-gray-600">Objectives</div>
						<pre class="text-xs">{JSON.stringify(finalSolution.optimal_objectives, null, 2)}</pre>
					</div>

					<div class="mb-3">
						<div class="text-xs font-semibold text-gray-600">Variables</div>
						<pre class="text-xs">{JSON.stringify(finalSolution.optimal_variables, null, 2)}</pre>
					</div>

					<div class="text-xs text-gray-600">
						success: {String(finalSolution.success)} — {finalSolution.message}
					</div>
				</div>
			{/if}
		{/snippet}
	</BaseLayout>
{:else}
	<BaseLayout
		showLeftSidebar={false}
		showRightSidebar={false}
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
							: previous_response.state_id == null
								? 'Cannot finalize because the final state_id is missing.'
								: 'Fetch the final representative solution(s).'
					}
				>
					<Button
						onclick={previous_response && previous_response.iterations_left === 0 && previous_response.state_id != null ? finalize_enautilus : undefined}
						disabled={!previous_response || previous_response.iterations_left !== 0 || previous_response.state_id == null}
						variant="destructive"
						class="ml-10"
					>
						Finish
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
				<table class="min-w-full border-collapse text-sm">
					<thead class="sticky top-0 bg-white">
						<tr class="border-b border-gray-200">
							<th class="px-2 py-2 text-left text-xs font-semibold text-gray-600">#</th>

							<th class="px-2 py-2 text-right text-xs font-semibold text-gray-600">
								closeness
							</th>

							{#each objective_labels as label}
								<th class="px-2 py-2 text-right text-xs font-semibold text-gray-600">
									{label}
								</th>
							{/each}
						</tr>
					</thead>

					<tbody>
						{#each currentIntermediatePoints as row, i}
							<tr
								class={`border-b border-gray-100 cursor-pointer ${
									i === selected_point_index ? 'bg-gray-100' : 'hover:bg-gray-50'
								}`}
								onclick={() => (selected_point_index = i)}
								title="Click to select this intermediate point"
							>
								<td class="px-2 py-2 text-xs text-gray-600">{i + 1}</td>

								<td class="px-2 py-2 text-right font-mono text-xs">
									{(previous_response.closeness_measures?.[i] ?? 0).toFixed(4)}
								</td>

								{#each row as value}
									<td class="px-2 py-2 text-right font-mono text-xs">
										{value.toFixed(6)}
									</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<div class="flex h-full items-center justify-center text-gray-500">
				No numerical values available.
			</div>
		{/if}
		{/snippet}

	</BaseLayout>
{/if}