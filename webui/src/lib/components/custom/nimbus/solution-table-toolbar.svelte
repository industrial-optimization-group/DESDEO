<script lang="ts" generics="TData">
	/**
	 * solution-table-toolbar.svelte
	 *
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created August 2025
	 *
	 * @description
	 * This component provides a toolbar for the NIMBUS solution table.
	 * It includes:
	 *   - Input for filtering solutions by name.
	 *   - Reset button to clear all filters (visible when filters are active).
	 *
	 * @prop {Table<TData>} table - TanStack Table instance, passed via $props in Svelte Runes mode.
	 * 
	 * @features
	 * - Provides search functionality for finding solutions by name
	 * - Shows/hides reset button based on filter state
	 *
	 * @usage
	 * <SolutionTableToolbar table={table} />
	 * 
	 * @dependencies
	 * - @tanstack/table-core for table logic
	 * - $lib/components/ui/button for reset button
	 * - $lib/components/ui/input for search field
	 * - Lucide icons (XIcon) for reset button
	 */
	import XIcon from '@lucide/svelte/icons/x';
	import type { Table } from '@tanstack/table-core';
	import Button from '$lib/components/ui/button/button.svelte';
	import { Input } from '$lib/components/ui/input/index.js';

	let { table }: { table: Table<TData> } = $props();

	const isFiltered = $derived(table.getState().columnFilters.length > 0);
</script>

<div class="flex items-center justify-between">
	<div class="flex flex-1 items-center space-x-2">
		<Input
			placeholder="Filter solutions by name..."
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
</div>