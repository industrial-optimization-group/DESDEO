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
	import { formatNumber, formatNumberArray } from '$lib/helpers';
	import { goto } from '$app/navigation';

	type ProblemInfo = components['schemas']['ProblemInfo'];
	type PreferenceValue = (typeof PREFERENCE_TYPES)[keyof typeof PREFERENCE_TYPES];

	interface Preference {
		type: PreferenceValue;
		values: number[];
	}

	let problem: ProblemInfo | null = $state(null);

	const { data } = $props<{ data: ProblemInfo[] }>();
	console.log('Data received:', data.problems);
	// Fix: data is already the array, not an object with problems property
	let problemList = data.problems ?? [];
	console.log('Data received:', data.problems);

	let selectedTypeSolutions = $state('current');

	// State with the required properties
	let num_solutions = $state(1);
	let objective_values = $state<number[]>([]);

	let emo_method = $state('NSGA3'); // or "RVEA"
	let max_evaluations = $state(1000);
	let use_archive = $state(true);

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
			current_preference: {
				type: current_preference.type,
				values: formatNumberArray(current_preference.values)
			},
			previous_preference: {
				type: previous_preference.type,
				values: formatNumberArray(previous_preference.values)
			},
			objective_values: formatNumberArray(objective_values)
		});
	}

	function handleIterate(data: {
		num_solutions: number;
		type_preferences: PreferenceValue;
		preference_values: number[];
		objective_values: number[];
	}) {
		console.log('Iterate clicked with data:', {
			num_solutions: data.num_solutions,
			type_preferences: data.type_preferences,
			preference_values: formatNumberArray(data.preference_values),
			objective_values: formatNumberArray(data.objective_values)
		});

		// Store current preference as previous before updating
		previous_preference = {
			type: current_preference.type,
			values: [...current_preference.values]
		};

		// num_solutions and preference type stay the same
		// Update objective_values and preference_values from your optimization procedure
		updateFromOptimizationProcedure(data);
	}

	type EMOSolveRequest = components['schemas']['EMOSolveRequest'];
	type ReferencePoint = components['schemas']['ReferencePoint'];

	async function updateFromOptimizationProcedure(data: {
		num_solutions: number;
		type_preferences: PreferenceValue;
		preference_values: number[];
		objective_values: number[];
	}) {
		try {
			console.log('Starting EMO solve with data:', data);

			if (!problem?.id) {
				throw new Error('No problem ID available');
			}

			// Create the aspiration_levels object
			const aspiration_levels: { [key: string]: number } = {};

			if (problem.objectives && data.preference_values) {
				problem.objectives.forEach((objective, index) => {
					if (index < data.preference_values.length) {
						// Use the format from the test: "f_1_min", "f_2_min", etc.
						const key = `f_${index + 1}_min`;
						aspiration_levels[key] = data.preference_values[index];
					}
				});
			}

			console.log('Created aspiration_levels:', aspiration_levels);

			const preference: ReferencePoint = {
				preference_type: 'reference_point',
				aspiration_levels: aspiration_levels
			};

			const solveRequest: EMOSolveRequest = {
				problem_id: problem.id,
				method: emo_method,
				preference: preference,
				max_evaluations: max_evaluations,
				number_of_vectors: data.num_solutions,
				use_archive: use_archive,
				session_id: null,
				parent_state_id: null
			};

			console.log('Final solve request:', JSON.stringify(solveRequest, null, 2));

			// Call the solve endpoint
			const response = await fetch('/interactive_methods/EMO/solve', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				credentials: 'include',
				body: JSON.stringify(solveRequest)
			});

			console.log('Response status:', response.status);
			console.log('Response headers:', Object.fromEntries(response.headers.entries()));

			if (!response.ok) {
				const errorData = await response.json();
				console.error('Error response data:', errorData);
				throw new Error(
					`HTTP error! status: ${response.status}, message: ${errorData.error || 'Unknown error'}, details: ${errorData.details || 'No details'}`
				);
			}

			const result = await response.json();
			console.log('Success response:', result);

			if (result.success && result.data) {
				// Extract the new values from the EMO solve response
				const emoState = result.data; // This is EMOState type

				console.log('EMO solve response:', emoState);

				// Update based on the EMO response structure
				if (emoState.solutions && emoState.solutions.length > 0) {
					// Use the first solution or implement logic to select the best one
					const selectedSolution = emoState.solutions[0];

					// Extract objective values from the selected solution
					if (emoState.outputs && emoState.outputs.length > 0) {
						const selectedOutput = emoState.outputs[0];

						// Convert the objective values object to array
						const newObjectiveValues: number[] = [];
						if (problem.objectives) {
							problem.objectives.forEach((objective) => {
								if (selectedOutput[objective.name] !== undefined) {
									newObjectiveValues.push(selectedOutput[objective.name]);
								}
							});
						}

						if (newObjectiveValues.length > 0) {
							objective_values = newObjectiveValues;
						}
					}

					// Update preference values with the solution variables if needed
					// or keep the current preference values as they represent user input
				}

				// Update number of solutions if provided
				if (emoState.number_of_vectors) {
					num_solutions = emoState.number_of_vectors;
				}

				console.log('Updated from EMO solve:', {
					num_solutions,
					previous_preference: {
						type: previous_preference.type,
						values: formatNumberArray(previous_preference.values)
					},
					current_preference: {
						type: current_preference.type,
						values: formatNumberArray(current_preference.values)
					},
					objective_values: formatNumberArray(objective_values)
				});
			} else {
				console.error('EMO solve failed:', result.error || 'Unknown error');
				throw new Error(result.error || 'EMO solve failed');
			}
		} catch (error) {
			console.error('Error calling EMO solve:', error);
			alert(`Error solving problem: ${error}`);
		}
	}

	// Optional fallback function if you want to keep simulation as backup
	function fallbackToSimulation(data: {
		num_solutions: number;
		type_preferences: PreferenceValue;
		preference_values: number[];
		objective_values: number[];
	}) {
		console.log('Using simulation fallback');

		const simulatedNewObjectiveValues = objective_values.map(
			(val) => val + Math.random() * 0.1 - 0.05
		);
		const simulatedNewPreferenceValues = current_preference.values.map(
			(val) => val + Math.random() * 0.1 - 0.05
		);

		objective_values = simulatedNewObjectiveValues;
		current_preference = {
			type: current_preference.type,
			values: simulatedNewPreferenceValues
		};
	}

	function handleFinish(data: {
		num_solutions: number;
		type_preferences: PreferenceValue;
		preference_values: number[];
		objective_values: number[];
	}) {
		console.log('Finish clicked with data:', {
			num_solutions: data.num_solutions,
			type_preferences: data.type_preferences,
			preference_values: formatNumberArray(data.preference_values),
			objective_values: formatNumberArray(data.objective_values)
		});

		// Store final result as previous preference
		previous_preference = {
			type: current_preference.type,
			values: [...current_preference.values]
		};

		// Handle finishing the optimization process
		console.log('Final preferences:', {
			previous_preference: {
				type: previous_preference.type,
				values: formatNumberArray(previous_preference.values)
			},
			current_preference: {
				type: current_preference.type,
				values: formatNumberArray(current_preference.values)
			},
			objective_values: formatNumberArray(objective_values)
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

					<!-- Debug info with formatted numbers -->
					<div class="mb-4 rounded bg-gray-50 p-2 text-xs">
						<div><strong>Num Solutions:</strong> {num_solutions}</div>
						<div><strong>Objective Values:</strong> {formatNumberArray(objective_values)}</div>
						<div class="mt-2">
							<strong>Current Preference:</strong>
							<div class="ml-2">
								<div>Type: {current_preference.type}</div>
								<div>Values: {formatNumberArray(current_preference.values)}</div>
							</div>
						</div>
						<div class="mt-2">
							<strong>Previous Preference:</strong>
							<div class="ml-2">
								<div>Type: {previous_preference.type}</div>
								<div>Values: {formatNumberArray(previous_preference.values)}</div>
							</div>
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

							<!-- Show comparison between current and previous preferences with formatted numbers -->
							<div class="grid grid-cols-2 gap-4">
								<div class="rounded border p-3">
									<h4 class="font-semibold">Current Preference</h4>
									<p class="text-sm text-gray-600">Type: {current_preference.type}</p>
									<p class="text-sm text-gray-600">
										Values: {formatNumberArray(current_preference.values)}
									</p>
								</div>
								<div class="rounded border p-3">
									<h4 class="font-semibold">Previous Preference</h4>
									<p class="text-sm text-gray-600">Type: {previous_preference.type}</p>
									<p class="text-sm text-gray-600">
										Values: {formatNumberArray(previous_preference.values)}
									</p>
								</div>
							</div>

							<!-- Additional table showing individual values -->
							<div class="mt-4">
								<h4 class="mb-2 font-semibold">Detailed Values</h4>
								<div class="overflow-x-auto">
									<table class="min-w-full border border-gray-200">
										<thead class="bg-gray-50">
											<tr>
												<th class="border border-gray-200 px-4 py-2 text-left">Objective</th>
												<th class="border border-gray-200 px-4 py-2 text-left">Current Value</th>
												<th class="border border-gray-200 px-4 py-2 text-left">Previous Value</th>
												<th class="border border-gray-200 px-4 py-2 text-left">Objective Value</th>
											</tr>
										</thead>
										<tbody>
											{#if problem}
												{#each problem.objectives as objective, idx}
													<tr class="hover:bg-gray-50">
														<td class="border border-gray-200 px-4 py-2">{objective.name}</td>
														<td class="border border-gray-200 px-4 py-2">
															{formatNumber(current_preference.values[idx] || 0)}
														</td>
														<td class="border border-gray-200 px-4 py-2">
															{formatNumber(previous_preference.values[idx] || 0)}
														</td>
														<td class="border border-gray-200 px-4 py-2">
															{formatNumber(objective_values[idx] || 0)}
														</td>
													</tr>
												{/each}
											{/if}
										</tbody>
									</table>
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
