<script lang="ts">
	/**
	 * Checkboxes for the leaf scenarios whose outcomes the chart shows, each with its colour; the
	 * baseline leaf is marked ★. With `aggregate` given, an entry for the aggregate comes first; it
	 * is disabled with a note when not available.
	 */
	import { Button } from '$lib/components/ui/button';
	import Checkbox from '$lib/components/ui/checkbox/checkbox.svelte';
	import { AGGREGATE_COLOR, scenarioColor } from './scenario-chart';

	let {
		leaves,
		baselineLeaf = null,
		checked = $bindable([]),
		aggregate = null,
		aggregateChecked = $bindable(false)
	}: {
		leaves: string[];
		baselineLeaf?: string | null;
		checked?: string[];
		aggregate?: { label: string; available: boolean; note: string } | null;
		aggregateChecked?: boolean;
	} = $props();

	function toggle(leaf: string, on: boolean) {
		// Kept in leaf order so lines and legend follow the scenario model.
		checked = leaves.filter((l) => (l === leaf ? on : checked.includes(l)));
	}
</script>

<div class="space-y-1">
	<div class="flex items-center justify-between gap-2">
		<span class="text-sm font-semibold">Scenarios in chart</span>
		<span class="flex gap-1">
			<Button
				variant="ghost"
				size="sm"
				class="h-6 px-2 text-xs"
				onclick={() => (checked = [...leaves])}>All</Button
			>
			<Button variant="ghost" size="sm" class="h-6 px-2 text-xs" onclick={() => (checked = [])}
				>None</Button
			>
		</span>
	</div>
	<p class="text-xs text-gray-500">
		{checked.length === 0 && !(aggregate && aggregateChecked)
			? 'None checked: the chart shows the target values.'
			: 'The chart shows the objective values of each design in the checked entries.'}
	</p>
	{#if aggregate}
		<div
			class="flex min-w-0 items-center gap-1"
			title={aggregate.available ? undefined : aggregate.note}
		>
			<Checkbox
				id="scenario-aggregate"
				checked={aggregate.available && aggregateChecked}
				disabled={!aggregate.available}
				onCheckedChange={(on) => (aggregateChecked = !!on)}
			/>
			<span
				class="h-1 w-3 shrink-0 rounded-sm"
				style="background-color: {AGGREGATE_COLOR}"
				aria-hidden="true"
			></span>
			<label
				for="scenario-aggregate"
				class="cursor-pointer truncate text-xs font-semibold {aggregate.available
					? ''
					: 'text-gray-400'}"
				style={aggregate.available ? `color: ${AGGREGATE_COLOR}` : undefined}
			>
				{aggregate.label}
			</label>
		</div>
		{#if !aggregate.available}
			<p class="text-xs text-gray-500">{aggregate.note}</p>
		{/if}
	{/if}
	{#if leaves.length > 10}
		<p class="text-xs text-gray-500">
			Beyond ten scenarios the colours repeat in darker or greyer variants; hover a line to see its
			scenario.
		</p>
	{/if}
	<div class="flex max-h-28 flex-wrap gap-x-3 gap-y-1 overflow-y-auto">
		{#each leaves as leaf, i (leaf)}
			<div class="flex min-w-0 items-center gap-1">
				<Checkbox
					id="scenario-{leaf}"
					checked={checked.includes(leaf)}
					onCheckedChange={(on) => toggle(leaf, !!on)}
				/>
				<span
					class="size-3 shrink-0 rounded-sm"
					style="background-color: {scenarioColor(i)}"
					aria-hidden="true"
				></span>
				<label
					for="scenario-{leaf}"
					class="max-w-[9rem] cursor-pointer truncate text-xs"
					style="color: {scenarioColor(i)}"
					title={leaf === baselineLeaf ? `${leaf} (baseline leaf)` : leaf}
				>
					{leaf === baselineLeaf ? '★ ' : ''}{leaf}
				</label>
			</div>
		{/each}
	</div>
</div>
