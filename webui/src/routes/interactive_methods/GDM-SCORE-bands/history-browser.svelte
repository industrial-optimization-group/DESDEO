<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import type { components } from "$lib/api/client-types";

	// Component props
	const { 
		history,
		currentIterationId,
		onRevertToIteration,
		isOwner = false
	} = $props<{
		history: (components["schemas"]["GDMSCOREBandsResponse"] | components["schemas"]["GDMSCOREBandsDecisionResponse"])[];
		currentIterationId: number;
		onRevertToIteration: (iteration: number) => void;
		isOwner?: boolean;
	}>();

	// Local state for this component
	let showHistory = $state(false);
	let expandedIterations = $state(new Set<number>());

	// Helper function to toggle iteration expansion (for future use)
	function toggleIterationExpansion(iterationId: number) {
		if (expandedIterations.has(iterationId)) {
			expandedIterations.delete(iterationId);
		} else {
			expandedIterations.add(iterationId);
		}
		expandedIterations = new Set(expandedIterations); // Trigger reactivity
	}
</script>

{#if isOwner}
	<div class="card bg-base-100 shadow-xl">
		<div class="card-body">
			<h2 class="card-title">History</h2>
			<div class="space-y-2 p-2">
				<Button
					onclick={() => showHistory = !showHistory}
					class="btn btn-secondary"
				>
					{showHistory ? 'Hide History' : 'Show History'}
				</Button>
				
				{#if showHistory}
					<div class="mt-4 space-y-2 max-h-100 overflow-y-auto">
						{#each history as historyItem, index}
							<div class="flex items-center justify-between p-2 border rounded">
								<span class="text-sm">
									Iteration {historyItem.group_iter_id}
									{#if historyItem.group_iter_id === currentIterationId}
										<span class="text-blue-600 text-xs">(current)</span>
									{/if}
									{#if historyItem.method === 'gdm-score-bands-final'}
										<span class="text-orange-600 text-xs">(final)</span>
									{/if}
								</span>
								<Button
									onclick={() => onRevertToIteration(historyItem.group_iter_id)}
									class="btn btn-xs btn-primary"
									disabled={historyItem.group_iter_id === currentIterationId || historyItem.method === 'gdm-score-bands-final'}
								>
									Go to this iteration
								</Button>
							</div>
						{/each}
						{#if history.length <= 1}
							<p class="text-sm text-gray-500 text-center">No previous iterations available</p>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}