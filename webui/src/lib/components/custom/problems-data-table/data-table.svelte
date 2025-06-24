<script lang="ts">
	import {
		type ColumnDef,
		type ColumnFiltersState,
		type PaginationState,
		type Row,
		type RowSelectionState,
		type SortingState,
		type VisibilityState,
		type Table as TableType,
		getCoreRowModel,
		getFacetedRowModel,
		getFacetedUniqueValues,
		getFilteredRowModel,
		getPaginationRowModel,
		getSortedRowModel,
		type Column
	} from '@tanstack/table-core';
	import DataTableToolbar from './data-table-toolbar.svelte';
	import { createSvelteTable } from '$lib/components/ui/data-table/data-table.svelte.js';
	import FlexRender from '$lib/components/ui/data-table/flex-render.svelte';
	import * as Table from '$lib/components/ui/table/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	//import { problemSchema, type Problem } from '../../data/schemas.js';
	import { renderComponent, renderSnippet } from '$lib/components/ui/data-table/render-helpers.js';
	import { Button, buttonVariants } from '$lib/components/ui/button/index.js';
	import EllipsisIcon from '@lucide/svelte/icons/ellipsis';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import ChevronLeftIcon from '@lucide/svelte/icons/chevron-left';
	import ChevronsLeftIcon from '@lucide/svelte/icons/chevrons-left';
	import ChevronsRightIcon from '@lucide/svelte/icons/chevrons-right';
	import ArrowUpIcon from '@lucide/svelte/icons/arrow-up';
	import ArrowDownIcon from '@lucide/svelte/icons/arrow-down';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import Play from '@lucide/svelte/icons/play';

	import * as Select from '$lib/components/ui/select/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';

	import type { HTMLAttributes } from 'svelte/elements';
	import { cn } from '$lib/utils.js';
	import { createEventDispatcher } from 'svelte';
	import type { components } from '$lib/api/client-types';

	// Use the OpenAPI type for a problem
	type ProblemInfo = components['schemas']['ProblemInfo'];

	import { z } from 'zod';

	export const problemSchema = z.object({
		id: z.number(),
		name: z.string(),
		description: z.string(),
		is_convex: z.boolean().nullable(),
		is_linear: z.boolean().nullable(),
		is_twice_differentiable: z.boolean().nullable(),
		scenario_keys: z.array(z.string()).nullable(),
		variable_domain: z.string(),
		user_id: z.number(),
		constants: z.array(z.any()).nullable(),
		tensor_constants: z.array(z.any()).nullable(),
		variables: z.array(z.any()).nullable(),
		tensor_variables: z.array(z.any()).nullable(),
		objectives: z.array(z.any()),
		constraints: z.array(z.any()).nullable(),
		scalarization_funcs: z.array(z.any()).nullable(),
		extra_funcs: z.array(z.any()).nullable(),
		discrete_representation: z.any().nullable(),
		simulators: z.array(z.any()).nullable()
	});
	// Use ProblemInfo everywhere you previously used Problem or PageData
	//let { data }: ProblemInfo[] = $props();
	const { data } = $props<{ data: ProblemInfo[] }>();

	let rowSelection = $state<RowSelectionState>({});
	let columnVisibility = $state<VisibilityState>({});
	let columnFilters = $state<ColumnFiltersState>([]);
	let sorting = $state<SortingState>([]);
	let pagination = $state<PaginationState>({ pageIndex: 0, pageSize: 5 });

	const dispatch = createEventDispatcher();

	const columns: ColumnDef<ProblemInfo>[] = [
		{
			accessorKey: 'name',
			header: ({ column }) => renderSnippet(ColumnHeader, { column, title: 'Name' }),
			cell: ({ row }) => {
				return renderSnippet(NameCell, {
					value: row.original.name
				});
			}
		},
		{
			accessorKey: 'objectives',
			header: ({ column }) =>
				renderSnippet(ColumnHeader, {
					column,
					title: '# Objectives'
				}),
			cell: ({ row }) => {
				return renderSnippet(NumberCell, {
					value: row.original.objectives.length
				});
			},
			filterFn: (row, id, value) => {
				return value.includes(row.getValue(id));
			}
		},
		{
			accessorKey: 'variables',
			header: ({ column }) => {
				return renderSnippet(ColumnHeader, {
					title: '# Variables',
					column
				});
			},
			cell: ({ row }) => {
				return renderSnippet(NumberCell, {
					value: row.original.variables?.length ?? 0
				});
			},
			filterFn: (row, id, value) => {
				return value.includes(row.getValue(id));
			}
		},
		{
			id: 'actions',
			header: ({ column }) => {
				return renderSnippet(ColumnHeader, {
					title: 'More',
					column
				});
			},
			cell: ({ row }) => renderSnippet(RowActions, { row })
		},
		{
			id: 'solve',
			header: ({ column }) => {
				return renderSnippet(ColumnHeader, {
					title: 'Solve',
					column
				});
			},
			cell: ({ row }) => renderSnippet(RowSolve, { row })
		}
	];

	const table = createSvelteTable({
		get data() {
			return data;
		},
		state: {
			get sorting() {
				return sorting;
			},
			get columnVisibility() {
				return columnVisibility;
			},
			get rowSelection() {
				return rowSelection;
			},
			get columnFilters() {
				return columnFilters;
			},
			get pagination() {
				return pagination;
			}
		},
		columns,
		enableRowSelection: true,
		enableMultiRowSelection: false,

		onRowSelectionChange: (updater) => {
			if (typeof updater === 'function') {
				rowSelection = updater(rowSelection);
			} else {
				rowSelection = updater;
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
		getCoreRowModel: getCoreRowModel(),
		getFilteredRowModel: getFilteredRowModel(),
		getPaginationRowModel: getPaginationRowModel(),
		getSortedRowModel: getSortedRowModel(),
		getFacetedRowModel: getFacetedRowModel(),
		getFacetedUniqueValues: getFacetedUniqueValues()
	});

	function handleRowClick(row: any) {
		row.toggleSelected(true);
		dispatch('select', row.original);
	}
</script>

{#snippet NumberCell({ value }: { value: number })}
	<div class="flex w-[100px] items-center">
		<span>{value}</span>
	</div>
{/snippet}

{#snippet NameCell({ value }: { value: string })}
	<div class="flex space-x-2">
		<span class="max-w-[500px] truncate font-medium">
			{value}
		</span>
	</div>
{/snippet}

{#snippet DefinedByCell({ value }: { value: string })}
	<div class="flex items-center">
		<span>{value}</span>
	</div>
{/snippet}

{#snippet RowActions({ row }: { row: Row<ProblemInfo> })}
	{@const problem = problemSchema.parse(row.original)}
	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button
					{...props}
					variant="ghost"
					class="hover:bg-muted data-[state=open]:bg-muted flex h-8 w-8 p-0"
				>
					<EllipsisIcon />
					<span class="sr-only">Open Menu</span>
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content class="w-[160px]" align="end">
			<DropdownMenu.Item class="data-highlighted:bg-muted">Details</DropdownMenu.Item>
			<DropdownMenu.Item class="data-highlighted:bg-muted">Edit</DropdownMenu.Item>
			<DropdownMenu.Item class="data-highlighted:bg-muted">Download</DropdownMenu.Item>
			<DropdownMenu.Item
				class="data-highlighted:bg-muted text-red-500 data-highlighted:text-red-700"
				>Delete</DropdownMenu.Item
			>
		</DropdownMenu.Content>
	</DropdownMenu.Root>
{/snippet}

{#snippet RowSolve({ row }: { row: Row<ProblemInfo> })}
	{@const problem = problemSchema.parse(row.original)}
	<Tooltip.Provider>
		<Tooltip.Root>
			<Tooltip.Trigger
				class={buttonVariants({
					variant: 'outline',
					size: 'icon',
					class: 'flex h-8 w-8 cursor-pointer p-0'
				})}
			>
				<a href={`/method?problemId=${encodeURIComponent(problem.id)}`}>
					<Play />
				</a>
			</Tooltip.Trigger>
			<Tooltip.Content>
				<p>Solve this problem</p>
			</Tooltip.Content>
		</Tooltip.Root>
	</Tooltip.Provider>
{/snippet}

{#snippet Pagination({ table }: { table: TableType<ProblemInfo> })}
	<div class="flex items-center justify-between px-2">
		<div class="text-muted-foreground flex-1 text-sm">
			{table.getFilteredSelectedRowModel().rows.length} of
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

{#snippet ColumnHeader({
	column,
	title,
	class: className,
	...restProps
}: { column: Column<ProblemInfo>; title: string } & HTMLAttributes<HTMLDivElement>)}
	{#if !column?.getCanSort()}
		<div class={className} {...restProps}>
			{title}
		</div>
	{:else}
		<div class={cn('flex items-center', className)} {...restProps}>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							size="sm"
							class="hover:bg-muted data-[state=open]:bg-muted -ml-3 h-8"
						>
							<span>
								{title}
							</span>
							{#if column.getIsSorted() === 'desc'}
								<ArrowDownIcon />
							{:else if column.getIsSorted() === 'asc'}
								<ArrowUpIcon />
							{:else}
								<ChevronsUpDownIcon />
							{/if}
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start">
					<DropdownMenu.Item
						class="data-highlighted:bg-muted"
						onclick={() => column.toggleSorting(false)}
					>
						<ArrowUpIcon class="text-muted-foreground/70 mr-2 size-3.5" />
						Asc
					</DropdownMenu.Item>
					<DropdownMenu.Item
						class="data-highlighted:bg-muted"
						onclick={() => column.toggleSorting(true)}
					>
						<ArrowDownIcon class="text-muted-foreground/70 mr-2 size-3.5" />
						Desc
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	{/if}
{/snippet}

<div class="w-full space-y-4">
	<DataTableToolbar {table} />
	<div class="rounded-md border">
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
			<Table.Body>
				{#each table.getRowModel().rows as row (row.id)}
					<Table.Row
						data-state={row.getIsSelected() && 'selected'}
						onclick={() => handleRowClick(row)}
						class="data-[state=selected]:bg-muted cursor-pointer"
						aria-label="Select row"
					>
						{#each row.getVisibleCells() as cell (cell.id)}
							<Table.Cell>
								<FlexRender content={cell.column.columnDef.cell} context={cell.getContext()} />
							</Table.Cell>
						{/each}
					</Table.Row>
				{:else}
					<Table.Row>
						<Table.Cell colspan={columns.length} class="h-24 text-center">No results.</Table.Cell>
					</Table.Row>
				{/each}
			</Table.Body>
		</Table.Root>
	</div>
	{@render Pagination({ table })}
</div>
