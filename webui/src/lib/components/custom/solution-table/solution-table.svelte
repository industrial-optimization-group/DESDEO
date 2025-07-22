<script lang="ts">
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import Table from '$lib/components/ui/table/table.svelte';
	import TableBody from '$lib/components/ui/table/table-body.svelte';
	import TableRow from '$lib/components/ui/table/table-row.svelte';
	import TableHead from '$lib/components/ui/table/table-head.svelte';
	import TableCell from '$lib/components/ui/table/table-cell.svelte';
	import type { components } from '$lib/api/client-types';

	type ProblemInfo = components['schemas']['ProblemInfo'];

	let {
        problem,
        solverResults,
        selectedSolution = $bindable(0),
        onRowClick
	}: {
        problem: ProblemInfo;
        solverResults: Array<{
			optimal_objectives: Record<string, number | number[]>;
			[key: string]: any;
		}>;
        selectedSolution: number;
        onRowClick: () => void;
	} = $props();


    function handleRowClick(index: number) {
        selectedSolution = index;
        onRowClick();
    }

    // Handle selecting multiple rows, not implemented yet
    // function handleSelect(index: number) {
    //         // Allow selecting multiple rows
    //         if (isSelected(index)) {
    //             selectedMultipleSolutions = selectedMultipleSolutions.filter(i => i !== index)
    //         } else {
    //             selectedMultipleSolutions = [...selectedMultipleSolutions, index];
    //         }
    //     onSelect(); // as props
    // }
</script>


{#if problem}
<Table class="w-auto inline-block">
    <TableBody>
        <!-- Table headers -->
        <TableRow>
            {#each problem.objectives as objective}
                <TableHead>
                    {objective.name} {objective.unit ? `/ ${objective.unit}` : ''}
                </TableHead>
            {/each}
        </TableRow>

        {#if solverResults && solverResults.length > 0}
            <!-- Table rows for solutions -->
            {#each solverResults as result, index}
                <TableRow 
                    onclick={() => handleRowClick(index)}
                    class="cursor-pointer {selectedSolution === index ? 'bg-primary/20' : ''}"
                >
                    {#each problem.objectives as objective}
                        <TableCell>
                            {result.optimal_objectives[objective.symbol]}
                        </TableCell>
                    {/each}
                </TableRow>
            {/each}
        {/if}
    </TableBody>
</Table>
{/if}
