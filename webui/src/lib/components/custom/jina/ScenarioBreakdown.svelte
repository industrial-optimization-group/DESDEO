<script lang="ts">
	/**
	 * Objective values of one design in each leaf scenario, compact with the full value on hover.
	 * Leaves listed in `failed` show their message instead of values; rows of `checkedLeaves` are bold.
	 */
	import * as Table from '$lib/components/ui/table/index.js';
	import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';
	import { baselineFirst, compactNumber, formatNumber, objectiveLabel } from './labels';

	let {
		problem,
		leafObjectives,
		failed = {},
		baselineLeaf = null,
		leafColors = {},
		checkedLeaves = []
	}: {
		problem: ProblemInfo;
		leafObjectives: Record<string, Record<string, number>>;
		failed?: Record<string, string>;
		baselineLeaf?: string | null;
		leafColors?: Record<string, string>;
		checkedLeaves?: string[];
	} = $props();

	let leaves = $derived(
		baselineFirst(
			[...new Set([...Object.keys(leafObjectives), ...Object.keys(failed)])],
			baselineLeaf
		)
	);
	let objectives = $derived([
		...new Set(Object.values(leafObjectives).flatMap((values) => Object.keys(values)))
	]);
</script>

{#if leaves.length === 0}
	<p class="p-2 text-sm text-gray-500">No per-scenario values.</p>
{:else}
	<!-- Fixed layout at the pane's width: the scenario column takes a third and the objectives share
	     the rest; names and values that do not fit are cut short, with the full text on hover. -->
	<Table.Root class="table-fixed text-xs">
		<Table.Header>
			<Table.Row>
				<Table.Head class="w-1/3 truncate px-1">Scenario</Table.Head>
				{#each objectives as symbol (symbol)}
					<Table.Head class="truncate px-1 text-right" title={objectiveLabel(problem, symbol)}>
						{objectiveLabel(problem, symbol)}
					</Table.Head>
				{/each}
			</Table.Row>
		</Table.Header>
		<Table.Body>
			{#each leaves as leaf (leaf)}
				{@const isBaseline = leaf === baselineLeaf}
				<Table.Row class={checkedLeaves.includes(leaf) ? 'font-semibold' : ''}>
					<Table.Cell
						class="truncate px-1"
						style={leafColors[leaf] ? `color: ${leafColors[leaf]}` : undefined}
						title={isBaseline ? `${leaf} (baseline leaf of the antifragility analysis)` : leaf}
					>
						{#if isBaseline}<span aria-label="baseline">★</span>{/if}
						{leaf}
					</Table.Cell>
					{#if failed[leaf] !== undefined}
						<Table.Cell
							colspan={objectives.length}
							class="truncate px-1 text-red-700"
							title={failed[leaf]}
						>
							{failed[leaf]}
						</Table.Cell>
					{:else}
						{#each objectives as symbol (symbol)}
							<Table.Cell
								class="truncate px-1 text-right"
								title={formatNumber(leafObjectives[leaf]?.[symbol], 8)}
							>
								{compactNumber(leafObjectives[leaf]?.[symbol])}
							</Table.Cell>
						{/each}
					{/if}
				</Table.Row>
			{/each}
		</Table.Body>
	</Table.Root>
{/if}
