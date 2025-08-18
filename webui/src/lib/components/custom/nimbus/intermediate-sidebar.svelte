<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import type { components } from '$lib/api/client-types';
	import { Input } from '$lib/components/ui/input/index.js';
	type Solution = components['schemas']['UserSavedSolutionAddress'];

		interface Props {
		onChange?: (event: { value: string}) => void;
		ref?: HTMLElement | null;
		currentSolutions: Solution[];
		numSolutions?: number;
		minNumSolutions?: number;
		maxNumSolutions?: number;
        onClick: () => void;
	}

	let {
		onChange,
		ref = null,
		currentSolutions,
		numSolutions = $bindable(1),
		minNumSolutions = 1,
		maxNumSolutions = 4,
        onClick,
	}: Props = $props();
</script>

<Sidebar.Root
	{ref}
	collapsible="none"
	class="top-12 flex h-[calc(100vh-6rem)] min-h-[calc(100vh-3rem)] w-[25rem]"
>
	<Sidebar.Header>
			<Sidebar.MenuButton
				size="lg"
				class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
			>
				<div class="flex flex-col gap-0.5 leading-none">
					<span class="font-semibold">
							Find Intermediate Solutions
					</span>
				</div>
			</Sidebar.MenuButton>
	</Sidebar.Header>
	<Sidebar.Content class="h-full px-4">
		<p class="mb-2 text-sm text-gray-500">Provide the maximum number of solutions to generate</p>
			<Input 
				type="number" 
				placeholder="Number of solutions" 
				class="mb-2 w-full" 
				bind:value={numSolutions} 
				oninput={(e: Event & { currentTarget: HTMLInputElement }) => {
					const numValue = Number(e.currentTarget.value);
					// Clamp value within allowed range
					const clampedValue = Math.max(minNumSolutions, Math.min(maxNumSolutions, numValue));
					
					if (numValue !== clampedValue) {
						numSolutions = clampedValue;
					}
					onChange?.({ 
						value: e.currentTarget.value,
					});
				}}
			/>
			<p class="mb-2 text-sm text-gray-500">Select two solutions from table or graph.</p>
			<!-- Display each selected solution for intermediate mode -->
			{#if currentSolutions.length > 0}
				{#each currentSolutions as solution}
					<div class="mb-4 border-b pb-3">
							{#if solution.name}
                                <div class="font-medium text-primary">{solution.name}</div>
                            {:else}
                                <div class="font-medium text-primary">Solution {solution.address_result + 1} ({solution.address_state})</div>
                            {/if}
					</div>
				{/each}
				
				{#if currentSolutions.length < 2}
					<div class="text-amber-500">Select one more solution to find intermediate solutions.</div>
				{/if}
			{:else}
				<div class="text-muted-foreground italic">No solutions selected</div>
			{/if}
	</Sidebar.Content>
	<Sidebar.Footer>
		<div class="items-right flex justify-end gap-2">
			<Button
				variant="default"
				size="sm"
				disabled={currentSolutions.length < 2}
				onclick={onClick}
			>
				Solve intermediate
			</Button>
		</div>
	</Sidebar.Footer>
	<Sidebar.Rail />
</Sidebar.Root>
