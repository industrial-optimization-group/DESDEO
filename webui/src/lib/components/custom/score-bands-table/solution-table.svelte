<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import { formatNumber } from '$lib/helpers';

	export type ObjectiveRange = {
		min: number;
		max: number;
		median: number;
		scaleMin: number;
		scaleMax: number;
	};

	export type ClusterBandRow = {
		id: number;
		label: string;
		color: string;
		numSolutions: number;
		objectiveRanges: Record<string, ObjectiveRange>;
	};

	let {
		axisNames = [],
		bands = [],
		selectedBand = null,
		onBandSelect = () => {}
	}: {
		axisNames: string[];
		bands: ClusterBandRow[];
		selectedBand: number | null;
		onBandSelect?: (clusterId: number) => void;
	} = $props();

	let totalSolutions = $derived.by(() =>
		bands.reduce((sum, band) => sum + band.numSolutions, 0)
	);

	function normalize(value: number, scaleMin: number, scaleMax: number) {
		if (scaleMax === scaleMin) return 0;
		const normalized = (value - scaleMin) / (scaleMax - scaleMin);
		return Math.max(0, Math.min(1, normalized));
	}
</script>

{#snippet RangeCell({ range, color }: { range?: ObjectiveRange; color: string })}
	{#if range}
		{@const minNorm = normalize(range.min, range.scaleMin, range.scaleMax)}
		{@const maxNorm = normalize(range.max, range.scaleMin, range.scaleMax)}
		{@const medianNorm = normalize(range.median, range.scaleMin, range.scaleMax)}
		{@const left = Math.min(minNorm, maxNorm) * 100}
		{@const width = Math.abs(maxNorm - minNorm) * 100}
		{@const medianLeft = medianNorm * 100}

		<div
			class="w-full min-w-[130px]"
			title={`Range: ${formatNumber(range.min, 3)} – ${formatNumber(range.max, 3)}, median: ${formatNumber(range.median, 3)}`}
		>
			<div class="relative h-7 px-1">
				<div class="absolute left-1 right-1 top-1/2 h-px bg-muted-foreground/30"></div>

				<div
					class="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full"
					style={`left: calc(${left}% + 0.25rem); width: max(6px, calc(${width}% - 0.5rem)); background-color: ${color}; opacity: 0.45;`}
				></div>

				<div
					class="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border border-background shadow-sm"
					style={`left: ${medianLeft}%; background-color: ${color};`}
				></div>
			</div>

			<div class="flex justify-between px-1 text-[10px] text-muted-foreground">
				<span>{formatNumber(range.scaleMin, 2)}</span>
				<span>{formatNumber(range.scaleMax, 2)}</span>
			</div>
		</div>
	{:else}
		<span class="text-muted-foreground">—</span>
	{/if}
{/snippet}

<div class="rounded-lg border bg-card shadow-sm">
	<div class="border-b px-4 py-3">
		<h3 class="text-sm font-semibold">Current bands (filtered)</h3>
		<p class="mt-1 text-xs text-muted-foreground">
			Each row is a band/cluster. Objective cells show the band range and median.
		</p>
	</div>

	<Table.Root>
		<Table.Header>
			<Table.Row>
				<Table.Head class="w-[220px]">Band / Cluster</Table.Head>

				{#each axisNames as axisName}
					<Table.Head class="min-w-[150px] text-center">
						{axisName}
					</Table.Head>
				{/each}

				<Table.Head class="text-right"># Solutions</Table.Head>
				<Table.Head class="text-right">% of total</Table.Head>
			</Table.Row>
		</Table.Header>

		<Table.Body>
			{#each bands as band}
				<Table.Row
					class="cursor-pointer hover:bg-muted/50 {selectedBand === band.id ? 'bg-muted' : ''}"
					onclick={() => onBandSelect(band.id)}
				>
					<Table.Cell
						class="border-l-4"
						style={`border-left-color: ${selectedBand === band.id ? band.color : 'transparent'};`}
					>
						<div class="flex items-center gap-3">
							<span
								class="h-3 w-3 rounded-full"
								style={`background-color: ${band.color};`}
							></span>

							<div>
								<div class="font-medium">{band.label}</div>
								<div class="text-xs text-muted-foreground">Click to select</div>
							</div>
						</div>
					</Table.Cell>

					{#each axisNames as axisName}
						<Table.Cell>
							{@render RangeCell({
								range: band.objectiveRanges[axisName],
								color: band.color
							})}
						</Table.Cell>
					{/each}

					<Table.Cell class="text-right">
						{band.numSolutions}
					</Table.Cell>

					<Table.Cell class="text-right">
						{#if totalSolutions > 0}
							{formatNumber((band.numSolutions / totalSolutions) * 100, 0)}%
						{:else}
							—
						{/if}
					</Table.Cell>
				</Table.Row>
			{:else}
				<Table.Row>
					<Table.Cell colspan={axisNames.length + 3} class="h-24 text-center">
						No bands available.
					</Table.Cell>
				</Table.Row>
			{/each}
		</Table.Body>
	</Table.Root>

	<div class="flex gap-6 border-t px-4 py-2 text-xs text-muted-foreground">
		<span>Line = objective scale</span>
		<span>Colored segment = band range</span>
		<span>Dot = median</span>
	</div>
</div>