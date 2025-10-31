<script lang="ts">
    import * as Table from '$lib/components/ui/table/index.js';
    import { formatNumber } from '$lib/helpers';
    import type { components } from '$lib/api/client-types';
    type ProblemInfo = components['schemas']['ProblemInfo'];

    let {
        problem,
        previousObjectiveValues,
        displayAccuracy,
        columnsLength
    }: {
        problem: ProblemInfo;
        previousObjectiveValues: { [key: string]: number }[];
        displayAccuracy: number[];
        columnsLength: number;
    } = $props();
</script>

{#if previousObjectiveValues && previousObjectiveValues.length > 0}
    <Table.Row class="pointer-events-none">
        <Table.Cell colspan={columnsLength}>
        </Table.Cell>
    </Table.Row>
    {#each previousObjectiveValues as previousObjectiveValue}
        <Table.Row class='pointer-events-none'>
            <Table.Cell class="border-l-10 border-emerald-400"></Table.Cell>
            <Table.Cell class="italic">
                <div>
                    <span class="text-gray-500">Previous solution</span>
                </div>
            </Table.Cell>
            <Table.Cell></Table.Cell>
            {#each problem.objectives as objective, idx}
                <Table.Cell class="text-gray-500 text-right pr-6">
                    {formatNumber(previousObjectiveValue[objective.symbol], displayAccuracy[idx])}
                </Table.Cell>
            {/each}
        </Table.Row>
    {/each}
{/if}
