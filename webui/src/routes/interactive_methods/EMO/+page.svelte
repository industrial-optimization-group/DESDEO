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
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';

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
	// Change these to store arrays of solutions instead of single values
	let solutions_objective_values = $state<number[][]>([]); // Array of objective value arrays
	let solutions_decision_values = $state<number[][]>([]); // Array of decision variable arrays
	let objective_values = $state<number[]>([]); // Keep this for current/selected solution

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
				const emoState = result.data; // This is EMOState type
				console.log('EMO solve response:', emoState);

				// Extract ALL solutions and their objective values
				if (
					emoState.solutions &&
					emoState.solutions.length > 0 &&
					emoState.outputs &&
					emoState.outputs.length > 0
				) {
					// Clear previous solutions
					solutions_objective_values = [];
					solutions_decision_values = [];

					// Process each solution
					emoState.solutions.forEach((solution: number[], solutionIndex: number) => {
						// Extract decision variables (solution variables)
						if (Array.isArray(solution)) {
							solutions_decision_values.push([...solution]);
						} else if (typeof solution === 'object') {
							// If solution is an object, convert to array
							const decisionVars = Object.values(solution).filter(
								(val) => typeof val === 'number'
							) as number[];
							solutions_decision_values.push(decisionVars);
						}

						// Extract corresponding objective values
						if (emoState.outputs[solutionIndex]) {
							const output = emoState.outputs[solutionIndex];
							const objectiveVals: number[] = [];

							if (problem?.objectives) {
								// Use objective names to extract values in correct order
								problem.objectives.forEach((objective) => {
									if (output[objective.name] !== undefined) {
										objectiveVals.push(output[objective.name]);
									}
								});
							} else {
								// Fallback: use all numeric values from output
								Object.values(output).forEach((val) => {
									if (typeof val === 'number') {
										objectiveVals.push(val);
									}
								});
							}

							if (objectiveVals.length > 0) {
								solutions_objective_values.push(objectiveVals);
							}
						}
					});

					// Update the current objective values with the first solution (or best solution)
					if (solutions_objective_values.length > 0) {
						objective_values = [...solutions_objective_values[0]];
					}

					console.log('Extracted solutions:', {
						numSolutions: solutions_objective_values.length,
						objectiveValues: solutions_objective_values,
						decisionValues: solutions_decision_values,
						currentObjective: objective_values
					});
				}

				// Update number of solutions if provided
				if (emoState.number_of_vectors) {
					num_solutions = emoState.number_of_vectors;
				}

				console.log('Updated from EMO solve:', {
					num_solutions,
					total_solutions: solutions_objective_values.length,
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
			// Clear previous solutions
			solutions_objective_values = [];
			solutions_decision_values = [];

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

	<div class="flex min-w-0 flex-1 flex-col">
		<Resizable.PaneGroup direction="vertical" class="flex-1">
			<Resizable.Pane class="flex min-h-0 flex-col">
				<div class="flex-shrink-0 p-2">
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
				</div>

				<!-- This container will flex to fill available space -->
				<div class="mx-2 min-h-0 flex-1 rounded border bg-gray-100 p-4">
					{#if problem}
						<VisualizationsPanel
							{problem}
							previous_preference_values={previous_preference.values}
							previous_preference_type={previous_preference.type}
							current_preference_values={current_preference.values}
							current_preference_type={current_preference.type}
							{solutions_objective_values}
							{solutions_decision_values}
							onSelectSolution={(index) => {
								// Update current objective values when user selects a solution
								if (solutions_objective_values[index]) {
									objective_values = [...solutions_objective_values[index]];
									console.log('Selected solution', index, 'with objectives:', objective_values);
								}
							}}
						/>
					{:else}
						<div class="flex h-full items-center justify-center text-gray-500">
							No problem data available for visualization
						</div>
					{/if}
				</div>
			</Resizable.Pane>

			<Resizable.Handle />

			<Resizable.Pane class="flex-shrink-0 p-2">
				<Tabs.Root value="numerical-values">
					<Tabs.List>
						<Tabs.Trigger value="numerical-values">Numerical values</Tabs.Trigger>
						<Tabs.Trigger value="saved-solutions">Saved solutions</Tabs.Trigger>
					</Tabs.List>
					<Tabs.Content value="numerical-values">Tables</Tabs.Content>
					<Tabs.Content value="saved-solutions">Visualize saved solutions</Tabs.Content>
				</Tabs.Root>
			</Resizable.Pane>
		</Resizable.PaneGroup>
	</div>

	<AdvancedSidebar />
</div>
