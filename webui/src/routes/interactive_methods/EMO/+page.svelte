<script lang="ts">
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import AdvancedSidebar from '$lib/components/custom/preferences-bar/advanced-sidebar.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import * as Menubar from '$lib/components/ui/menubar/index.js';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import type { components } from '$lib/api/client-types';
	import { onMount } from 'svelte';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { Combobox } from '$lib/components/ui/combobox';
	import { PREFERENCE_TYPES } from '$lib/constants';

	type ProblemInfo = components['schemas']['ProblemInfo'];
	type PreferenceValue = (typeof PREFERENCE_TYPES)[keyof typeof PREFERENCE_TYPES];

	interface Preference {
		type: PreferenceValue;
		values: number[];
	}

	let problem: ProblemInfo | null = $state(null);

	const { data } = $props<{ data: ProblemInfo[] }>();

	let problemList = data.problems ?? [];
	let selectedTypeSolutions = $state('current');

	// State with the required properties
	let num_solutions = $state(1);
	let objective_values = $state<number[]>([]);

	// Preference objects with type and values
	let previous_preference = $state<Preference>({
		type: PREFERENCE_TYPES.ReferencePoint,
		values: []
	});

	let current_preference = $state<Preference>({
		type: PREFERENCE_TYPES.ReferencePoint,
		values: []
	});

	const type_solutions_to_visualize = [
		{ value: 'current', label: 'Current solutions' },
		{ value: 'best', label: 'Best solutions' },
		{ value: 'all', label: 'All solutions' }
	];

	function handleChange(event: { value: string }) {
		selectedTypeSolutions = event.value;
		console.log('Selected type of solutions:', selectedTypeSolutions);
	}

	function handlePreferenceChange(data: {
		num_solutions: number;
		type_preferences: PreferenceValue;
		preference_values: number[];
		objective_values: number[];
	}) {
		// Update all properties when user changes preferences
		num_solutions = data.num_solutions;
		objective_values = [...data.objective_values];

		// Update current preference
		current_preference = {
			type: data.type_preferences,
			values: [...data.preference_values]
		};

		console.log('Preference changed:', {
			num_solutions,
			current_preference,
			previous_preference,
			objective_values
		});
	}

	function handleIterate(data: {
		num_solutions: number;
		type_preferences: PreferenceValue;
		preference_values: number[];
		objective_values: number[];
	}) {
		console.log('Iterate clicked with data:', data);

		// Store current preference as previous before updating
		previous_preference = {
			type: current_preference.type,
			values: [...current_preference.values]
		};

		// num_solutions and preference type stay the same
		// Update objective_values and preference_values from your optimization procedure
		updateFromOptimizationProcedure(data);
	}

	function updateFromOptimizationProcedure(data: {
		num_solutions: number;
		type_preferences: PreferenceValue;
		preference_values: number[];
		objective_values: number[];
	}) {
		// This is where you would call your actual optimization backend
		// For now, we'll simulate updating the values

		// Keep num_solutions and preference type the same
		// Update preference_values and objective_values based on optimization results

		// Simulate new values from optimization
		const simulatedNewObjectiveValues = objective_values.map(
			(val) => val + Math.random() * 0.1 - 0.05
		);
		const simulatedNewPreferenceValues = current_preference.values.map(
			(val) => val + Math.random() * 0.1 - 0.05
		);

		// Update the state with new values
		objective_values = simulatedNewObjectiveValues;
		current_preference = {
			type: current_preference.type, // Keep the same type
			values: simulatedNewPreferenceValues
		};

		console.log('Updated from optimization:', {
			num_solutions, // unchanged
			previous_preference, // previous iteration values
			current_preference, // updated values
			objective_values // updated
		});
	}

	function handleFinish(data: {
		num_solutions: number;
		type_preferences: PreferenceValue;
		preference_values: number[];
		objective_values: number[];
	}) {
		console.log('Finish clicked with data:', data);

		// Store final result as previous preference
		previous_preference = {
			type: current_preference.type,
			values: [...current_preference.values]
		};

		// Handle finishing the optimization process
		console.log('Final preferences:', {
			previous_preference,
			current_preference,
			objective_values
		});
	}

	// Initialize values when problem is loaded
	$effect(() => {
		if (problem) {
			// Initialize preference_values and objective_values based on problem
			const defaultValues = problem.objectives.map((obj) =>
				typeof obj.ideal === 'number' ? obj.ideal : 0
			);

			objective_values = [...defaultValues];

			// Initialize both current and previous preferences
			current_preference = {
				type: PREFERENCE_TYPES.ReferencePoint,
				values: [...defaultValues]
			};

			previous_preference = {
				type: PREFERENCE_TYPES.ReferencePoint,
				values: [...defaultValues]
			};
		}
	});

	onMount(() => {
		if ($methodSelection.selectedProblemId) {
			problem = problemList.find(
				(p: ProblemInfo) => String(p.id) === String($methodSelection.selectedProblemId)
			);
		}
	});
</script>

<div class="flex min-h-[calc(100vh-3rem)]">
	{#if problem}
		<AppSidebar
			{problem}
			preference_types={[
				PREFERENCE_TYPES.ReferencePoint,
				PREFERENCE_TYPES.PreferredRange,
				PREFERENCE_TYPES.PreferredSolution
			]}
			{num_solutions}
			type_preferences={current_preference.type}
			preference_values={current_preference.values}
			{objective_values}
			showNumSolutions={true}
			onPreferenceChange={handlePreferenceChange}
			onIterate={handleIterate}
			onFinish={handleFinish}
		/>
	{/if}

	<div class="flex-1">
		<Resizable.PaneGroup direction="vertical">
			<Resizable.Pane class="p-2">
				<div class="flex-row">
					<div class="flex flex-row items-center justify-between gap-4 pb-2">
						<div class="font-semibold">Solution explorer</div>
						<div>
							<span>View: </span>
							<Combobox
								options={type_solutions_to_visualize}
								defaultSelected={selectedTypeSolutions}
								onChange={handleChange}
							/>
						</div>
					</div>

					<div class="h-full w-full">
						<div class="grid h-full w-full gap-4 xl:grid-cols-1">
							<div class="min-h-[50rem] flex-1 rounded bg-gray-100 p-4">
								<span>Objective space</span>
							</div>
						</div>
					</div>
				</div>
			</Resizable.Pane>
			<Resizable.Handle />
			<Resizable.Pane class="p-2">
				<Tabs.Root value="numerical-values">
					<Tabs.List>
						<Tabs.Trigger value="numerical-values">Numerical values</Tabs.Trigger>
						<Tabs.Trigger value="saved-solutions">Saved solutions</Tabs.Trigger>
					</Tabs.List>
					<Tabs.Content value="numerical-values">
						<div class="space-y-4">
							<div>Table of solutions</div>

							<!-- Show comparison between current and previous preferences -->
							<div class="grid grid-cols-2 gap-4">
								<div class="rounded border p-3">
									<h4 class="font-semibold">Current Preference</h4>
									<p class="text-sm text-gray-600">Type: {current_preference.type}</p>
									<p class="text-sm text-gray-600">
										Values: {current_preference.values.map((v) => v.toFixed(3)).join(', ')}
									</p>
								</div>
								<div class="rounded border p-3">
									<h4 class="font-semibold">Previous Preference</h4>
									<p class="text-sm text-gray-600">Type: {previous_preference.type}</p>
									<p class="text-sm text-gray-600">
										Values: {previous_preference.values.map((v) => v.toFixed(3)).join(', ')}
									</p>
								</div>
							</div>
						</div>
					</Tabs.Content>
					<Tabs.Content value="saved-solutions">Visualize saved solutions</Tabs.Content>
				</Tabs.Root>
			</Resizable.Pane>
		</Resizable.PaneGroup>
	</div>

	<AdvancedSidebar />
</div>
