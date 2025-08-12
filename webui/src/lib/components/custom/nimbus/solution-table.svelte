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

	type ProblemInfo = components['schemas']['ProblemInfo'];
	type Solution = components['schemas']['UserSavedSolutionAddress'];
	let {
        problem,
        solverResults,
        selectedSolutions,
        handle_save,
        handle_row_click: onRowClick,
        has_unsaved_changes = $bindable(false),
        isSaved,
        previousObjectiveValues = [],
	}: {
        problem: ProblemInfo;
        solverResults: Array<Solution>;
        selectedSolutions: number[];
        handle_save: (solution: Solution, name:string|undefined) => void;
        handle_row_click: (index:number) => void;
        has_unsaved_changes: boolean;
        isSaved: (solution: Solution) => boolean;
        previousObjectiveValues?: { [key: string]: number }[];
	} = $props();


    // Helper to determine if a row is selected
    function isSelected(index: number): boolean {
        return selectedSolutions.includes(index);
    }

    // Track names being edited in inputs
    let editNames = $state<Record<number, string>>({});
    let inputFocused = $state<Record<number, boolean>>({});
    let inputChanged = $state<Record<number, boolean>>({});

    // Initialize names from solutions whenever results change
    $effect(() => {
        if (solverResults) {
            // Reset edited names when solver results change
            let newEditNames: Record<number, string> = {};
            
            // Initialize with current solution names
            for (let i = 0; i < solverResults.length; i++) {
                const solution = solverResults[i];
                newEditNames[i] = solution.name || '';
            }
            
            // Update state
            editNames = newEditNames;
            // Clear tracking flags
            inputFocused = {};
            inputChanged = {};
        }
    });

    // Update the input tracking when selection changes
    $effect(() => {
        // When selection changes, reset inputs for deselected rows
        if (solverResults) {
            for (let i = 0; i < solverResults.length; i++) {
                if (!selectedSolutions.includes(i) && inputChanged[i]) {
                    // Reset this row's edited name
                    editNames[i] = solverResults[i].name || '';
                    inputChanged[i] = false;
                }
            }
        }
    });

     // Reactive effect to update has_unsaved_changes whenever relevant state changes
    $effect(() => {
        // Check if any currently selected solution has unsaved changes
        let anyChanges = false;
        for (const selectedIndex of selectedSolutions) {
            if (inputChanged[selectedIndex]) {
                anyChanges = true;
                break;
            }
        }
        has_unsaved_changes = anyChanges;
    });

    // Get the display accuracy
    let displayAccuracy = $derived(() => getDisplayAccuracy(problem)); 

    // Update edited name for a solution
    function setEditName(index: number, value: string) {
        editNames[index] = value;
        
        // Mark as changed if the value differs from the solution's name
        const originalName = solverResults[index]?.name || '';
        inputChanged[index] = value !== originalName;
    }

    // Check if input for a specific row is focused
    function isInputFocused(index: number): boolean {
        return !!inputFocused[index];
    }
    
    // Clear input changes for a specific row when saving
    function clearInputChanges(index: number): void {
        inputChanged[index] = false;
    }

</script>


{#if problem}
<Table class="w-auto inline-block">
    <TableBody>
        <!-- Table headers -->
        <TableRow>
            <TableHead>
                Name (optional)
            </TableHead>
            {#each problem.objectives as objective}
                <TableHead>
                    {objective.symbol} {objective.unit ? `/ ${objective.unit}` : ''}({objective.maximize ? 'max' : 'min'})
                </TableHead>
            {/each}
        </TableRow>

        {#if previousObjectiveValues && previousObjectiveValues.length > 0}
            <!-- TODO: previous solution, does not work yet -->
            {#each previousObjectiveValues as previousObjectiveValue}
                <TableRow >
                    <TableCell class="italic">
                        <div class="flex items-center gap-2">
                            <span class="text-gray-500">Previous solution</span>
                        </div>
                    </TableCell>
                    {#each problem.objectives as objective}
                        <TableCell class="text-gray-500">
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
                    class="cursor-pointer {isSelected(index) ? 'bg-primary/20' : ''}"
                >
                    <TableCell class="flex items-center gap-2">
                        {#if isSaved(solution)}
                            <div class="h-2 w-2 rounded-full bg-green-500" title="This solution is saved"></div>
                        {:else}
                            <div class="h-2 w-2 opacity-0"></div> <!-- Invisible placeholder to keep alignment -->
                        {/if}
                        {#if isSelected(index)}
                            <div class="flex items-center gap-2">
                                <Input 
                                    type="text" 
                                    value={editNames[index] || ''}
                                    oninput={(e) => setEditName(index, e.currentTarget.value)}
                                    onclick={(e) => e.stopPropagation()} 
                                    onmousedown={(e) => e.stopPropagation()}
                                    class="transition-all duration-200 {isInputFocused(index) ? 'border-primary shadow-sm' : 'border-gray-200 bg-gray-50 text-gray-600'}"
                                    placeholder={`Solution ${solution.address_result + 1}`}
                                    onfocus={() => inputFocused[index] = true}
                                    onblur={() => inputFocused[index] = false}
                                />
                                <Button 
                                    size="sm" 
                                    onclick={(e) => {
                                        e.stopPropagation(); // Prevent row click
                                        handle_save(solution, editNames[index]);
                                        clearInputChanges(index); // Mark as saved
                                    }}
                                    variant={inputChanged[index] ? "default" : "outline"}
                                >Save</Button>
                            </div>
                        {:else}
                            {#if solution.name}
                                {solution.name}
                            {:else}
                                <span class="text-gray-400">Solution {solution.address_result + 1}</span>
                            {/if}
                        {/if}
                    </TableCell>
                    {#each problem.objectives as objective}
                        <TableCell>
                            {formatNumber(solution.objective_values[objective.symbol], displayAccuracy())}
                        </TableCell>
                    {/each}
                </TableRow>
            {/each}
        {/if}
    </TableBody>
</Table>
{/if}
