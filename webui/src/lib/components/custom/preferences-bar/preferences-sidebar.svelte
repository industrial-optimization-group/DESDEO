<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import PreferenceSwitcher from './preference-switcher.svelte';
	import { writable } from 'svelte/store';
	import type { components } from '$lib/api/client-types';
	import { HorizontalBar } from '$lib/components/visualizations/horizontal-bar';
	import { Input } from '$lib/components/ui/input/index.js';
	type ProblemInfo = components['schemas']['ProblemInfo'];

		interface Props {
		preference_types: string[];
		problem: ProblemInfo;
		onChange?: (event: { value: string; preference: number[]; numSolutions: number }) => void;
		showNumSolutions?: boolean;
		ref?: HTMLElement | null;
		preference?: number[];
		numSolutions?: number;
		minNumSolutions?: number;
		maxNumSolutions?: number;
	}

	let {
		preference_types,
		problem,
		onChange,
		showNumSolutions = false,
		ref = null,
		preference = undefined,
		numSolutions = 1,
		minNumSolutions = 1,
		maxNumSolutions = 4
	}: Props = $props();


	//let ref: HTMLElement | null = $state(null);
	//let preference_types: string[] = ['Reference point', 'Ranges', 'Preferred solution'];
	//export let problem: ProblemInfo | null = null;

	// Store for the currently selected preference type
	const selectedPreference = writable(preference_types[0]);
	console.log('Problem in preferences sidebar:', problem);

	let internalPreference = $state<number[]>(
		preference && preference.length > 0 
			? [...preference] 
			: []
	);
	
	let internalNumSolutions = $state<number>(numSolutions);

    const classification = {
        ChangeFreely: "Change freely",
        WorsenUntil: "Worsen until",
        KeepConstant: "Keep constant at",
        ImproveUntil: "Improve until",
        ImproveFreely: "Improve freely",
    } as const;

    // Create a derived classification array
    // Todo: Idea copied straight from old nimbus, and there was this comment: 
	// "This only works if lowerIsBetter is false, I think." Is that so? I don't get it.
    let classificationValues = $derived(
		$selectedPreference === 'Classification' 
			? problem.objectives.map((objective, idx:number) => {
				if (objective.ideal == null || objective.nadir == null) {
					return classification.ChangeFreely;
				}
				const selectedValue = internalPreference[idx];
				const solutionValue = objective.ideal;
				const lowerBound = Math.min(objective.ideal, objective.nadir);
				const higherBound = Math.max(objective.ideal, objective.nadir);
				const precision = 0.001; // Adjust as needed

				if (selectedValue === undefined || solutionValue === undefined) {
					return classification.ChangeFreely;
				} else if (
					Math.abs(selectedValue - lowerBound) < precision ||
					selectedValue < lowerBound
				) {
					return classification.ChangeFreely;
				} else if (
					Math.abs(selectedValue - higherBound) < precision ||
					selectedValue > higherBound
				) {
					return classification.ImproveFreely;
				} else if (Math.abs(selectedValue - solutionValue) < precision) {
					return classification.KeepConstant;
				} else if (selectedValue < solutionValue) {
					return classification.WorsenUntil;
				} else if (selectedValue > solutionValue) {
					return classification.ImproveUntil;
				}
				
				return classification.ChangeFreely; // fallback
			})
			: []
    );
</script>

<Sidebar.Root
	{ref}
	collapsible="none"
	class="top-12 flex h-[calc(100vh-6rem)] min-h-[calc(100vh-3rem)] w-[25rem]"
>
	<Sidebar.Header>
		{#if preference_types.length > 1}
			<PreferenceSwitcher
				preferences={preference_types}
				defaultPreference={preference_types[0]}
				onswitch={(e: string) => selectedPreference.set(e)}
			/>
		{:else}
			<Sidebar.MenuButton
				size="lg"
				class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
			>
				<div class="flex flex-col gap-0.5 leading-none">
					<span class="font-semibold">Preference information</span>
					<span class="text-primary-500">{$selectedPreference}</span>
				</div>
			</Sidebar.MenuButton>
		{/if}
	</Sidebar.Header>
	<Sidebar.Content class="h-full px-4">
		{#if showNumSolutions}
			<Input 
				type="number" 
				placeholder="Number of solutions" 
				class="mb-2 w-full" 
				bind:value={internalNumSolutions} 
				oninput={(e: Event & { currentTarget: HTMLInputElement }) => {
					const numValue = Number(e.currentTarget.value);
					const clampedValue = Math.max(minNumSolutions, Math.min(maxNumSolutions, numValue));
					
					if (numValue !== clampedValue) {
						internalNumSolutions = clampedValue;
					}
					onChange?.({ 
						value: e.currentTarget.value,
						preference: [...internalPreference],
						numSolutions: internalNumSolutions 
					});
				}}
			/>
		{/if}
		{#if $selectedPreference === 'Classification'}
			<p class="mb-2 text-sm text-gray-500">Provide one desirable value for each objective.</p>

			{#each problem.objectives as objective, idx}
				{#if objective.ideal != null && objective.nadir != null}
					{@const minValue = Math.min(objective.ideal, objective.nadir)}
					{@const maxValue = Math.max(objective.ideal, objective.nadir)}
		
					<div class="flex items-center justify-between mb-2">
						<div>
							<div class="flex-1">
								<div class="text-sm font-medium">{objective.name} {#if objective.unit}/{objective.unit}{/if} ({objective.maximize ? "max" : "min"})</div>
							</div>
								<label for="input-{idx}" class="text-xs text-gray-500">{classificationValues[idx]}</label>
							<Input
								type="number"
								id="input-{idx}"
								step="0.01"
								min={minValue}
								max={maxValue}
								bind:value={internalPreference[idx]}
								class="w-20 h-8 text-sm"
								oninput={(e: Event & { currentTarget: HTMLInputElement }) => {
									const numValue = Number(e.currentTarget.value);
									const clampedValue = Math.max(minValue, Math.min(maxValue, numValue));
									
									if (numValue !== clampedValue) {
										internalPreference[idx] = clampedValue;
									}
									onChange?.({ 
										value: e.currentTarget.value,
										preference: [...internalPreference], // Send the full array
										numSolutions: internalNumSolutions
									});
								}}
							/>
						</div>
						<HorizontalBar
							axisRanges={[objective.ideal, objective.nadir]}
							solutionValue={objective.ideal}
							selectedValue={internalPreference[idx]}
							barColor="#4f8cff"
							direction="min"
							options={{
								barHeight: 32,
								decimalPrecision: 2,
								showPreviousValue: false,
								aspectRatio: 'aspect-[11/2]'
							}}
							onSelect={(newValue: number) => {
								internalPreference[idx] = newValue
								console.log('Selected value:', newValue);
								onChange?.({ 
									value: String(newValue),
									preference: [...internalPreference], // Send the full array
									numSolutions: internalNumSolutions
								});
							}}
						/>
					</div>
				{:else}
					<div class="text-sm text-red-500">Objective {objective.name} missing ideal/nadir values</div>
				{/if}
			{/each}
		{:else if $selectedPreference === 'Reference point'}
			<p class="mb-2 text-sm text-gray-500">
				Provide a range for each objective, indicating the minimum and maximum acceptable values.
			</p>
		{:else if $selectedPreference === 'Ranges'}
			<p class="mb-2 text-sm text-gray-500">
				Provide a range for each objective, indicating the minimum and maximum acceptable values.
			</p>
			<!-- 			{#each objectives as item}
				<div class="mb-1">
					<span>{item.name} (Min: {item.ideal}, Max: {item.nadir})</span>
				</div>
			{/each} -->
		{:else if $selectedPreference === 'Preferred solution'}
			<p class="mb-2 text-sm text-gray-500">Select one or multiple preferred solutions.</p>
			<!-- 			{#each objectives as item}
				<div class="mb-1">
					<span>{item.name}</span>
				</div>
			{/each} -->
		{:else}
			<p>Select a preference type to view options.</p>
		{/if}
	</Sidebar.Content>
	<Sidebar.Rail />
</Sidebar.Root>
