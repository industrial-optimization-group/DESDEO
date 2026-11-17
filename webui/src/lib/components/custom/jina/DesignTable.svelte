<script lang="ts">
	/**
	 * Table of the results of a JINA iteration: one row per variant or pool scorer with its
	 * design id, target values (binding targets marked) and design variable values. Clicking
	 * a row selects its design; the eye toggles whether the design is plotted, and hidden designs
	 * are greyed.
	 */
	import * as Table from '$lib/components/ui/table/index.js';
	import { Button } from '$lib/components/ui/button';
	import Eye from '@lucide/svelte/icons/eye';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import type {
		JinaDesignInfo,
		JinaIterateResult,
		ProblemInfo,
		Target
	} from '$lib/gen/endpoints/DESDEOFastAPI';
	import { formatNumber, formatValue, targetLabel } from './labels';

	let {
		problem,
		targets,
		results,
		designs,
		designVariables,
		nameLabel = 'Variant',
		selectedId = $bindable(null),
		hidden = $bindable([])
	}: {
		problem: ProblemInfo;
		targets: Target[];
		results: JinaIterateResult[];
		designs: JinaDesignInfo[];
		designVariables: string[];
		nameLabel?: string;
		selectedId?: number | null;
		hidden?: number[];
	} = $props();

	let byId = $derived(new Map(designs.map((d) => [d.id, d])));
	let showBinding = $derived(results.some((r) => (r.binding ?? []).length > 0));
	let ids = $derived([
		...new Set(results.flatMap((r) => (r.design_id != null ? [r.design_id] : [])))
	]);

	function toggleHidden(id: number) {
		hidden = hidden.includes(id) ? hidden.filter((h) => h !== id) : [...hidden, id];
	}
</script>

<div class="h-full overflow-auto">
	<div class="flex gap-1 px-2 pt-1">
		<Button
			variant="ghost"
			size="sm"
			class="h-6 px-2 text-xs"
			onclick={() => (hidden = hidden.filter((h) => !ids.includes(h)))}>Show all</Button
		>
		<Button
			variant="ghost"
			size="sm"
			class="h-6 px-2 text-xs"
			onclick={() => (hidden = [...new Set([...hidden, ...ids])])}>Hide all</Button
		>
	</div>
	<Table.Root>
		<Table.Header>
			<Table.Row>
				<Table.Head class="w-8"><span class="sr-only">Plotted</span></Table.Head>
				<Table.Head>Design</Table.Head>
				<Table.Head>{nameLabel}</Table.Head>
				{#each targets as target (target.symbol)}
					<Table.Head class="text-right">{targetLabel(problem, target)}</Table.Head>
				{/each}
				{#each designVariables as symbol (symbol)}
					<Table.Head class="text-right text-gray-500">{symbol}</Table.Head>
				{/each}
			</Table.Row>
		</Table.Header>
		<Table.Body>
			{#each results as result, i (i)}
				{@const design = result.design_id != null ? byId.get(result.design_id) : undefined}
				{@const isHidden = result.design_id != null && hidden.includes(result.design_id)}
				<Table.Row
					class="cursor-pointer {result.design_id != null && result.design_id === selectedId
						? 'bg-blue-50'
						: ''} {isHidden ? 'text-gray-400' : ''}"
					onclick={() => {
						if (result.design_id != null) selectedId = result.design_id;
					}}
				>
					<Table.Cell class="px-1">
						{#if result.design_id != null}
							{@const id = result.design_id}
							<button
								class="rounded p-1 hover:bg-gray-100"
								title={isHidden
									? 'Hidden from the chart; click to show'
									: 'Click to hide from the chart'}
								aria-label={isHidden
									? `Show design ${id} in the chart`
									: `Hide design ${id} from the chart`}
								aria-pressed={!isHidden}
								onclick={(e) => {
									e.stopPropagation();
									toggleHidden(id);
								}}
							>
								{#if isHidden}<EyeOff class="size-4" />{:else}<Eye class="size-4" />{/if}
							</button>
						{/if}
					</Table.Cell>
					<Table.Cell>{result.design_id != null ? `#${result.design_id}` : '—'}</Table.Cell>
					<Table.Cell>
						{result.name}
						{#if !result.success}
							<span class="block text-xs text-red-700">{result.message}</span>
						{/if}
					</Table.Cell>
					{#each targets as target (target.symbol)}
						{@const binding = (result.binding ?? []).includes(target.symbol)}
						<Table.Cell
							class="text-right {binding ? 'font-semibold' : ''}"
							title={binding ? 'Binding at this reference point' : undefined}
						>
							{formatNumber(result.target_values?.[target.symbol])}{binding ? ' ●' : ''}
						</Table.Cell>
					{/each}
					{#each designVariables as symbol (symbol)}
						<Table.Cell class="text-right text-gray-600">
							{design ? formatValue(design.values[symbol]) : '—'}
						</Table.Cell>
					{/each}
				</Table.Row>
			{/each}
		</Table.Body>
	</Table.Root>
	{#if showBinding}
		<p class="px-2 py-1 text-xs text-gray-500">● binding target at this reference point</p>
	{/if}
</div>
