<script lang="ts">
	/**
	 * solution-table.svelte
	 *
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created August 2025
	 *
	 * @description
	 * This component renders a table of solutions for the NIMBUS interactive multiobjective optimization method.
	 * It displays objective values for solutions and allows for selecting, renaming, saving, and removing solutions.
	 * The table adapts its display based on the current view mode (current, best, or all solutions).
	 *
	 * @props
	 * @property {ProblemInfo} problem - The current optimization problem.
	 * @property {Solution[]} solverResults - The solutions to display in the table.
	 * @property {number[]} selectedSolutions - Indexes of selected solutions.
	 * @property {Function} handle_save - Callback to save a solution with an optional name.
	 * @property {Function} handle_change - Callback to rename a solution.
	 * @property {Function} handle_row_click - Callback when a row is clicked.
	 * @property {Function} handle_remove_saved - Callback to remove a saved solution.
	 * @property {Function} isSaved - Function to check if a solution is already saved.
	 * @property {string} [selected_type_solutions="current"] - The current view mode ("current", "best", "all").
	 * @property {{ [key: string]: number }[]} [secondaryObjectiveValues=[]] - Previous objective values for comparison.
	 * @property {string} [methodPage="nimbus"] - What page is using this. Makes it possible to render different components based on use case.
	 *
	 * @features
	 * - Displays solution names and objective values in a sortable, filterable table.
	 * - Highlights selected solutions.
	 * - Shows save/edit buttons for solutions.
	 * - Displays iteration number for non-current solutions.
	 * - Formats numbers according to problem's display accuracy.
	 * - Filterable by solution name.
	 *
	 * @dependencies
	 * - @tanstack/table-core for table logic.
	 * - $lib/components/ui/table for table UI.
	 * - $lib/components/ui/button for buttons.
	 * - $lib/components/ui/data-table for table functionality.
	 * - $lib/api/client-types for OpenAPI-generated types.
	 * - $lib/helpers for number formatting.
	 * - Svelte Runes mode for reactivity.
	 * - Lucide icons for UI.
	 *
	 * @customization
	 * - Column definitions dynamically built based on the problem objectives.
	 * - Cell rendering customized via Svelte snippets.
	 * - Shows different columns based on selected_type_solutions.
	 *
	 * @notes
	 * - The component works with the NIMBUS method implementation in DESDEO.
	 * - Number formatting respects the problem's precision requirements.
	 */
	import {
		type ColumnDef,
		type Column,
		type Row,
		type ColumnFiltersState,
		type PaginationState,
		type SortingState,
		type VisibilityState,
		type Table as TableType,
		getCoreRowModel,
		getFacetedRowModel,
		getFacetedUniqueValues,
		getFilteredRowModel,
		getPaginationRowModel,
		getSortedRowModel
	} from '@tanstack/table-core';
	import { createSvelteTable } from '$lib/components/ui/data-table/data-table.svelte.js';
	import FlexRender from '$lib/components/ui/data-table/flex-render.svelte';
	import * as Table from '$lib/components/ui/table/index.js';
	import { renderSnippet } from '$lib/components/ui/data-table/render-helpers.js';
	import { Button } from '$lib/components/ui/button';
	import type { components } from '$lib/api/client-types';
	import { getDisplayAccuracy, formatNumber } from '$lib/helpers';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors.js';
	import PenIcon from '@lucide/svelte/icons/pen';
	import BookmarkIcon from '@lucide/svelte/icons/bookmark';
	import type { HTMLAttributes } from 'svelte/elements';
	import { cn } from '$lib/utils.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import ChevronLeftIcon from '@lucide/svelte/icons/chevron-left';
	import ChevronsLeftIcon from '@lucide/svelte/icons/chevrons-left';
	import ChevronsRightIcon from '@lucide/svelte/icons/chevrons-right';
	import ArrowUpIcon from '@lucide/svelte/icons/arrow-up';
	import ArrowDownIcon from '@lucide/svelte/icons/arrow-down';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import SolutionTableToolbar from './solution-table-toolbar.svelte';
	import PreviousSolutions from './solution-table-prev-solutions.svelte';
	import UserResults from './solution-table-gdm-user-results.svelte';

	// Types matching your original solution-table
	type ProblemInfo = components['schemas']['ProblemInfo'];
	type Solution = components['schemas']['SolutionReferenceResponse'];
	type MethodPage = 'nimbus' | 'gnimbus';

	// Props matching your original solution-table for compatibility
	let {
		problem,
		solverResults,
		selectedSolutions,
		handle_save = () => {},
		handle_change = () => {},
		handle_row_click,
		handle_remove_saved = () => {},
		isSaved = () => false,
		savingEnabled = true,
		selected_type_solutions = 'current',
		secondaryObjectiveValues = [],
		methodPage = 'nimbus',
		isFrozen = false,
		personalResultIndex
	}: {
		problem: ProblemInfo;
		solverResults: Array<any>;
		selectedSolutions: number[];
		handle_save?: (solution: Solution, name: string | undefined) => void;
		handle_change?: (solution: Solution) => void;
		handle_row_click: (index: number) => void;
		handle_remove_saved?: (solution: Solution) => void;
		isSaved?: (solution: Solution) => boolean;
		savingEnabled?: boolean;
		selected_type_solutions?: string;
		secondaryObjectiveValues?: { [key: string]: number }[];
		methodPage?: MethodPage;
		isFrozen?: boolean;
		personalResultIndex?: number | null;
	} = $props();

	// Get the display accuracy
	let displayAccuracy = $derived.by(() => getDisplayAccuracy(problem));
	let displayName = $derived((idx: number | null) => {
		let baseName = methodPage === "gnimbus" ? 'Group solution' : 'Solution'
		let indexSuffix = (solverResults.length > 1 && idx !== null) ? idx + 1 : ''
		
		return `${baseName} ${indexSuffix}`;
	});

	// Helper function to get objective title for display
	function getObjectiveTitle(objective: any): string {
		if (!objective) return '';
		
		const tooltip = objective.description || objective.name;
		return objective.unit ? `${tooltip} (${objective.unit})` : tooltip;
	}

	let columnVisibility = $state<VisibilityState>({});
	let columnFilters = $state<ColumnFiltersState>([]);
	let sorting = $state<SortingState>([]);
	let pagination = $state<PaginationState>({ pageIndex: 0, pageSize: 5 });

	// Define columns for the table
	const columns: ColumnDef<any>[] = $derived.by(() => {
		return [
			// First column - Bookmark/Save icon
			{
				accessorKey: 'saved',
				header: ({ column }) => renderSnippet(ColumnHeader, { column, title: '' }),
				cell: ({ row }) =>
					renderSnippet(SavedCell, { solution: row.original, rowIndex: row.index }),
				enableSorting: false
			},
			// Second column - Solution name
			{
				accessorKey: 'name',
				header: ({ column }) => renderSnippet(ColumnHeader, { column, title: 'Name (optional)' }),
				cell: ({ row }) => renderSnippet(NameCell, { solution: row.original }),
				enableSorting: true,
				sortUndefined: 'last'
			},
			// Third column - Edit button (if saved)
			{
				accessorKey: 'edit',
				header: ({ column }) => renderSnippet(ColumnHeader, { column, title: '' }),
				cell: ({ row }) => renderSnippet(EditCell, { solution: row.original }),
				enableSorting: false
			},
			// Fourth column - Iteration (only visible when not "current")
			...(selected_type_solutions !== 'current'
				? [
						{
							id: 'iteration_number',
							accessorFn: (row: any) => String(row.iteration_number ?? row.state_id ?? ''),
							header: ({ column }: { column: Column<Solution> }) =>
								renderSnippet(ColumnHeader, { column, title: 'Iteration' }),
							cell: ({ row }: { row: Row<any> }) =>
								renderSnippet(IterationCell, { solution: row.original }),
							enableSorting: true,
							enableColumnFilter: true,
							filterFn: 'includesString' // Force string-based filtering
						}
					]
				: []),
			// Add columns for each objective
			...problem.objectives.map((objective, idx) => ({
				accessorKey: `objective_values.${objective.symbol}`,
				header: ({ column }: { column: Column<Solution> }) =>
					renderSnippet(ColumnHeader, { column, objective, idx }),
				cell: ({ row }: { row: Row<Solution> }) =>
					renderSnippet(ObjectiveCell, {
						value: row.original.objective_values?.[objective.symbol],
						accuracy: displayAccuracy[idx]
					}),
				enableSorting: true
			}))
		];
	});

	// Create the table
	const table = createSvelteTable({
		get data() {
			return solverResults || [];
		},
		get columns() {
			return columns;
		},
		state: {
			get sorting() {
				return sorting;
			},
			get columnVisibility() {
				return columnVisibility;
			},
			get columnFilters() {
				return columnFilters;
			},
			get pagination() {
				return pagination;
			}
		},
		onSortingChange: (updater) => {
			if (typeof updater === 'function') {
				sorting = updater(sorting);
			} else {
				sorting = updater;
			}
		},
		onColumnFiltersChange: (updater) => {
			if (typeof updater === 'function') {
				columnFilters = updater(columnFilters);
			} else {
				columnFilters = updater;
			}
		},
		onColumnVisibilityChange: (updater) => {
			if (typeof updater === 'function') {
				columnVisibility = updater(columnVisibility);
			} else {
				columnVisibility = updater;
			}
		},
		onPaginationChange: (updater) => {
			if (typeof updater === 'function') {
				pagination = updater(pagination);
			} else {
				pagination = updater;
			}
		},
		enableRowSelection: true,
		enableMultiRowSelection: true,
		getCoreRowModel: getCoreRowModel(),
		getFilteredRowModel: getFilteredRowModel(),
		getPaginationRowModel: getPaginationRowModel(),
		getSortedRowModel: getSortedRowModel(),
		getFacetedRowModel: getFacetedRowModel(),
		getFacetedUniqueValues: getFacetedUniqueValues()
	});

	function isFirstCell(cellIndex: number) {
		return cellIndex === 0;
	}
</script>

<!-- there is only 2 small changes to Pagination in comparison to dataTable: the selectedSolutions and TableType<Solution> -->
{#snippet Pagination({ table }: { table: TableType<Solution> })}
	<div class="flex items-center justify-between px-2">
		<div class="text-muted-foreground flex-1 text-sm">
			{selectedSolutions.length} of
			{table.getFilteredRowModel().rows.length} row(s) selected.
		</div>
		<div class="flex items-center space-x-6 lg:space-x-8">
			<div class="flex items-center space-x-2">
				<p class="text-sm font-medium">Rows per page</p>
				<Select.Root
					allowDeselect={false}
					type="single"
					value={`${table.getState().pagination.pageSize}`}
					onValueChange={(value) => {
						table.setPageSize(Number(value));
					}}
				>
					<Select.Trigger class="h-8 w-[70px]">
						{String(table.getState().pagination.pageSize)}
					</Select.Trigger>
					<Select.Content side="top">
						{#each [5, 10, 15, 20, 25, 30] as pageSize (pageSize)}
							<Select.Item value={`${pageSize}`}>
								{pageSize}
							</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
			</div>
			<div class="flex w-[100px] items-center justify-center text-sm font-medium">
				Page {table.getState().pagination.pageIndex + 1} of
				{table.getPageCount()}
			</div>
			<div class="flex items-center space-x-2">
				<Button
					variant="outline"
					class="hidden size-8 p-0 lg:flex"
					onclick={() => table.setPageIndex(0)}
					disabled={!table.getCanPreviousPage()}
				>
					<span class="sr-only">Go to first page</span>
					<ChevronsLeftIcon />
				</Button>
				<Button
					variant="outline"
					class="size-8 p-0"
					onclick={() => table.previousPage()}
					disabled={!table.getCanPreviousPage()}
				>
					<span class="sr-only">Go to previous page</span>
					<ChevronLeftIcon />
				</Button>
				<Button
					variant="outline"
					class="size-8 p-0"
					onclick={() => table.nextPage()}
					disabled={!table.getCanNextPage()}
				>
					<span class="sr-only">Go to next page</span>
					<ChevronRightIcon />
				</Button>
				<Button
					variant="outline"
					class="hidden size-8 p-0 lg:flex"
					onclick={() => table.setPageIndex(table.getPageCount() - 1)}
					disabled={!table.getCanNextPage()}
				>
					<span class="sr-only">Go to last page</span>
					<ChevronsRightIcon />
				</Button>
			</div>
		</div>
	</div>
{/snippet}

<!-- Cell rendering snippets -->
{#snippet SavedCell({ solution, rowIndex }: { solution: Solution; rowIndex: number })}
	<div class="w-10">
		{#if savingEnabled}
			{#if !isFrozen && isSaved(solution)}
				<Button
					size="icon"
					variant="ghost"
					class="mx-auto flex justify-center text-green-600 transition-colors hover:text-green-700"
					title="Click to remove from saved solutions"
					aria-label="Remove from saved solutions"
					onclick={(e) => {
						e.stopPropagation(); // Prevent row click
						if (handle_remove_saved) {
							handle_remove_saved(solution);
						}
					}}
				>
					<BookmarkIcon class="h-4 w-4 fill-current" />
				</Button>
			{:else if !isFrozen}
				<Button
					size="icon"
					variant="ghost"
					class="mx-auto flex justify-center text-gray-500 transition-colors hover:text-gray-700"
					title="Click to save this solution"
					aria-label="Save this solution"
					onclick={(e) => {
						e.stopPropagation(); // Prevent row click
						handle_save(solution, undefined);
					}}
				>
					<BookmarkIcon class="h-4 w-4 fill-current" />
				</Button>
			{/if}
		{:else}
			<div class="h-4 w-4"></div>
			<!-- Empty div to maintain spacing -->
		{/if}
	</div>
{/snippet}

{#snippet NameCell({ solution }: { solution: Solution })}
	<div>
		{#if solution.name}
			{solution.name}
		{:else}
			<span class="text-gray-400"
				>{displayName(solution.solution_index)}</span
			>
		{/if}
	</div>
{/snippet}

{#snippet EditCell({ solution }: { solution: Solution })}
	{#if !isFrozen && isSaved(solution)}
		<Button
			size="icon"
			onclick={(e) => {
				e.stopPropagation(); // Prevent row click
				handle_change(solution);
			}}
			variant="ghost"
			class="h-8 w-8"
			title="Rename solution"
		>
			<PenIcon class="h-4 w-4" />
			<span class="sr-only">Rename solution</span>
		</Button>
	{/if}
{/snippet}

{#snippet IterationCell({ solution }: { solution: any })}
	{#if methodPage ==="gnimbus"}
		{solution.iteration_number}
	{:else}
		{solution.state_id}
	{/if}
{/snippet}

{#snippet ObjectiveCell({
	value,
	accuracy
}: {
	value: number | null | undefined;
	accuracy: number;
})}
	<div class="pr-4 text-right">
		{value != null ? formatNumber(value, accuracy) : '-'}
	</div>
{/snippet}

{#snippet ColumnHeader({
	column,
	title,
	objective,
	idx,
	class: className,
	...restProps
}: {
	column: Column<Solution>;
	title?: string;
	objective?: any;
	idx?: number;
} & HTMLAttributes<HTMLDivElement>)}
	{#if !column?.getCanSort() || isFrozen}
		<!-- Non-sortable column header -->
		<div
			class={cn('px-2 py-1', className)}
			style={objective
				? `border-bottom: 4px solid ${COLOR_PALETTE[(idx ?? 0) % COLOR_PALETTE.length]}; width: 100%; padding: 0.5rem;`
				: ''}
			title={objective ? getObjectiveTitle(objective) : undefined}
			{...restProps}
		>
			{#if objective}
				{objective.name}
				{objective.unit ? `/ ${objective.unit}` : ''}({objective.maximize ? 'max' : 'min'})
			{:else if title}
				{title}
			{/if}
		</div>
	{:else}
		<!-- Sortable column header -->
		<div
			class={cn('flex items-center', className)}
			style={objective
				? `border-bottom: 6px solid ${COLOR_PALETTE[(idx ?? 0) % COLOR_PALETTE.length]}; width: 100%; padding: 0.5rem;`
				: ''}
			{...restProps}
		>
			<Button
				variant="ghost"
				size="sm"
				onclick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
				class="-ml-3 h-8 {objective ? 'flex-1 justify-start text-left' : ''}"
				title={objective ? getObjectiveTitle(objective) : undefined}
            >
				<span>
					{#if objective}
						{objective.name}
						{objective.unit ? `/ ${objective.unit}` : ''}({objective.maximize ? 'max' : 'min'})
					{:else if title}
						{title}
					{/if}
				</span>
				{#if column.getIsSorted() === 'desc'}
					<ArrowDownIcon class="ml-2 h-4 w-4" />
				{:else if column.getIsSorted() === 'asc'}
					<ArrowUpIcon class="ml-2 h-4 w-4" />
				{:else}
					<ChevronsUpDownIcon class="ml-2 h-4 w-4 opacity-50" />
				{/if}
			</Button>
		</div>
	{/if}
{/snippet}

{#if problem}
	<div class="flex h-full flex-col items-start">
		{#if selected_type_solutions !== 'current' && !isFrozen}
			{#if methodPage ==='gnimbus'}
				<SolutionTableToolbar
					{table}
					filterColumn="iteration_number"
					placeholder="Filter solutions by iteration..."
				/>
			{:else}
				<SolutionTableToolbar {table} />
			{/if}
		{/if}
		<div class="overflow-auto rounded border shadow-sm">
			<!-- Header and previous solutions -->
			<Table.Root>
				<Table.Header>
					{#each table.getHeaderGroups() as headerGroup (headerGroup.id)}
						<Table.Row>
							{#each headerGroup.headers as header (header.id)}
								<Table.Head colspan={header.colSpan}>
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

				<!-- Main table with TanStack Table -->
				<Table.Body>
					{#each table.getRowModel().rows as row (row.id)}
						<Table.Row
							onclick={!isFrozen ? () => handle_row_click(row.index) : undefined}
							class="{isFrozen ? '' : 'cursor-pointer'} {selectedSolutions.includes(row.index)
								? 'bg-gray-300'
								: ''} {isFrozen ? 'pointer-events-none' : ''}"
							aria-label="Select row"
						>
							{#each row.getVisibleCells() as cell, cellIndex (cell.id)}
								<Table.Cell
									class={isFirstCell(cellIndex)
										? selectedSolutions.includes(row.index)
											? 'border-l-10 border-blue-600'
											: 'border-l-10'
										: ''}
								>
									<FlexRender content={cell.column.columnDef.cell} context={cell.getContext()} />
								</Table.Cell>
							{/each}
						</Table.Row>
					{:else}
						<Table.Row>
							<Table.Cell colspan={columns.length} class="h-24 text-center">
								No solutions available.
							</Table.Cell>
						</Table.Row>
					{/each}
					{#if selected_type_solutions === 'current'}
						{#if methodPage === 'nimbus' && secondaryObjectiveValues.length > 0}
							<PreviousSolutions
								{problem}
								previousObjectiveValues={secondaryObjectiveValues}
								displayAccuracy={displayAccuracy}
								columnsLength={columns.length}
							/>
						{:else if methodPage === 'gnimbus'}
							<UserResults
								{problem}
								objectiveValues={secondaryObjectiveValues}
								displayAccuracy={displayAccuracy}
								columnsLength={columns.length}
								personalResultIndex={personalResultIndex ?? -1}
							/>
						{/if}
					{/if}
				</Table.Body>
			</Table.Root>
		</div>
		{#if selected_type_solutions !== 'current' && !isFrozen}
			{@render Pagination({ table })}
		{/if}
	</div>
{/if}
