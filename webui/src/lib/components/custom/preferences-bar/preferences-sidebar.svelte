<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import PreferenceSwitcher from './preference-switcher.svelte';
	import { writable, type Writable } from 'svelte/store';
	import { Button } from '$lib/components/ui/button/index.js';
	import type { components } from '$lib/api/client-types';
	import {
		HorizontalBar,
		HorizontalBarRanges
	} from '$lib/components/visualizations/horizontal-bar';
	import { Input } from '$lib/components/ui/input/index.js';
	import ValidatedTextbox from '../validated-textbox/validated-textbox.svelte';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors.js';
	type ProblemInfo = components['schemas']['ProblemInfo'];

		interface Props {
		preference_types: string[];
		problem: ProblemInfo;
		onChange?: (event: { value: string; preference?: number[]; numSolutions?: number }) => void;
		onIterate?: (selectedPreference: Writable<string>, referencePointValues: Writable<number[]>) => void;
		onFinish?: (referencePointValues?: Writable<number[]>) => void;
		showNumSolutions?: boolean;
		ref?: HTMLElement | null;
		referencePointValues?: Writable<number[]>;
		handleReferencePointChange?: (idx: number, newValue: number) => void;
		isIterationAllowed?: boolean;
		isFinishAllowed?: boolean;
		currentObjectives?: Record<string, number>;
		preference?: number[];
		numSolutions?: number;
		minNumSolutions?: number;
		maxNumSolutions?: number;
		lastIteratedPreference?: number[];
	}

	let {
		preference_types,
		problem,
		onChange,
		onIterate,
		onFinish,
		showNumSolutions = false,
		ref = null,
		referencePointValues = writable(problem.objectives.map((obj: any) => obj.ideal)), // default if not provided
		handleReferencePointChange = (idx: number, newValue: number) => {}, // default noop
		isIterationAllowed = true,
		isFinishAllowed = true,
		currentObjectives = undefined,
		preference = undefined,
		numSolutions = 1,
		minNumSolutions = 1,
		maxNumSolutions = 4,
		lastIteratedPreference = []
	}: Props = $props();


	// Store for the currently selected preference type
	const selectedPreference = writable(preference_types[0]);
	console.log('Problem in preferences sidebar:', problem);

	// preferences and numSolutions come as props, 
	// but these states keep them in sync in both input and slider,
	// so that onChange-function has the latest preference and numSolutions
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

    // Create a derived classification array for nimbus classification
	// copied almost straight from old nimbus
    let classificationValues = $derived(
		$selectedPreference === 'Classification' 
			? problem.objectives.map((objective, idx:number) => {
				if (objective.ideal == null || objective.nadir == null) {
					return classification.ChangeFreely;
				}
				
				const selectedValue = internalPreference[idx];
				const solutionValue = currentObjectives ? currentObjectives[objective.symbol] : undefined;
				const precision = 0.001; // Adjust as needed

                if (selectedValue === undefined || solutionValue === undefined) {
                    return classification.ChangeFreely;
                }

                // Check if we're at the bounds
                if (Math.abs(selectedValue - objective.ideal) < precision) {
                    return classification.ImproveFreely; // At ideal value
                } else if (Math.abs(selectedValue - objective.nadir) < precision) {
                    return classification.ChangeFreely; // At nadir (worst) value
                } else if (Math.abs(selectedValue - solutionValue) < precision) {
                    return classification.KeepConstant; // Same as current solution
                }

                // Determine if selectedValue is better or worse than solutionValue
                // based on the objective's optimization direction
                const isSelectedBetter = objective.maximize 
                    ? selectedValue > solutionValue  // For maximization: higher is better
                    : selectedValue < solutionValue; // For minimization: lower is better

                return isSelectedBetter 
                    ? classification.ImproveUntil 
                    : classification.WorsenUntil;
            })
            : []
    );

	function handleReferencePointChangeInternal(idx: number, newValue: number) {
		referencePointValues.update((values) => {
			const updated = [...values];
			updated[idx] = newValue;
			return updated;
		});
		onChange?.({ value: String(newValue) });
	}
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
		<p class="mb-2 text-sm text-gray-500">Provide the maximum number of solutions to generate</p>
			<Input 
				type="number" 
				placeholder="Number of solutions" 
				class="mb-2 w-full" 
				bind:value={internalNumSolutions} 
				oninput={(e: Event & { currentTarget: HTMLInputElement }) => {
					const numValue = Number(e.currentTarget.value);
					// Clamp value within allowed range
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
					{@const currentValue = currentObjectives ? currentObjectives[objective.symbol] : objective.ideal}
		
					<div class="flex items-center justify-between mb-2">
						<div>
							<!-- Objective name with unit and optimization direction -->
							<div class="text-sm font-medium mb-1">
								{objective.name}
								{#if objective.unit}({objective.unit}){/if}
								<span class="text-gray-500">({objective.maximize ? "max" : "min"})</span>
							</div>
							<div class="text-xs text-gray-500"> Previous preference: {lastIteratedPreference && lastIteratedPreference[idx] !== undefined ? lastIteratedPreference[idx] : "-"}</div>
							<!-- Current NIMBUS classification label -->
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
									// Clamp value within allowed range
									const clampedValue = Math.max(minValue, Math.min(maxValue, numValue));
									
									if (numValue !== clampedValue) {
										internalPreference[idx] = clampedValue;
									}
									onChange?.({ 
										value: e.currentTarget.value,
										preference: [...internalPreference],
										numSolutions: internalNumSolutions
									});
								}}
							/>
						</div>
						<HorizontalBar
							axisRanges={[objective.ideal, objective.nadir]}
							solutionValue={currentValue}
							selectedValue={internalPreference[idx]}
							barColor="#4f8cff"
							direction="min"
							options={{
								decimalPrecision: 2,
								showPreviousValue: false,
								aspectRatio: 'aspect-[11/2]'
							}}
							onSelect={(newValue: number) => {
								internalPreference[idx] = newValue
								onChange?.({ 
									value: String(newValue),
									preference: [...internalPreference],
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
			{#each problem.objectives as objective, idx}
				{#if objective.ideal != null && objective.nadir != null}
					<div class="mb-4 flex flex-col gap-2">
						<div class="text-sm font-semibold text-gray-700">
							{objective.name} ({objective.maximize ? "max" : "min"})
						</div>
						<div class="flex flex-row">
							<div class="flex w-1/4 flex-col justify-center">
								<span class="text-sm text-gray-500">Value</span>
								<ValidatedTextbox
									placeholder={''}
									min={objective.ideal < objective.nadir ? objective.ideal : objective.nadir}
									max={objective.nadir > objective.ideal ? objective.nadir : objective.ideal}
									value={String($referencePointValues[idx])}
									onChange={(value: String) => {
										const val = Number(value);
										if (!isNaN(val)) handleReferencePointChangeInternal(idx, val);
									}}
								/>
							</div>
							<div class="w-3/4">
								<HorizontalBar
									axisRanges={[
										objective.ideal < objective.nadir ? objective.ideal : objective.nadir,
										objective.nadir > objective.ideal ? objective.nadir : objective.ideal
									]}
									solutionValue={$referencePointValues[idx]}
									selectedValue={$referencePointValues[idx]}
									barColor={COLOR_PALETTE[idx % COLOR_PALETTE.length]}
									direction={objective.maximize ? "max" : "min"}
									options={{
										decimalPrecision: 2,
										showPreviousValue: false,
										aspectRatio: 'aspect-[11/2]'
									}}
									onSelect={(value: number) => {
										handleReferencePointChangeInternal(idx, value);
									}}
								/>
							</div>
						</div>
					</div>
				{:else}
					<div class="text-sm text-red-500">Objective {objective.name} missing ideal/nadir values</div>
				{/if}
			{/each}
		{:else if $selectedPreference === 'Ranges'}
			{#each problem.objectives as objective, idx}
				{#if objective.ideal != null && objective.nadir != null}
					<div class="mb-4 flex flex-col gap-2">
						<div class="text-sm font-semibold text-gray-700">
							{objective.name} ({objective.maximize ? "max" : "min"})
						</div>
						<div class="flex flex-row">
							<div class="flex w-1/4 flex-col justify-center">
								<span class="text-sm text-gray-500">Value</span>
								<ValidatedTextbox
									placeholder={''}
									min={objective.ideal < objective.nadir ? objective.ideal : objective.nadir}
									max={objective.nadir > objective.ideal ? objective.nadir : objective.ideal}
									value={String($referencePointValues[idx])}
									onChange={(value: String) => {
										const val = Number(value);
										if (!isNaN(val)) handleReferencePointChangeInternal(idx, val);
									}}
								/>
							</div>
							<div class="w-3/4">
								<HorizontalBarRanges
									axisRanges={[
										objective.ideal < objective.nadir ? objective.ideal : objective.nadir,
										objective.nadir > objective.ideal ? objective.nadir : objective.ideal
									]}
									lowerBound={$referencePointValues[idx]}
									upperBound={$referencePointValues[idx]}
									barColor={COLOR_PALETTE[idx % COLOR_PALETTE.length]}
									direction={objective.maximize ? "max" : "min"}
									options={{
										decimalPrecision: 2,
										showPreviousValue: false,
										aspectRatio: 'aspect-[11/2]'
									}}
								/>
							</div>
						</div>
					</div>
				{:else}
					<div class="text-sm text-red-500">Objective {objective.name} missing ideal/nadir values</div>
				{/if}
			{/each}
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
	<Sidebar.Footer>
		<div class="items-right flex justify-end gap-2">
			<Button
				variant="default"
				disabled={!isIterationAllowed}
				size="sm"
				onclick={() => {
					selectedPreference.set(preference_types[0]);
					referencePointValues.set(problem.objectives.map((obj: any) => obj.ideal));
					onIterate?.(selectedPreference, referencePointValues);
				}}
			>
				Iterate
			</Button>
			<Button
				variant="secondary"
				size="sm"
				disabled={!isFinishAllowed}
				onclick={() => {
					selectedPreference.set(preference_types[0]);
					referencePointValues.set(problem.objectives.map((obj: any) => obj.ideal));
					onFinish?.(referencePointValues);
				}}
			>
				Finish
			</Button>
		</div>
	</Sidebar.Footer>
	<Sidebar.Rail />
</Sidebar.Root>
