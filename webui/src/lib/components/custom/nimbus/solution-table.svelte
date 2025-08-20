<script lang="ts">
	import Table from '$lib/components/ui/table/table.svelte';
	import TableBody from '$lib/components/ui/table/table-body.svelte';
	import TableRow from '$lib/components/ui/table/table-row.svelte';
	import TableHead from '$lib/components/ui/table/table-head.svelte';
	import TableCell from '$lib/components/ui/table/table-cell.svelte';
	import type { components } from '$lib/api/client-types';
	import Input from '$lib/components/ui/input/input.svelte';
	import { Button } from '$lib/components/ui/button';
    import { getDisplayAccuracy, formatNumber } from '$lib/helpers';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors.js';
	import TableHeader from '$lib/components/ui/table/table-header.svelte';
	import PenIcon from '@lucide/svelte/icons/pen';
	import BookmarkIcon from '@lucide/svelte/icons/bookmark';

	type ProblemInfo = components['schemas']['ProblemInfo'];
	type Solution = components['schemas']['UserSavedSolutionAddress'];
    let {
        problem,
        solverResults,
        selectedSolutions,
        handle_save,
        handle_change,
        handle_row_click: onRowClick,
        isSaved,
        previousObjectiveValues = [],
	}: {
        problem: ProblemInfo;
        solverResults: Array<Solution>;
        selectedSolutions: number[];
        handle_save: (solution: Solution, name:string|undefined) => void;
        handle_change: (solution: Solution) => void;
        handle_row_click: (index:number) => void;
        isSaved: (solution: Solution) => boolean;
        previousObjectiveValues?: { [key: string]: number }[];
	} = $props();
    // Helper to determine if a row is selected
    function isSelected(index: number): boolean {
        return selectedSolutions.includes(index);
    }

    let inputFocused = $state<Record<number, boolean>>({});

    // Initialize names from solutions whenever results change
    $effect(() => {
        if (solverResults) {
            // Clear tracking flags
            inputFocused = {};
        }
    });

    // Get the display accuracy
    let displayAccuracy = $derived(() => getDisplayAccuracy(problem)); 

    // Check if input for a specific row is focused
    function isInputFocused(index: number): boolean {
        return !!inputFocused[index];
    }

</script>

{#if problem}
<div class="h-full flex flex-col items-start">
    <div class="border rounded shadow-sm overflow-auto">
        <Table>
            <!-- Table headers - make headers sticky when scrolling -->
            <TableHeader>
                <TableRow>
                    <TableHead>
                    </TableHead>
                    <TableHead>
                        Name (optional)
                    </TableHead>
                    <TableHead class="w-15"></TableHead>
                    {#each problem.objectives as objective, idx}
                    <TableHead style="background-color: {COLOR_PALETTE[idx % COLOR_PALETTE.length]}">
                        {objective.symbol} {objective.unit ? `/ ${objective.unit}` : ''}({objective.maximize ? 'max' : 'min'})
                    </TableHead>
                    {/each}
                </TableRow>
            </TableHeader>
            <TableBody > 
                {#if previousObjectiveValues && previousObjectiveValues.length > 0}
                    {#each previousObjectiveValues as previousObjectiveValue}
                        <TableRow class='bg-teal-400/30 pointer-events-none'>
                            <TableCell></TableCell>
                            <TableCell class="italic">
                                <div>
                                    <span class="text-gray-500">Previous solution</span>
                                </div>
                            </TableCell>
                            <TableCell></TableCell>

                            {#each problem.objectives as objective}
                                <TableCell class="text-gray-500 text-right pr-4">
                                    {formatNumber(previousObjectiveValue[objective.symbol], displayAccuracy())}
                                </TableCell>
                            {/each}
                        </TableRow>
                        
                    {/each}
                {/if}

                {#if solverResults && solverResults.length > 0}
                    <!-- Table rows for solutions -->
                    {#each solverResults as solution, index}
                        <TableRow 
                            onclick={() => onRowClick(index)}
                            class="cursor-pointer {isSelected(index) ? 'bg-blue-600/30' : ''}"
                        >
                            <TableCell class="w-10">
                                {#if isSaved(solution)}
                                    <div 
                                        class="flex justify-center text-green-600" 
                                        title="This solution is saved"
                                    >
                                        <BookmarkIcon class="h-4 w-4 fill-current" />
                                    </div>
                                {:else}
                                    <Button
                                        size="icon"
                                        variant="ghost"
                                        class="flex justify-center text-gray-500 hover:text-gray-700 transition-colors mx-auto"
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
                            </TableCell> 
                            <TableCell>
                                {#if solution.name}
                                    {solution.name}
                                {:else}
                                    <span class="text-gray-400">Solution {solution.address_result + 1} ({solution.address_state})</span>
                                {/if}
                                </TableCell>
                                <TableCell>
                                {#if isSaved(solution)}
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
                                </TableCell>                            
                            {#each problem.objectives as objective}
                                <TableCell class="text-right pr-4">
                                    {formatNumber(solution.objective_values[objective.symbol], displayAccuracy())}
                                </TableCell>
                            {/each}
                        </TableRow>
                    {/each}
                {/if}
            </TableBody>
        </Table>
    </div>
</div>
{/if}
