<script lang="ts">
	import { onMount } from 'svelte';
	import { methodSelection } from '../../../stores/methodSelection';
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
		points_to_list
	} from './handler';
	import type { stepMethodEnautilusStepPostResponse } from '$lib/gen/endpoints/DESDEOFastAPI';
	import { number } from 'zod';

	let selection = $state({ selectedProblemId: null, selectedMethod: null });
	let problem_info = $state(null);
	let enautilus_state = $state<ENautilusStepResponse | null>(null);
	let selected_point_index = $state<number>(0);
	let previous_objective_values = $state<number[]>([]);
	let number_intermediate_points = $state<number>(3);

	let currentIntermediatePoints = $derived.by(() => {
		if (!enautilus_state) {
			return [];
		}

		return points_to_list(enautilus_state.intermediate_points);
	});

	let currentReachableBestBounds = $derived.by(() => {
		if (!enautilus_state) {
			return [];
		}

		return points_to_list(enautilus_state.reachable_best_bounds);
	});

	let currentReachableWorstBounds = $derived.by(() => {
		if (!enautilus_state) {
			return [];
		}

		return points_to_list(enautilus_state.reachable_worst_bounds);
	});

	$effect(() => {
		$inspect('enautilus_state', enautilus_state);
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
				const response: ProblemInfo = await fetch_problem_info(request);

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
					iterations_left: 5,
					selected_point: {},
					reachable_point_indices: [],
					number_of_intermediate_points: number_intermediate_points
					// session_id, parent_state_id
				};

				const stepResponse: ENautilusStepResponse = await initialize_enautilus_state(stepRequest);

				if (stepResponse === null) {
					console.log('E-NAUTILUS initialization failed (empty response).');
					errorMessage.set('Failed to initialize E-NAUTILUS.');
					return;
				}

				enautilus_state = stepResponse;
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

			const next = await step_enautilus(
				enautilus_state,
				selected_point_index,
				selection.selectedProblemId,
				number_intermediate_points
			);

			if (!next) {
				errorMessage.set('Failed to iterate E-NAUTILUS');
				return;
			}

			previous_objective_values = currentIntermediatePoints[selected_point_index];

			enautilus_state = next;
		} catch (err) {
			console.error('Error during E-NAUTILUS step', err);
			errorMessage.set('Unexpected error during E-NAUTILUS step.');
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
			<span
				class="inline-block"
				title={selected_point_index == null
					? 'Select exactly one intermediate point to advance the E-NAUTILUS method.'
					: 'Advance the E-NAUTILUS method using the selected intermediate point.'}
			>
				<Button
					onclick={selected_point_index != null ? handle_iteration : undefined}
					disabled={selected_point_index == null ||
						!enautilus_state ||
						enautilus_state.iterations_left <= 0}
					variant="default"
					class="ml-10"
				>
					Next iteration
				</Button>
			</span>
		</div>
	{/snippet}
	{#snippet visualizationArea()}
		{#if problem_info && enautilus_state && currentIntermediatePoints.length > 0}
			<div class="h-full">
				<Resizable.PaneGroup direction="horizontal" class="h-full">
					<Resizable.Pane defaultSize={100} minSize={40} class="h-full">
						<VisualizationsPanel
							problem={problem_info}
							previousPreferenceValues={currentReachableBestBounds[selected_point_index]}
							currentPreferenceValues={[]}
							previousPreferenceType={null}
							currentPreferenceType={null}
							solutionsObjectiveValues={currentIntermediatePoints}
							previousObjectiveValues={[previous_objective_values]}
							externalSelectedIndexes={[selected_point_index]}
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
</BaseLayout>
