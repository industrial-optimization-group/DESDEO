<script lang="ts">
	import type { PairwiseTradeoffEntry } from './journey-utils';
	import { formatNumber } from '$lib/helpers';

	interface Props {
		tradeoffs: PairwiseTradeoffEntry[];
	}

	let { tradeoffs }: Props = $props();

	// Group by favored objective, sorted by total sacrifice desc
	let grouped = $derived.by(() => {
		const map = new Map<string, { label: string; entries: PairwiseTradeoffEntry[] }>();
		for (const t of tradeoffs) {
			const existing = map.get(t.favoredKey) ?? { label: t.favoredLabel, entries: [] };
			existing.entries.push(t);
			map.set(t.favoredKey, existing);
		}
		for (const group of map.values()) {
			group.entries.sort((a, b) => b.avgSacrifice - a.avgSacrifice);
		}
		return [...map.entries()];
	});

	function sacrificeColor(sacrifice: number): string {
		if (sacrifice >= 0.6) return '#dc2626'; // red – heavy cost
		if (sacrifice >= 0.3) return '#d97706'; // amber – moderate cost
		return '#059669'; // green – low cost
	}
</script>

{#if grouped.length > 0}
	<div class="space-y-2.5 text-xs">
		{#each grouped as [, group]}
			<div>
				<div class="font-medium text-gray-700">
					Prioritizing {group.label}:
				</div>
				{#each group.entries as entry}
					<div class="ml-3 flex items-baseline gap-1 text-gray-600">
						<span class="shrink-0">&rarr;</span>
						<span class="shrink-0">{entry.sacrificedLabel}:</span>
						<span
							class="font-semibold"
							style="color: {sacrificeColor(entry.avgSacrifice)}"
						>
							avg {formatNumber(entry.avgSacrifice * 100, 0)}% cost
						</span>
						<span class="text-gray-400">({entry.count}&times;)</span>
					</div>
				{/each}
			</div>
		{/each}
	</div>
{:else}
	<div class="text-xs italic text-gray-400">Not enough data for tradeoff analysis.</div>
{/if}
