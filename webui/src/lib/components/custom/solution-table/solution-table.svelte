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
        selectedSolutions = $bindable([]),
        onSelect,
		phase = "classify" as 'classify' | 'intermediate' | 'save' | 'finish'
	}: {
        problem: ProblemInfo;
        solverResults: Array<{
			optimal_objectives: Record<string, number | number[]>;
			[key: string]: any;
		}>;
        selectedSolutions: number[];
        onSelect: () => void;
		phase?: 'classify' | 'intermediate' | 'save' | 'finish';
	} = $props();

    // Helper to determine if a row is selected
    function isSelected(index: number): boolean {
        return selectedSolutions.includes(index);
    }

    // Handle row selection based on the phase
    function handleRowClick(index: number) {
        if (phase === 'classify') {
            // Allow selecting only one row
            selectedSolutions = [index];
        } else if (phase === 'intermediate') {
            // Allow selecting up to 2 rows
            if (isSelected(index)) {
                selectedSolutions = selectedSolutions.filter(i => i !== index)
            } else if (selectedSolutions.length < 2) {
                selectedSolutions = [...selectedSolutions, index];
            }
        } else if (phase === 'save') {
            // Allow selecting multiple rows
            if (isSelected(index)) {
                selectedSolutions = selectedSolutions.filter(i => i !== index)
            } else {
                selectedSolutions = [...selectedSolutions, index];
            }
        }
        onSelect();
    }
</script>


{#if problem && phase ==="classify"}
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
                    class="cursor-pointer {isSelected(index) ? 'bg-primary/20' : ''}"
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
