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
		formatNumber,
		getDisplayAccuracy
	} from '$lib/helpers/index.js';
	import { PREFERENCE_TYPES } from '$lib/constants/index.js';

	type ProblemInfo = components['schemas']['ProblemInfo'];

	interface Props {
		preferenceTypes: PreferenceValue[];
		problem: ProblemInfo;
		numSolutions: number;
		typePreferences: PreferenceValue;
		preferenceValues: number[];
		objectiveValues: number[];
		onPreferenceChange?: (data: {
			numSolutions: number;
			typePreferences: PreferenceValue;
			preferenceValues: number[];
			objectiveValues: number[];
		}) => void;
		onIterate?: (data: {
			numSolutions: number;
			typePreferences: PreferenceValue;
			preferenceValues: number[];
			objectiveValues: number[];
		}) => void;
		onFinish?: (data: {
			numSolutions: number;
			typePreferences: PreferenceValue;
			preferenceValues: number[];
			objectiveValues: number[];
		}) => void;
		showNumSolutions?: boolean;
		ref?: HTMLElement | null;
		isIterationAllowed?: boolean;
		isCalculating?: boolean;
		isFinishAllowed?: boolean;
		minNumSolutions?: number;
		maxNumSolutions?: number;
		lastIteratedPreference?: number[];
		isFinishButton?: boolean;
	}

	let {
		preferenceTypes,
		problem,
		numSolutions,
		typePreferences,
		preferenceValues,
		objectiveValues,
		onPreferenceChange,
		onIterate,
		onFinish,
		showNumSolutions = false,
		ref = null,
		isIterationAllowed = true,
		isFinishAllowed = true,
		minNumSolutions = 1,
		maxNumSolutions = 4,
		lastIteratedPreference = [],
		isFinishButton = true
	}: Props = $props();

	// Validate that preference_types only contains valid values
	const valid_preference_types = $derived(preferenceTypes.filter((type) =>
		Object.values(PREFERENCE_TYPES).includes(type as PreferenceValue)
	));

	$effect(() => {
		if (valid_preference_types.length !== preferenceTypes.length) {
			console.warn(
				'Invalid preference types detected:',
				preferenceTypes.filter(
					(type) => !Object.values(PREFERENCE_TYPES).includes(type as PreferenceValue)
				)
			);
		}
	});

	// Internal state that syncs with props (initialized via $effect below)
	let internal_num_solutions = $state(0);
	let internal_type_preferences = $state('');
	let internal_preference_values = $state<number[]>([]);
	let internal_objective_values = $state<number[]>([]);

	let displayAccuracy = $derived((idx: number) => {
		const list = getDisplayAccuracy(problem)
		return list[idx];
	});

	// Sync internal state with props when they change
	$effect(() => {
		internal_num_solutions = numSolutions;
	});

	$effect(() => {
		internal_type_preferences = typePreferences;
	});

	$effect(() => {
		internal_preference_values = [...preferenceValues];
	});

	$effect(() => {
		internal_objective_values = [...objectiveValues];
	});

	// Classification values for display
	let classification_values = $derived(
		internal_type_preferences === PREFERENCE_TYPES.Classification
			? problem.objectives.map((objective, idx: number) =>
					calculateClassification(
						objective,
						internal_preference_values[idx],
						internal_objective_values[idx],
						0.001
					)
				)
			: []
	);

	function notify_change() {
		onPreferenceChange?.({
			numSolutions: internal_num_solutions,
			typePreferences: internal_type_preferences,
			preferenceValues: [...internal_preference_values],
			objectiveValues: [...internal_objective_values]
		});
	}

	function handle_num_solutions_change(value: number) {
		internal_num_solutions = value;
		notify_change();
	}

	function handle_type_preferences_change(type: PreferenceValue) {
		internal_type_preferences = type;
		notify_change();
	}

	function handle_preference_value_change(idx: number, value: number) {
		internal_preference_values[idx] = value;
		notify_change();
	}

	function handle_objective_value_change(idx: number, value: number) {
		internal_objective_values[idx] = value;
		notify_change();
	}

	function handle_iterate() {
		onIterate?.({
			numSolutions: internal_num_solutions,
			typePreferences: internal_type_preferences,
			preferenceValues: [...internal_preference_values],
			objectiveValues: [...internal_objective_values]
		});
	}

	function handle_finish() {
		onFinish?.({
			numSolutions: internal_num_solutions,
			typePreferences: internal_type_preferences,
			preferenceValues: [...internal_preference_values],
			objectiveValues: [...internal_objective_values]
		});
	}

	// Add a helper function to safely get preference values
	function get_preference_value(idx: number): number {
		return internal_preference_values[idx] ?? 0;
	}

	function get_objective_value(idx: number): number {
		return internal_objective_values[idx] ?? 0;
	}

	// Helper function to get objective title for display
	function getObjectiveTitle(objective: any): string {
		if (!objective) return '';

		const tooltip = objective.description || objective.name;
		return objective.unit ? `${tooltip} (${objective.unit})` : tooltip;
	}

</script>

<Sidebar.Root
	{ref}
	collapsible="none"
	class="top-12 flex h-[calc(100vh-6rem)] min-h-[calc(100vh-3rem)] w-[25rem]"
>
	<Sidebar.Header>
		{#if valid_preference_types.length > 1}
			<PreferenceSwitcher
				preferences={valid_preference_types}
				defaultPreference={internal_type_preferences}
				onswitch={handle_type_preferences_change}
			/>
		{:else}
			<Sidebar.MenuButton
				size="lg"
				class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
			>
				<div class="flex flex-col gap-0.5 leading-none">
					<span class="font-semibold">Preference information</span>
					<span class="text-primary-500">{internal_type_preferences}</span>
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
				value={internal_num_solutions}
				min={minNumSolutions}
				max={maxNumSolutions}
				oninput={(e) => {
					const target = e.currentTarget;
					if (target instanceof HTMLInputElement) {
						const num_value = Number(target.value);
						const clamped_value = Math.max(minNumSolutions, Math.min(maxNumSolutions, num_value));
						handle_num_solutions_change(clamped_value);
					}
				}}
			/>
		{/if}

		{#if internal_type_preferences === PREFERENCE_TYPES.Classification}
			<p class="mb-2 text-sm text-gray-500">Provide one desirable value for each objective.</p>

			{#each problem.objectives as objective, idx}
				{#if objective.ideal != null && objective.nadir != null}
					<div class="mb-4 flex flex-col gap-2">
						<div
							class="text-sm font-semibold text-gray-700"
							title={getObjectiveTitle(objective)}
						>
							{objective.name} ({objective.maximize ? 'max' : 'min'})
						</div>
						<div class="flex flex-row items-start">
							<div class="flex w-1/4 flex-col">
								<div class="h-12 overflow-y-auto">
									<span class="text-sm text-gray-500">{classification_values[idx]}</span>
								</div>
								<ValidatedTextbox
									placeholder=""
									min={Math.min(objective.ideal, objective.nadir)}
									max={Math.max(objective.ideal, objective.nadir)}
									value={String(formatNumber(get_preference_value(idx), displayAccuracy(idx)))}
									onChange={(value) => {
										const val = Number(value);
										if (!isNaN(val)) handle_preference_value_change(idx, val);
									}}
								/>
							</div>
							<div class="w-3/4">
								<HorizontalBar
									axisRanges={[
										Math.min(objective.ideal, objective.nadir),
										Math.max(objective.ideal, objective.nadir)
									]}
									solutionValue={get_objective_value(idx) || objective.ideal}
									selectedValue={get_preference_value(idx)}
									barColor={COLOR_PALETTE[idx % COLOR_PALETTE.length]}
									direction={objective.maximize ? 'max' : 'min'}
									previousValue={lastIteratedPreference[idx] ?? undefined}
									options={{
										decimalPrecision: displayAccuracy(idx),
										showPreviousValue: true,
										showSelectedValueLabel: false,
										aspectRatio: 'aspect-[11/2]'
									}}
									onSelect={(newValue) => handle_preference_value_change(idx, newValue)}
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
		{:else if internal_type_preferences === PREFERENCE_TYPES.ReferencePoint}
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
									value={String(formatNumber(get_preference_value(idx), displayAccuracy(idx)))}
									onChange={(value) => {
										const val = Number(value);
										if (!isNaN(val)) handle_preference_value_change(idx, val);
									}}
								/>
							</div>
							<div class="w-3/4">
								<HorizontalBar
									axisRanges={[
										Math.min(objective.ideal, objective.nadir),
										Math.max(objective.ideal, objective.nadir)
									]}
									solutionValue={get_objective_value(idx) || objective.ideal}
									selectedValue={get_preference_value(idx)}
									barColor={COLOR_PALETTE[idx % COLOR_PALETTE.length]}
									direction={objective.maximize ? 'max' : 'min'}
									options={{
										decimalPrecision: 2,
										showPreviousValue: false,
										aspectRatio: 'aspect-[11/2]'
									}}
									onSelect={(value) => handle_preference_value_change(idx, value)}
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
		{:else if internal_type_preferences === PREFERENCE_TYPES.PreferredRange}
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
									value={String(formatNumber(get_preference_value(idx), displayAccuracy(idx)))}
									onChange={(value) => {
										const val = Number(value);
										if (!isNaN(val)) handle_preference_value_change(idx, val);
									}}
								/>
							</div>
							<div class="w-3/4">
								<HorizontalBarRanges
									axisRanges={[
										Math.min(objective.ideal, objective.nadir),
										Math.max(objective.ideal, objective.nadir)
									]}
									lowerBound={get_preference_value(idx)}
									upperBound={get_preference_value(idx)}
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
		{:else if internal_type_preferences === PREFERENCE_TYPES.PreferredSolution}
			<p class="mb-2 text-sm text-gray-500">Select one or multiple preferred solutions.</p>
		{:else}
			<p>Select a preference type to view options.</p>
		{/if}
	</Sidebar.Content>

	<Sidebar.Footer>
		<div class="items-right flex justify-end gap-2">
			<Button variant="default" disabled={!isIterationAllowed} size="sm" onclick={handle_iterate}>
				Iterate
			</Button>
			{#if isFinishButton}
				<Button variant="secondary" size="sm" disabled={!isFinishAllowed} onclick={handle_finish}>
					Finish
				</Button>
			{/if}
		</div>
	</Sidebar.Footer>
	<Sidebar.Rail />
</Sidebar.Root>
