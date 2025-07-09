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
	import { calculateClassification, type PreferenceValue } from '$lib/helpers/index.js';
	import { PREFERENCE_TYPES } from '$lib/constants/index.js';

	type ProblemInfo = components['schemas']['ProblemInfo'];

	interface Props {
		preference_types: PreferenceValue[];
		problem: ProblemInfo;
		onChange?: (event: {
			preferenceType: string;
			preference: number[];
			numSolutions: number;
		}) => void;
		onIterate?: (event: {
			preferenceType: PreferenceValue;
			preferenceValue: any;
			numSolutions: number;
		}) => void;
		onFinish?: (event: { value: PreferenceValue }) => void;
		showNumSolutions?: boolean;
		ref?: HTMLElement | null;
		referencePointValues?: Writable<number[]>;
		handleReferencePointChange?: (idx: number, newValue: number) => void;
		preference?: number[];
		numSolutions?: number;
		minNumSolutions?: number;
		maxNumSolutions?: number;
	}

	let {
		preference_types,
		problem,
		onChange,
		onIterate,
		onFinish,
		showNumSolutions = false,
		ref = null,
		referencePointValues = writable(problem.objectives.map((obj: any) => obj.ideal)),
		handleReferencePointChange = (idx: number, newValue: number) => {},
		preference = undefined,
		numSolutions = 1,
		minNumSolutions = 1,
		maxNumSolutions = 4
	}: Props = $props();

	// Validate that preference_types only contains valid values
	const validPreferenceTypes = preference_types.filter((type) =>
		Object.values(PREFERENCE_TYPES).includes(type as PreferenceValue)
	);

	if (validPreferenceTypes.length !== preference_types.length) {
		console.warn(
			'Invalid preference types detected:',
			preference_types.filter(
				(type) => !Object.values(PREFERENCE_TYPES).includes(type as PreferenceValue)
			)
		);
	}

	const selectedPreference = writable<PreferenceValue>(validPreferenceTypes[0]);

	// Internal state for preference type and values
	let internalPreference = $state<number[]>(
		preference && preference.length > 0 ? [...preference] : []
	);
	let internalNumSolutions = $state<number>(numSolutions);

	// Use the constants for comparison
	let classificationValues = $derived(
		$selectedPreference === PREFERENCE_TYPES.Classification
			? problem.objectives.map((objective, idx: number) =>
					calculateClassification(objective, internalPreference[idx], 0.001)
				)
			: []
	);

	function handleReferencePointChangeInternal(idx: number, newValue: number) {
		referencePointValues.update((values) => {
			const updated = [...values];
			updated[idx] = newValue;
			return updated;
		});
		onChange?.({
			preferenceType: $selectedPreference,
			preference: [...internalPreference],
			numSolutions: internalNumSolutions
		});
	}
</script>

<Sidebar.Root
	{ref}
	collapsible="none"
	class="top-12 flex h-[calc(100vh-6rem)] min-h-[calc(100vh-3rem)] w-[25rem]"
>
	<Sidebar.Header>
		{#if validPreferenceTypes.length > 1}
			<PreferenceSwitcher
				preferences={validPreferenceTypes}
				defaultPreference={validPreferenceTypes[0]}
				onswitch={(e: PreferenceValue) => selectedPreference.set(e)}
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
					const clampedValue = Math.max(minNumSolutions, Math.min(maxNumSolutions, numValue));

					if (numValue !== clampedValue) {
						internalNumSolutions = clampedValue;
					}
					onChange?.({
						preferenceType: $selectedPreference,
						preference: [...internalPreference],
						numSolutions: internalNumSolutions
					});
				}}
			/>
		{/if}

		{#if $selectedPreference === PREFERENCE_TYPES.Classification}
			<p class="mb-2 text-sm text-gray-500">Provide one desirable value for each objective.</p>

			{#each problem.objectives as objective, idx}
				{#if objective.ideal != null && objective.nadir != null}
					{@const minValue = Math.min(objective.ideal, objective.nadir)}
					{@const maxValue = Math.max(objective.ideal, objective.nadir)}

					<div class="mb-2 flex items-center justify-between">
						<div>
							<!-- Objective name with unit and optimization direction -->
							<div class="mb-1 text-sm font-medium">
								{objective.name}
								{#if objective.unit}({objective.unit}){/if}
								<span class="text-gray-500">({objective.maximize ? 'max' : 'min'})</span>
							</div>
							<!-- Current NIMBUS classification label -->
							<label for="input-{idx}" class="text-xs text-gray-500"
								>{classificationValues[idx]}</label
							>
							<Input
								type="number"
								id="input-{idx}"
								step="0.01"
								min={minValue}
								max={maxValue}
								bind:value={internalPreference[idx]}
								class="h-8 w-20 text-sm"
								oninput={(e: Event & { currentTarget: HTMLInputElement }) => {
									const numValue = Number(e.currentTarget.value);
									// Clamp value within allowed range
									const clampedValue = Math.max(minValue, Math.min(maxValue, numValue));

									if (numValue !== clampedValue) {
										internalPreference[idx] = clampedValue;
									}
									onChange?.({
										preferenceType: $selectedPreference,
										preference: [...internalPreference],
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
								decimalPrecision: 2,
								showPreviousValue: false,
								aspectRatio: 'aspect-[11/2]'
							}}
							onSelect={(newValue: number) => {
								internalPreference[idx] = newValue;
								onChange?.({
									preferenceType: $selectedPreference,
									preference: [...internalPreference],
									numSolutions: internalNumSolutions
								});
							}}
						/>
					</div>
				{:else}
					<div class="text-sm text-red-500">
						Objective {objective.name} missing ideal/nadir values
					</div>
				{/if}
			{/each}
		{:else if $selectedPreference === PREFERENCE_TYPES.ReferencePoint}
			{#each problem.objectives as objective, idx}
				{#if objective.ideal != null && objective.nadir != null}
					<div class="mb-4 flex flex-col gap-2">
						<div class="text-sm font-semibold text-gray-700">
							{objective.name} ({objective.maximize ? 'max' : 'min'})
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
									direction={objective.maximize ? 'max' : 'min'}
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
					<div class="text-sm text-red-500">
						Objective {objective.name} missing ideal/nadir values
					</div>
				{/if}
			{/each}
		{:else if $selectedPreference === PREFERENCE_TYPES.PreferredRange}
			{#each problem.objectives as objective, idx}
				{#if objective.ideal != null && objective.nadir != null}
					<div class="mb-4 flex flex-col gap-2">
						<div class="text-sm font-semibold text-gray-700">
							{objective.name} ({objective.maximize ? 'max' : 'min'})
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
									direction={objective.maximize ? 'max' : 'min'}
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
					<div class="text-sm text-red-500">
						Objective {objective.name} missing ideal/nadir values
					</div>
				{/if}
			{/each}
		{:else if $selectedPreference === PREFERENCE_TYPES.PreferredSolution}
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
				size="sm"
				onclick={() => {
					selectedPreference.set(validPreferenceTypes[0]);
					referencePointValues.set(problem.objectives.map((obj: any) => obj.ideal));
					onIterate?.({
						preferenceType: $selectedPreference,
						preferenceValue: [...internalPreference],
						numSolutions: internalNumSolutions
					});
				}}
			>
				Iterate
			</Button>
			<Button
				variant="secondary"
				size="sm"
				onclick={() => {
					selectedPreference.set(validPreferenceTypes[0]);
					referencePointValues.set(problem.objectives.map((obj: any) => obj.ideal));
					onFinish?.({
						value: $selectedPreference
					});
				}}
			>
				Finish
			</Button>
		</div>
	</Sidebar.Footer>
	<Sidebar.Rail />
</Sidebar.Root>
