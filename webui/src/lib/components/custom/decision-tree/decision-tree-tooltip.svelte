<script lang="ts">
	import type { TreeNodeResponse, DecisionEventResponse } from './tree-types';
	import { formatPoint, analyzeTradeoffs, type ObjectiveTradeoff } from './tree-utils';

	interface Props {
		node: TreeNodeResponse;
		event?: DecisionEventResponse | null;
		parentNode?: TreeNodeResponse | null;
		forwardEvent?: DecisionEventResponse | null;
		maximizeMap?: Record<string, boolean>;
		x: number;
		y: number;
		visible: boolean;
	}

	let { node, event = null, parentNode = null, forwardEvent = null, maximizeMap = {}, x, y, visible }: Props = $props();

	// Flip tooltip to the left if it would overflow the right edge of the viewport
	let flipLeft = $derived(x + 280 > (typeof window !== 'undefined' ? window.innerWidth : 1200));

	// Arrival trade-offs: decision that led TO this node
	let arrivalTradeoffs = $derived.by(() => {
		if (!event || event.chosen_option_idx == null || !parentNode?.intermediate_points) {
			return null;
		}
		return analyzeTradeoffs(
			parentNode.intermediate_points as Record<string, number>[],
			event.chosen_option_idx,
			maximizeMap
		);
	});

	// Forward trade-offs: decision made FROM this node (fallback for root nodes)
	let forwardTradeoffs = $derived.by(() => {
		if (!forwardEvent || forwardEvent.chosen_option_idx == null || !node.intermediate_points) {
			return null;
		}
		return analyzeTradeoffs(
			node.intermediate_points as Record<string, number>[],
			forwardEvent.chosen_option_idx,
			maximizeMap
		);
	});

	// Prefer arrival; fall back to forward for root nodes
	let tradeoffs = $derived(arrivalTradeoffs ?? forwardTradeoffs);

	function tradeoffColor(t: ObjectiveTradeoff): string {
		// Green (prioritized) → Yellow (neutral) → Red (sacrificed)
		if (t.normalizedRank <= 0.25) return '#059669'; // emerald-600
		if (t.normalizedRank >= 0.75) return '#dc2626'; // red-600
		return '#d97706'; // amber-600
	}

	function tradeoffLabel(t: ObjectiveTradeoff): string {
		if (t.total <= 1) return '';
		if (t.rank === 1) return 'best';
		if (t.rank === t.total) return 'worst';
		return `${t.rank}/${t.total}`;
	}

	function tradeoffBarWidth(t: ObjectiveTradeoff): number {
		// Invert: best (rank 1) = full bar, worst = minimal bar
		return Math.max(8, (1 - t.normalizedRank) * 100);
	}
</script>

{#if visible}
	<div
		class="pointer-events-none fixed z-[9999] w-72 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs shadow-lg"
		style="left: {flipLeft ? x - 288 : x + 12}px; top: {y - 8}px;"
	>
		<div class="mb-1 font-semibold text-gray-900">
			Node #{node.node_id}
			{#if node.node_type === 'final'}
				<span class="ml-1 rounded bg-emerald-100 px-1 text-emerald-700">Final</span>
			{/if}
		</div>

		{#if node.node_type === 'step'}
			<div class="text-gray-600">
				Iteration: {node.current_iteration ?? '—'} | Left: {node.iterations_left ?? '—'}
			</div>

			{#if tradeoffs}
				<!-- Trade-off analysis -->
				<div class="mt-2 border-t border-gray-100 pt-1.5">
					<div class="mb-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
						Trade-offs at this choice
					</div>
					<div class="space-y-1">
						{#each tradeoffs as t}
							<div class="flex items-center gap-1.5">
								<span class="w-8 shrink-0 font-mono text-gray-700">{t.key}</span>
								<span class="w-4 shrink-0 text-center text-[9px] text-gray-400" title={t.maximize ? 'maximize' : 'minimize'}>
									{t.maximize ? 'max' : 'min'}
								</span>
								<!-- Visual bar showing relative ranking -->
								<div class="relative h-3 flex-1 rounded-sm bg-gray-100">
									<div
										class="h-full rounded-sm transition-all"
										style="width: {tradeoffBarWidth(t)}%; background-color: {tradeoffColor(t)};"
									></div>
								</div>
								<span
									class="w-10 shrink-0 text-right font-semibold"
									style="color: {tradeoffColor(t)};"
								>
									{tradeoffLabel(t)}
								</span>
							</div>
						{/each}
					</div>
					<div class="mt-1 text-[10px] text-gray-400">
						Green = prioritized, Red = sacrificed
					</div>
				</div>
			{:else if node.intermediate_points}
				<div class="mt-1 text-gray-600">
					{node.intermediate_points.length} intermediate points
				</div>
			{/if}
		{:else}
			<div class="mt-1 text-gray-600">
				<span class="font-medium">Selected point #{(node.selected_point_index ?? 0) + 1}</span>
			</div>
			{#if node.final_solution_objectives}
				<div class="mt-1 text-gray-600">
					<span class="font-medium">Objectives:</span>
					{formatPoint(node.final_solution_objectives)}
				</div>
			{/if}
		{/if}
	</div>
{/if}
