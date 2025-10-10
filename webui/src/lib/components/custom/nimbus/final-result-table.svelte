<script lang="ts">
	/**
	 * final-result-table.svelte
	 *
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created October 2025
	 *
	 * @description
	 * This component renders a read-only table showing either objective values or decision variables
	 * for solutions in the DESDEO framework. It is primarily used to display final results after
	 * the decision-making process is completed.
	 *
	 * @props
	 * @property {ProblemInfo} problem - The optimization problem definition.
	 * @property {Solution[]} solverResults - The solutions to display.
	 * @property {string} title - Title to display in the first column header.
	 * @property {'objectives' | 'variables'} mode - Whether to show objective values or decision variables.
	 *
	 * @features
	 * - Displays either objective values or decision variables based on mode
	 * - Supports displaying multiple solutions if needed
	 * - Color-coded headers for objectives to match with possible visualizations (not for variables)
	 * - Formats numbers according to problem's display accuracy
	 * - Read-only display without any interaction functionality
	 *
	 * @dependencies
	 * - @tanstack/table-core for table structure
	 * - $lib/components/ui/table for table UI
	 * - $lib/api/client-types for type definitions
	 * - $lib/helpers for number formatting
	 *
	 * @notes
	 * - This is a simplified version of solution-table.svelte, focused only on displaying data
	 * - Purpose is to make solution-table.svelte less complex and easier to maintain
	 */
	import { type ColumnDef, type Column, type Row, getCoreRowModel } from '@tanstack/table-core';
	import { createSvelteTable } from '$lib/components/ui/data-table/data-table.svelte.js';
	import FlexRender from '$lib/components/ui/data-table/flex-render.svelte';
	import * as Table from '$lib/components/ui/table/index.js';
	import { renderSnippet } from '$lib/components/ui/data-table/render-helpers.js';
	import type { components } from '$lib/api/client-types';
	import { getDisplayAccuracy, formatNumber } from '$lib/helpers';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors.js';

	// Types matching your original solution-table
	type ProblemInfo = components['schemas']['ProblemInfo'];
	type Solution = components['schemas']['SolutionReferenceResponse'];

	// Props matching your original solution-table for compatibility
	let {
		problem,
		solverResults,
		title,
		mode = 'objectives'
	}: {
		problem: ProblemInfo;
		solverResults: Array<Solution>;
		title: string;
		mode: 'objectives' | 'variables';
	} = $props();

	// Get the display accuracy
	let displayAccuracy = $derived(() => getDisplayAccuracy(problem));

	// Define columns based on mode
	const columns: ColumnDef<Solution>[] = $derived.by(() => {
		const items = mode === 'objectives' ? problem.objectives : problem.variables;
		if (!items || items.length === 0) {
			return [];
		}
		return [
			// Title column (always first)
			{
				accessorKey: 'title_column',
				header: title,
				cell: () => '' // Empty cell content
			},
			// Name/Solution column (only if multiple solutions)
			...(solverResults.length > 1
				? [
						{
							accessorKey: 'name',
							header: 'Solution',
							cell: ({ row }: { row: Row<Solution> }) =>
								row.original.name ||
								`Solution ${row.original.solution_index ? row.original.solution_index + 1 : ''}`
						}
					]
				: []),
			// Dynamic columns based on mode
			...items.map((item, idx) => ({
				accessorKey: `${mode === 'objectives' ? 'objective' : 'variable'}_values.${item.symbol}`,
				header: ({ column }: { column: Column<Solution> }) =>
					renderSnippet(ColumnHeader, {
						column,
						item,
						idx,
						mode
					}),
				cell: ({ row }: { row: Row<Solution> }) =>
					renderSnippet(ValueCell, {
						value:
							mode === 'objectives'
								? row.original.objective_values?.[item.symbol]
								: row.original.variable_values?.[item.symbol],
						accuracy: displayAccuracy()
					})
			}))
		];
	});

	const table = createSvelteTable({
		get data() {
			return solverResults || [];
		},
		get columns() {
			return columns;
		},
		getCoreRowModel: getCoreRowModel()
	});
</script>

{#snippet ColumnHeader({ item, idx, mode }: { item: any; idx: number; mode: string })}
	<div
		style={mode === 'objectives'
			? `border-bottom: 4px solid ${COLOR_PALETTE[idx % COLOR_PALETTE.length]}; width: 100%; padding: 0.5rem;`
			: 'width: 100%; padding: 0.5rem;'}
	>
		{item.symbol}
		{#if item.unit}
			/ {item.unit}
		{/if}
		{#if mode === 'objectives' && 'maximize' in item}
			({item.maximize ? 'max' : 'min'})
		{/if}
	</div>
{/snippet}

{#snippet ValueCell({ value, accuracy }: { value: number | null | undefined; accuracy: number })}
	<div class="pr-4 text-right">
		{value != null ? formatNumber(value, accuracy) : '-'}
	</div>
{/snippet}

<div class="flex h-full flex-col items-start">
	<div class="rounded border shadow-sm">
		<Table.Root>
			<Table.Header class="pointer-events-none">
				{#each table.getHeaderGroups() as headerGroup}
					<Table.Row>
						{#each headerGroup.headers as header}
							<Table.Head>
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
				{#each table.getRowModel().rows as row}
					<Table.Row class="bg-gray-300">
						{#each row.getVisibleCells() as cell}
							<Table.Cell>
								<FlexRender content={cell.column.columnDef.cell} context={cell.getContext()} />
							</Table.Cell>
						{/each}
					</Table.Row>
				{/each}
			</Table.Body>
		</Table.Root>
	</div>
</div>
