<script lang="ts">
    import * as Table from '$lib/components/ui/table';
    import { formatNumber } from '$lib/helpers';
    import type { ObjectiveDB } from '$lib/gen/endpoints/DESDEOFastAPI';

    let { problem, solutions, referenceIndex = 0 } = $props();
    
    // One of the solutions has to be a reference
    const reference = $derived(solutions[referenceIndex]);

    // Function that decides wether is the candidate's value better than reference value
    function isBetter(
        objective:ObjectiveDB, 
        candidate: number | null | undefined, 
        referenceValue: number | null | undefined
    ): boolean {
        if(candidate == null || referenceValue == null) return false;

        return objective.maximize
            ? candidate > referenceValue  // maximize → bigger is better
            : candidate < referenceValue; // minimize → smaller is better
    }

    // Function that computes absolute and percentage difference
    function getChange(
        candidate: number | null | undefined, 
        referenceValue: number | null | undefined
    ): {diff: number; percent: number} | null {
        if (candidate == null || referenceValue == null) return null;

        const diff = candidate - referenceValue;
        const percent = referenceValue !== 0
            ? (diff / referenceValue) * 100
            : 0;

        return { diff, percent };
    }
</script>

<Table.Root>
    <Table.Header>
        <Table.Row>
            <Table.Head>Objective</Table.Head>

            {#each solutions as s}
                <Table.Head>{s.name ?? `Solution ${s.solution_index + 1}`}</Table.Head>
            {/each}
        </Table.Row>
    </Table.Header>

    <Table.Body>
        {#each problem.objectives as objective}
            <Table.Row>
                <!-- Objective name -->
                <Table.Cell>
                    {objective.name} ({objective.maximize ? 'max' : 'min'})
                </Table.Cell>

                <!-- Values -->
                {#each solutions as solution, i}
                    {@const value = solution.objective_values?.[objective.symbol]}
                    {@const refValue = reference.objective_values?.[objective.symbol]}
                    {@const change = i === referenceIndex ? null : getChange(value, refValue)}
                    {@const better = i === referenceIndex ? false : isBetter(objective, value, refValue)}

                    <Table.Cell
                        class={
                            i === referenceIndex
                                ? ''
                                : better
                                    ? 'text-green-600'
                                    : 'text-red-600'
                        }
                    >
                        {#if value != null}
                            {formatNumber(value)}
                        {:else}
                            -
                        {/if}

                        {#if change}
                            <div class="text-xs opacity-70">
                                {change.diff > 0 ? '+' : ''}
                                {formatNumber(change.diff, 2)} (
                                {formatNumber(change.percent, 1)}%)
                            </div>
                        {/if}
                    </Table.Cell>
                {/each}
            </Table.Row>
        {/each}
    </Table.Body>
</Table.Root>