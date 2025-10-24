<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import { formatNumber } from '$lib/helpers';
	import type { components } from '$lib/api/client-types';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import { Button } from '$lib/components/ui/button';
	type ProblemInfo = components['schemas']['ProblemInfo'];

	let {
		problem,
		previousObjectiveValues,
		displayAccuracy,
		columnsLength,
		personalResultIndex
	}: {
		problem: ProblemInfo;
		previousObjectiveValues: { [key: string]: number }[];
		displayAccuracy: number;
		columnsLength: number;
		personalResultIndex: number;
	} = $props();

	let showOtherSolutions = $state(false);
</script>

{#if previousObjectiveValues && previousObjectiveValues.length > 0}
	<Table.Row class="pointer-events-none">
		<Table.Cell colspan={columnsLength}></Table.Cell>
	</Table.Row>

	{#if personalResultIndex === -1}
		<!-- Show all solutions without distinction when user is owner but not DM -->
		{#each previousObjectiveValues as previousObjectiveValue, index}
			<Table.Row class="pointer-events-none">
				<Table.Cell class="border-l-10 border-teal-400"></Table.Cell>
				<Table.Cell class="italic">
					<div>
						<span>User {index + 1}'s solution</span>
					</div>
				</Table.Cell>
				<Table.Cell></Table.Cell>
				{#each problem.objectives as objective}
					<Table.Cell class="pr-6 text-right">
						{formatNumber(previousObjectiveValue[objective.symbol], displayAccuracy)}
					</Table.Cell>
				{/each}
			</Table.Row>
		{/each}
	{:else}
		<!-- Personal Solution -->
		{#if previousObjectiveValues[personalResultIndex]}
			<Table.Row class="hover:bg-gray-200">
				<Table.Cell class="border-l-10 border-teal-400">
					{#if previousObjectiveValues.length > 1}
						<Button
							size="icon"
							variant="ghost"
							class="mx-auto flex justify-center transition-colors"
							onclick={() => {
								showOtherSolutions = !showOtherSolutions;
							}}
						>
							{#if showOtherSolutions}
								<ChevronDownIcon class="h-4 w-4" />
							{:else}
								<ChevronRightIcon class="h-4 w-4" />
							{/if}
						</Button>
					{/if}
				</Table.Cell>
				<Table.Cell class="italic">
					<div>
						<span>Your personal solution</span>
					</div>
				</Table.Cell>
				<Table.Cell></Table.Cell>
				{#each problem.objectives as objective}
					<Table.Cell class="pr-6 text-right">
						{formatNumber(
							previousObjectiveValues[personalResultIndex][objective.symbol],
							displayAccuracy
						)}
					</Table.Cell>
				{/each}
			</Table.Row>
		{/if}

		<!-- Other Solutions -->
		{#if showOtherSolutions}
			{#each previousObjectiveValues as previousObjectiveValue, index}
				{#if index !== personalResultIndex}
					<Table.Row class="pointer-events-none">
						<Table.Cell class="border-l-10 border-teal-400 pl-6"></Table.Cell>
						<Table.Cell class="italic">
							<div>
								<span class="text-gray-500">Another user's solution</span>
							</div>
						</Table.Cell>
						<Table.Cell></Table.Cell>
						{#each problem.objectives as objective}
							<Table.Cell class="pr-6 text-right text-gray-500">
								{formatNumber(previousObjectiveValue[objective.symbol], displayAccuracy)}
							</Table.Cell>
						{/each}
					</Table.Row>
				{/if}
			{/each}
		{/if}
	{/if}
{/if}
