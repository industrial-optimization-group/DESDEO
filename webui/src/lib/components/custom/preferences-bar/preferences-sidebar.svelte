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
	import {
		calculateClassification,
		type PreferenceValue,
		formatNumber
	} from '$lib/helpers/index.js';
	import { PREFERENCE_TYPES, SIGNIFICANT_DIGITS } from '$lib/constants/index.js';

	type ProblemInfo = components['schemas']['ProblemInfo'];

	interface Props {
		preference_types: PreferenceValue[];
		problem: ProblemInfo;
		num_solutions: number;
		type_preferences: PreferenceValue;
		preference_values: number[];
		objective_values: number[];
		onPreferenceChange?: (data: {
			num_solutions: number;
			type_preferences: PreferenceValue;
			preference_values: number[];
			objective_values: number[];
		}) => void;
		onIterate?: (data: {
			num_solutions: number;
			type_preferences: PreferenceValue;
			preference_values: number[];
			objective_values: number[];
		}) => void;
		onFinish?: (data: {
			num_solutions: number;
			type_preferences: PreferenceValue;
			preference_values: number[];
			objective_values: number[];
		}) => void;
		showNumSolutions?: boolean;
		ref?: HTMLElement | null;
		isIterationAllowed?: boolean;
		isFinishAllowed?: boolean;
		minNumSolutions?: number;
		maxNumSolutions?: number;
		lastIteratedPreference?: number[];
	}

	let {
		preference_types,
		problem,
		num_solutions,
		type_preferences,
		preference_values,
		objective_values,
		onPreferenceChange,
		onIterate,
		onFinish,
		showNumSolutions = false,
		ref = null,
		isIterationAllowed = true,
		isFinishAllowed = true,
		minNumSolutions = 1,
		maxNumSolutions = 4,
		lastIteratedPreference = []
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

	// Internal state that syncs with props
	let internalNumSolutions = $state(num_solutions);
	let internalTypePreferences = $state(type_preferences);
	let internalPreferenceValues = $state([...preference_values]);
	let internalObjectiveValues = $state([...objective_values]);

	// Sync internal state with props when they change
	$effect(() => {
		internalNumSolutions = num_solutions;
	});

	$effect(() => {
		internalTypePreferences = type_preferences;
	});

	$effect(() => {
		internalPreferenceValues = [...preference_values];
	});

	$effect(() => {
		internalObjectiveValues = [...objective_values];
	});

	// Classification values for display
	let classificationValues = $derived(
		internalTypePreferences === PREFERENCE_TYPES.Classification
			? problem.objectives.map((objective, idx: number) =>
					calculateClassification(objective, internalPreferenceValues[idx], 0.001)
				)
			: []
	);

	function notifyChange() {
		onPreferenceChange?.({
			num_solutions: internalNumSolutions,
			type_preferences: internalTypePreferences,
			preference_values: [...internalPreferenceValues],
			objective_values: [...internalObjectiveValues]
		});
	}

	function handleNumSolutionsChange(value: number) {
		internalNumSolutions = value;
		notifyChange();
	}

	function handleTypePreferencesChange(type: PreferenceValue) {
		internalTypePreferences = type;
		notifyChange();
	}

	function handlePreferenceValueChange(idx: number, value: number) {
		internalPreferenceValues[idx] = value;
		notifyChange();
	}

	function handleObjectiveValueChange(idx: number, value: number) {
		internalObjectiveValues[idx] = value;
		notifyChange();
	}

	function handleIterate() {
		onIterate?.({
			num_solutions: internalNumSolutions,
			type_preferences: internalTypePreferences,
			preference_values: [...internalPreferenceValues],
			objective_values: [...internalObjectiveValues]
		});
	}

	function handleFinish() {
		onFinish?.({
			num_solutions: internalNumSolutions,
			type_preferences: internalTypePreferences,
			preference_values: [...internalPreferenceValues],
			objective_values: [...internalObjectiveValues]
		});
	}

	// Add a helper function to safely get preference values
	function getPreferenceValue(idx: number): number {
		return internalPreferenceValues[idx] ?? 0;
	}

	function getObjectiveValue(idx: number): number {
		return internalObjectiveValues[idx] ?? 0;
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
				defaultPreference={internalTypePreferences}
				onswitch={handleTypePreferencesChange}
			/>
		{:else}
			<Sidebar.MenuButton
				size="lg"
				class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
			>
				<div class="flex flex-col gap-0.5 leading-none">
					<span class="font-semibold">Preference information</span>
					<span class="text-primary-500">{internalTypePreferences}</span>
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
				value={internalNumSolutions}
				min={minNumSolutions}
				max={maxNumSolutions}
				oninput={(e) => {
					const target = e.currentTarget;
					if (target instanceof HTMLInputElement) {
						const numValue = Number(target.value);
						const clampedValue = Math.max(minNumSolutions, Math.min(maxNumSolutions, numValue));
						handleNumSolutionsChange(clampedValue);
					}
				}}
			/>
		{/if}

		{#if internalTypePreferences === PREFERENCE_TYPES.Classification}
			<p class="mb-2 text-sm text-gray-500">Provide one desirable value for each objective.</p>

			{#each problem.objectives as objective, idx}
				{#if objective.ideal != null && objective.nadir != null}
					<div class="mb-4 flex flex-col gap-2">
						<div class="text-sm font-semibold text-gray-700">
							{objective.name}
							{#if objective.unit}({objective.unit}){/if}
							({objective.maximize ? 'max' : 'min'})
						</div>
						<!-- 							<div class="text-xs text-gray-500">
								Previous preference: {lastIteratedPreference &&
								lastIteratedPreference[idx] !== undefined
									? lastIteratedPreference[idx]
									: '-'}
							</div> -->

						<div class="flex flex-row">
							<div class="flex w-1/4 flex-col justify-center">
								<span class="text-sm text-gray-500">{classificationValues[idx]}</span>
								<ValidatedTextbox
									placeholder=""
									min={Math.min(objective.ideal, objective.nadir)}
									max={Math.max(objective.ideal, objective.nadir)}
									value={String(formatNumber(getPreferenceValue(idx), SIGNIFICANT_DIGITS))}
									onChange={(value) => {
										const val = Number(value);
										if (!isNaN(val)) handlePreferenceValueChange(idx, val);
									}}
								/>
							</div>
							<div class="w-3/4">
								<HorizontalBar
									axisRanges={[
										Math.min(objective.ideal, objective.nadir),
										Math.max(objective.ideal, objective.nadir)
									]}
									solutionValue={getObjectiveValue(idx) || objective.ideal}
									selectedValue={getPreferenceValue(idx)}
									barColor={COLOR_PALETTE[idx % COLOR_PALETTE.length]}
									direction={objective.maximize ? 'max' : 'min'}
									previousValue={lastIteratedPreference[idx] ?? undefined}
									options={{
										decimalPrecision: SIGNIFICANT_DIGITS,
										showPreviousValue: true,
										aspectRatio: 'aspect-[11/2]'
									}}
									onSelect={(newValue) => handlePreferenceValueChange(idx, newValue)}
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
		{:else if internalTypePreferences === PREFERENCE_TYPES.ReferencePoint}
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
									placeholder=""
									min={Math.min(objective.ideal, objective.nadir)}
									max={Math.max(objective.ideal, objective.nadir)}
									value={String(formatNumber(getPreferenceValue(idx), SIGNIFICANT_DIGITS))}
									onChange={(value) => {
										const val = Number(value);
										if (!isNaN(val)) handlePreferenceValueChange(idx, val);
									}}
								/>
							</div>
							<div class="w-3/4">
								<HorizontalBar
									axisRanges={[
										Math.min(objective.ideal, objective.nadir),
										Math.max(objective.ideal, objective.nadir)
									]}
									solutionValue={getObjectiveValue(idx) || objective.ideal}
									selectedValue={getPreferenceValue(idx)}
									barColor={COLOR_PALETTE[idx % COLOR_PALETTE.length]}
									direction={objective.maximize ? 'max' : 'min'}
									options={{
										decimalPrecision: 2,
										showPreviousValue: false,
										aspectRatio: 'aspect-[11/2]'
									}}
									onSelect={(value) => handlePreferenceValueChange(idx, value)}
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
		{:else if internalTypePreferences === PREFERENCE_TYPES.PreferredRange}
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
									placeholder=""
									min={Math.min(objective.ideal, objective.nadir)}
									max={Math.max(objective.ideal, objective.nadir)}
									value={String(formatNumber(getPreferenceValue(idx), SIGNIFICANT_DIGITS))}
									onChange={(value) => {
										const val = Number(value);
										if (!isNaN(val)) handlePreferenceValueChange(idx, val);
									}}
								/>
							</div>
							<div class="w-3/4">
								<HorizontalBarRanges
									axisRanges={[
										Math.min(objective.ideal, objective.nadir),
										Math.max(objective.ideal, objective.nadir)
									]}
									lowerBound={getPreferenceValue(idx)}
									upperBound={getPreferenceValue(idx)}
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
		{:else if internalTypePreferences === PREFERENCE_TYPES.PreferredSolution}
			<p class="mb-2 text-sm text-gray-500">Select one or multiple preferred solutions.</p>
		{:else}
			<p>Select a preference type to view options.</p>
		{/if}
	</Sidebar.Content>

	<Sidebar.Footer>
		<div class="items-right flex justify-end gap-2">
			<Button variant="default" disabled={!isIterationAllowed} size="sm" onclick={handleIterate}>
				Iterate
			</Button>
			<Button variant="secondary" size="sm" disabled={!isFinishAllowed} onclick={handleFinish}>
				Finish
			</Button>
		</div>
	</Sidebar.Footer>
	<Sidebar.Rail />
</Sidebar.Root>
