<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import PreferenceSwitcher from './preference-switcher.svelte';
	import { writable, type Writable } from 'svelte/store';
	import InfoIcon from '@lucide/svelte/icons/info';
	import Circle from '@lucide/svelte/icons/circle';
	import Triangle from '@lucide/svelte/icons/triangle';

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
	import { Tooltip } from 'bits-ui';
	import * as Popover from '$lib/components/ui/popover/index.js';

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
		showPreviousPreference?: boolean;
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
		showPreviousPreference = false,
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
		const list = getDisplayAccuracy(problem);
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
	class="top-12 flex h-[calc(100vh-6rem)] min-h-[calc(100vh-3rem)] w-full"
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
				<div
					class="w-full gap-0.5 leading-none"
					style="display: flex; flex-direction: row; align-items: center; justify-content: space-between;"
				>
					<div class="flex flex-col">
						<div class="font-semibold">Preference information</div>
						<div class="text-primary-500">{internal_type_preferences}</div>
					</div>
					<!-- 					<div class="flex justify-center">
						<Tooltip.Root>
							<Tooltip.Trigger><InfoIcon class="h-5 w-5" /></Tooltip.Trigger>
							<Tooltip.Content side="right" class="tooltip-content">
								{#if internal_type_preferences === PREFERENCE_TYPES.Classification}
									<p class="leading-relaxed">
										Use the classification to indicate how you want each objective function to
										change in the next iteration, based on the current solution.
									</p>
								{:else if internal_type_preferences === PREFERENCE_TYPES.ReferencePoint}
									<p class="leading-relaxed">
										The <span class="font-semibold">Reference Point</span> preference type lets you specify
										a reference point in the objective space. Solutions will be evaluated based on their
										distance from this reference point, helping you identify those that are closest to
										your ideal outcomes.
									</p>
								{:else if internal_type_preferences === PREFERENCE_TYPES.PreferredRange}
									<p class="leading-relaxed">
										The <span class="font-semibold">Preferred Range</span> preference type enables you
										to define a preferred range for each objective. Solutions will be assessed based
										on whether they fall within these ranges, allowing you to focus on those that meet
										your specific criteria.
									</p>
								{:else if internal_type_preferences === PREFERENCE_TYPES.PreferredSolution}
									<p class="leading-relaxed">
										The <span class="font-semibold">Preferred Solution</span> preference type allows
										you to select one or more preferred solutions. The system will then analyze how other
										solutions compare to your selected preferences, helping you understand trade-offs
										and make informed decisions.
									</p>
								{:else}
									<p>Select a preference type to view more information.</p>
								{/if}
							</Tooltip.Content>
						</Tooltip.Root>
					</div> -->
				</div>
			</Sidebar.MenuButton>
		{/if}
	</Sidebar.Header>

	<Sidebar.Content class="h-full w-full px-4">
		{#if internal_type_preferences === PREFERENCE_TYPES.Classification}
			<span class="mb-1 cursor-pointer text-sm text-gray-700"
				>Drag the sliders to define how each objective function should change. Colored areas
				indicate the current value.</span
			>
			<Popover.Root>
				<Popover.Trigger
					class="flex items-center gap-1 text-sm text-gray-400 transition-colors hover:text-gray-700"
				>
					<InfoIcon class="h-3 w-3" />
					<span>How do these sliders work?</span>
				</Popover.Trigger>

				<Popover.Content class="w-72 text-sm">
					<div class="space-y-2">
						<p class="font-medium">How these sliders work</p>
						<ul class="text-muted-foreground space-y-2 text-sm">
							<li class="flex items-center gap-2">
								<Triangle class="h-4 w-4 -rotate-90 text-gray-400" />
								<span><b>Minimum value</b> — set preference to the lowest achievable value</span>
							</li>

							<li class="flex items-center gap-2">
								<Triangle class="h-4 w-4 rotate-90 text-gray-400" />
								<span><b>Maximum value</b> — set preference to the highest achievable value</span>
							</li>

							<li class="flex items-center gap-2">
								<span class="h-3 w-6 rounded-sm bg-gradient-to-r from-gray-300 to-gray-400"></span>
								<span><b>Colored bar</b> — current objective value</span>
							</li>

							<li class="flex items-center gap-2">
								<Circle class="h-4 w-4 fill-white text-black" />
								<span><b>Preference value</b> — drag to adjust classification values</span>
							</li>

							<li class="flex items-center gap-2">
								<Triangle class="h-4 w-4 rotate-180 fill-black text-black" />
								<span><b>Match current value</b> — align preference with bar value</span>
							</li>
							<li class="flex items-center gap-2">
								<Circle class="h-4 w-4 fill-gray-600 text-black" />
								<span
									><b>Match previous preference</b> — align preference with previous iteration value</span
								>
							</li>
						</ul>
					</div>
				</Popover.Content>
			</Popover.Root>
			{#each problem.objectives as objective, idx}
				{#if objective.ideal != null && objective.nadir != null}
					<div class="mb-4 flex flex-col gap-2">
						<div class="text-sm font-semibold text-gray-700" title={getObjectiveTitle(objective)}>
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
										showPreviousValue: showPreviousPreference,
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
										showPreviousValue: showPreviousPreference,
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
										showPreviousValue: showPreviousPreference,
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
	</Sidebar.Content>

	<Sidebar.Footer>
		<div class="items-right flex justify-end gap-2">
			<Tooltip.Root>
				<Tooltip.Trigger>
					<Button
						variant="default"
						disabled={!isIterationAllowed}
						size="sm"
						onclick={handle_iterate}
					>
						Iterate
					</Button>
				</Tooltip.Trigger>
				<Tooltip.Content side="top" class="tooltip-content">
					{#if isIterationAllowed}
						<p>Click "Iterate" to generate new solutions based on your preferences.</p>
					{:else}
						<p>
							Please adjust your preferences to continue for the next iteration. Tip: To improve one
							objective function, at least one other must be allowed to be impaired.
						</p>
					{/if}
				</Tooltip.Content>
			</Tooltip.Root>

			{#if isFinishButton}
				<Button variant="secondary" size="sm" disabled={!isFinishAllowed} onclick={handle_finish}>
					Finish
				</Button>
			{/if}
		</div>
	</Sidebar.Footer>
	<Sidebar.Rail />
</Sidebar.Root>
