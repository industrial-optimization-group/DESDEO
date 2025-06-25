<script lang="ts" generics="TData">
	/**
	 * data-table-toolbar.svelte
	 *
	 * @author Giomara Larraga <glarragw@jyu.fi>
	 * @created June 2025
	 *
	 * @description
	 * This component provides a toolbar for the DESDEO problems data table.
	 * It includes:
	 *   - Input for filtering problems by name.
	 *   - Reset button to clear all column filters (visible when filters are active).
	 *   - "New problem" button.
	 *
	 * @prop {Table<TData>} table - TanStack Table instance, passed via $props in Svelte Runes mode.
	 *
	 * @usage
	 * <DataTableToolbar table={table} />
	 *
	 * @see https://ui.shadcn.com/examples/tasks (source/example adapted)
	 */
	import XIcon from '@lucide/svelte/icons/x';
	import NewIcon from '@lucide/svelte/icons/plus';
	import type { Table } from '@tanstack/table-core';
	import Button from '$lib/components/ui/button/button.svelte';
	import { Input } from '$lib/components/ui/input/index.js';

	let { table }: { table: Table<TData> } = $props();

	const isFiltered = $derived(table.getState().columnFilters.length > 0);
</script>

<div class="flex items-center justify-between">
	<div class="flex flex-1 items-center space-x-2">
		<Input
			placeholder="Filter problems by name..."
			value={(table.getColumn('name')?.getFilterValue() as string) ?? ''}
			oninput={(e) => {
				table.getColumn('name')?.setFilterValue(e.currentTarget.value);
			}}
			onchange={(e) => {
				table.getColumn('name')?.setFilterValue(e.currentTarget.value);
			}}
			class="h-8 w-[150px] lg:w-[250px]"
		/>

		{#if isFiltered}
			<Button variant="ghost" onclick={() => table.resetColumnFilters()} class="h-8 px-2 lg:px-3">
				Reset
				<XIcon />
			</Button>
		{/if}
	</div>
	<Button variant="secondary" size="sm" class="hidden lg:flex">
		<NewIcon />
		<span class="hidden lg:inline">New problem</span>
	</Button>
</div>
