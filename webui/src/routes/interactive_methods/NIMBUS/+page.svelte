<script lang="ts">
	/**
	 * +page.svelte (NIMBUS method)
	 *
	 * @author Stina (Functionality) <palomakistina@gmail.com>
	 * @author Giomara Larraga (Base structure)<glarragw@jyu.fi>
	 * @created July 2025
	 *
	 * @description
	 * This page implements the NIMBUS interactive multiobjective optimization method in DESDEO.
	 * It displays a sidebar with problem information, a solution explorer with a combobox to select solution types,
	 * and a resizable pane layout for visualizing the objective and decision spaces, as well as solution tables.
	 *
	 * @props
	 * @property {Object} data - Contains a list of optimization problems fetched from the server.
	 * @property {ProblemInfo[]} data.problems - List of problems.
	 *
	 * @features
	 * - Sidebar with problem information and preference types.
	 * - Solution explorer with a combobox to select between "Current", "Best", and "All" solutions.
	 * - Responsive, resizable layout using PaneGroup and Pane components.
	 * - Visualization placeholders for objective and decision spaces.
	 * - Tabbed interface for numerical values and saved solutions.
	 *
	 * @dependencies
	 * - AppSidebar: Sidebar component for preferences and problem info.
	 * - Combobox: Custom combobox component for solution type selection.
	 * - Resizable: UI components for resizable panes.
	 * - Tabs: UI components for tabbed content.
	 * - methodSelection: Svelte store for the currently selected problem.
	 * - OpenAPI-generated ProblemInfo type.
	 *
	 * @notes
	 * - The selected problem is determined from the methodSelection store.
	 * - Visualization and table content are placeholders and should be implemented as needed.
	 */
	import { BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import type { components } from '$lib/api/client-types';
	import { onMount } from 'svelte';
	import { Combobox } from '$lib/components/ui/combobox';
	import Table from '$lib/components/ui/table/table.svelte';
	import TableBody from '$lib/components/ui/table/table-body.svelte';
	import TableRow from '$lib/components/ui/table/table-row.svelte';
	import TableHead from '$lib/components/ui/table/table-head.svelte';
	import TableCell from '$lib/components/ui/table/table-cell.svelte';

	import IntermediateSidebar from '$lib/components/custom/intermediate-sidebar.svelte';
	import { ToggleGroup, ToggleGroupItem } from '$lib/components/ui/toggle-group';

	import ConfirmationDialog from '$lib/components/custom/confirmation-dialog.svelte';
	import SolutionTable from '$lib/components/custom/solution-table/solution-table.svelte';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';
	import EchartsComponent from '$lib/components/custom/echarts-component.svelte';


	import { PREFERENCE_TYPES } from '$lib/constants';

	type ProblemInfo = components['schemas']['ProblemInfo'];

	// TODO: hopefully this will disappear too, when backend is ready and I can run client-types and use schemas
	// type OriginalSolution = components['schemas']['UserSavedSolutionAddress'];
	// type Solution = OriginalSolution & {
	// 	optimal_variables?: Record<string, number | number[]>; // TODO: this WILL BE REMOVED when I figure out where to get it, and API changes
	// };
		type Solution = {
		objective_values: {
			[key: string]: number | number[];
		};
		address_state: number;
		address_result: number;
		name?: string; // Optional name for the solution, used in the table, exists for all saved solutions
		optimal_variables?: Record<string, number | number[]>; // TODO: this WILL BE REMOVED when I figure out where to get it, and API changes
	};
	// Define a general type for any state with solver_results
	// TODO: This type will be rethought and not needed when API has changed 
	// (Vili is refactoring responses and hopefully they all will return EXACTLY the same state and I can use that here).
	type ResponseState = {
		state_id: number;
		previous_reference_point:{
			preference_type: 'reference_point',
			aspiration_levels: Record<string, number>
		};
		current_solutions: Solution[],
		saved_solutions: Solution[], // Using same solutions for all three lists for now
		all_solutions: Solution[],   // Using same solutions for all three lists for now
		
		_originalData: any
	};

	// State for NIMBUS iteration management
	let current_state: ResponseState = $state({} as ResponseState);
	
	let problem: ProblemInfo | null = $state(null);
	const { data } = $props<{ data: ProblemInfo[] }>();
	let problem_list = data.problems ?? [];
	// user can choose from three types of solutions: current, best, or all
	let selected_type_solutions = $state('current');
	
	// variables for handling different modes (iteration, intermediate, save, finish)
	// and chosen solutions that are separate for every mode
	let mode: "iterate" | "final" | "intermediate" = $state("iterate");
	// iteration mode
	let selected_iteration_index: number[] = $state([0]); // Index of solution from previous results to use in sidebar. List for consistency, but always has one element
	let current_num_iteration_solutions: number = $state(1); // how many solutions user wants when making the iteration
	let selected_iteration_objectives: Record<string, number> = $state({}); // actual objectives of the selected solution in iteration mode
	// intermediate mode
	let selected_intermediate_indexes: number[] = $state([]);
	let current_num_intermediate_solutions: number = $state(1);
	let selected_solutions_for_intermediate: Solution[] = $state([]); // actual objectives, but it is a list unlike for iteration, since user should choose two solutions
	// save mode
	let selected_save_indexes: number[] = $state([]);
	let selected_solutions_for_saving: Solution[] = $state([]);
	
	// currentPreference is initialized from previous preference or ideal values
	let current_preference: number[] = $state([]);
	// Store the last iterated preference values to show as "previous" in UI
	let last_iterated_preference: number[] = $state([]);

	// Variables for showing the map for UTOPIA
	type PeriodKey = 'period1' | 'period2' | 'period3';
	let mapOptions = $state<Record<PeriodKey, Record<string, any>>>({
		period1: {},
		period2: {},
		period3: {}
	});
	let yearlist = $state<string[]>([]);
	let selectedPeriod = $state<PeriodKey>("period1");
	let geoJSON = $state<object | undefined>(undefined);
	let mapName = $state<string | undefined>(undefined);
	let mapDescription = $state<string | undefined>(undefined);
	let compensation = $state(0.0);

	const frameworks = [
		{ value: 'current', label: 'Current solutions' },
		{ value: 'best', label: 'Best solutions' },
		{ value: 'all', label: 'All solutions' }
	];

	// Validation: iteration is allowed when at least one preference is better and one is worse than current objectives
	let is_iteration_allowed = $derived(() => {
		if (!problem || current_preference.length === 0 || Object.keys(selected_iteration_objectives).length === 0) {
			return false;
		}

		let has_improvement = false;
		let has_worsening = false;

		for (let i = 0; i < problem.objectives.length; i++) {
			const objective = problem.objectives[i];
			const preference_value = current_preference[i];
			const current_value = selected_iteration_objectives[objective.symbol];

			console.log(
				`Checking preference for ${objective.symbol}: preference=${preference_value}, current=${current_value}`
			);
			if (preference_value === undefined || current_value === undefined) {
				continue;
			}

			// Check if preference differs from current value.
			// It does not matter what actually is better or worse as long as there is both
			if (preference_value > current_value) {
				has_improvement = true;
			} else if (preference_value < current_value) {
				has_worsening = true;
			}
		}

		// Need both improvement and worsening for valid NIMBUS classification
		return has_improvement && has_worsening;
	})

	function handle_type_solutions_change(event: { value: string }) {
		selected_type_solutions = event.value;
		console.log('Selected type of solutions:', selected_type_solutions);
	}

	// Variables for handling unsaved changes confirmation
	let show_save_confirm_dialog: boolean = $state(false);
	let pending_selection_target: number = $state(-1); // Store the target row that was clicked
	let has_unsaved_changes: boolean = $state(false); // Store result from solution table
	function handle_solution_click(index: number) {
		// If there are unsaved changes, show confirmation dialog
		if (mode ==="iterate"){
			if(selected_iteration_index[0] === index) {
				return; // Already selected, do nothing
			}
			if (has_unsaved_changes) {
				// Store the target index for use after confirmation
				pending_selection_target = index;
				// Show the confirmation dialog
				show_save_confirm_dialog = true;
				return;
			}
            // Iterate mode: always select just one solution
            selected_iteration_index = [index];
			update_iteration_selection(current_state);
        } else if (mode === "intermediate") {
            // Intermediate mode: allow selecting up to 2 rows
            if (selected_intermediate_indexes.includes(index)) {
                // If already selected, deselect it, checking unsaved changes first
				if (has_unsaved_changes) {
					// Store the target index for use after confirmation
					pending_selection_target = index;
					// Show the confirmation dialog
					show_save_confirm_dialog = true;
					return;
				}
                selected_intermediate_indexes = selected_intermediate_indexes.filter(i => i !== index);
            } else if (selected_intermediate_indexes.length < 2) {
                // Only add if we haven't reached the limit of 2, checking unsaved changes first
				if (has_unsaved_changes) {
					// Store the target index for use after confirmation
					pending_selection_target = index;
					// Show the confirmation dialog
					show_save_confirm_dialog = true;
					return;
				}
                selected_intermediate_indexes = [...selected_intermediate_indexes, index];
            }
			update_intermediate_selection(current_state);
        }
	}
								
	// This function handles the selection change after confirmation dialog
	function handle_solution_click_after_pop_up() {
		console.log('Changes confirmed, proceeding with selection change');
		// Apply the pending selection if there was one
		if (pending_selection_target >= 0) {
			const index = pending_selection_target;
			
			if (mode === "iterate") {
				selected_iteration_index = [index];
				update_iteration_selection(current_state);
			} else if (mode === "intermediate") {
				// Intermediate mode: allow selecting up to 2 rows
				if (selected_intermediate_indexes.includes(index)) {
					// If already selected, deselect
					selected_intermediate_indexes = selected_intermediate_indexes.filter(i => i !== index);
				} else if (selected_intermediate_indexes.length < 2) {
					// Only add if we haven't reached the limit of 2
					selected_intermediate_indexes = [...selected_intermediate_indexes, index];
				}
				update_intermediate_selection(current_state);
			}
		}
		// Reset pending selection
		pending_selection_target = -1;
	}

	let show_confirm_dialog: boolean = $state(false);
	function handle_press_finish() {
		show_confirm_dialog = true;
	}
	// TODO: Handler for finishing the NIMBUS optimization process, right now I should just make better view
	async function handle_finish() {
		try {
			const response = await fetch('/interactive_methods/NIMBUS/?type=choose', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					problem_id: problem?.id,
					solution: selected_iteration_index[0]
				})
			});

			const result = await response.json();

			if (result.success) {
				mode = "final";
				console.log(result.message);
			} else {
				console.error('Failed to save final choice:', result.error);
			}
		} catch (error) {
			console.error('Error calling mock endpoint:', error);
		}
	}

	// TODO: actual http request
	async function handle_intermediate() {
		try {
			const response = await fetch('/interactive_methods/NIMBUS/?type=intermediate', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					problem_id: problem?.id,
					solution: selected_iteration_index[0],
				}),
			});

			const result = await response.json();

			if (result.success) {
				mode = "iterate";
				console.log(result.message);
			} else {
				console.error('Failed to solve intermediate solutions:', result.error);
			}
		} catch (error) {
			console.error('Error calling mock endpoint:', error);
		}
	}

	// TODO: actual http request and reaction to name change, possible ONLY after new endpoint is implemented
	// Save a solution with an optional name
	async function handle_save(solution: Solution, name: string | undefined) {		
		// Check if solution is already in saved_solutions by comparing state_id and result_index 
		// TODO: ASK if we should rather compare VALUES to avoid duplicates. But in this case, would the name change modify the OLD solution? Is that ok? 
		// What would be the marginal? Should it come from problem metadata in this case also? In backend, also? And, in my opinion, these cases are different! Are they, though?
		// meaning, the case where solution values match old solution, vs the case where state and result index match. 
		// The first one is "there is a similar solution saved" and the second one is "this solution is saved already"
		
		
		// Create a copy of the solution with the name
		const solutionToSave = {
			...solution,
			name: name
		};
		
		// save the solution to the server
		try {
			const response = await fetch('/interactive_methods/NIMBUS/?type=save', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					problem_id: problem?.id,
					solutions: [solutionToSave], // we save one solution at a time
				}),
			});

			const result = await response.json();

			if (result.success) {
				// Update the solution in all lists after it is successfully saved in the backend
				const updateSolutionInList = (list: Solution[]) => 
					list.map(item => 
						(item.address_state === solution.address_state && item.address_result === solution.address_result) 
							? solutionToSave 
							: item
					);
				const existingIndex = current_state.saved_solutions.findIndex(
					saved => saved.address_state === solution.address_state && saved.address_result === solution.address_result
				);
				let updatedSavedSolutions;
				if (existingIndex !== -1) {
					// Solution already exists in saved_solutions, update the name
					updatedSavedSolutions = [...current_state.saved_solutions];
					updatedSavedSolutions[existingIndex] = {
						...updatedSavedSolutions[existingIndex],
						name: name
					};
				} else {
					// Add to saved_solutions
					updatedSavedSolutions = [...current_state.saved_solutions, solutionToSave];
				}
				
				current_state = {
					...current_state,
					current_solutions: updateSolutionInList(current_state.current_solutions),
					saved_solutions: updatedSavedSolutions,
					all_solutions: updateSolutionInList(current_state.all_solutions)


				};
				
				console.log('Solution saved successfully:', result.message);
				console.log($state.snapshot(current_state));
			} else {
				console.error('Failed to save solution:', result.error);
			}
		} catch (error) {
			console.error('Error calling save endpoint:', error);
		}
	}


	// The optional unused values are kept for compatibility with the AppSidebar component
	async function handle_iterate(data: {
		numSolutions: number;
		typePreferences: string;
		preferenceValues: number[];
		objectiveValues: number[];
	}) {
		if (!problem) {
			console.error('No problem selected');
			return;
		}
		if (current_preference.length === 0) {
			console.error('No preferences set');
			return;
		}
		if (!is_iteration_allowed()) {
			console.error('Iteration not allowed based on current preferences and objectives');
			return;
		}

		const session_id = null;
		const parent_state_id = null;
		const preference = {
			// TODO: change this to PREFERENCE_TYPES.CLASSIFICATION 
			// what is this comment, oh, right type or what? and what the heck does the reduce do here?
			// this is quite vital to understand now, since the whole NIMBUS method is based on classification
			preference_type: 'reference_point',
			aspiration_levels: problem.objectives.reduce(
				(acc, obj, idx) => {
					acc[obj.symbol] = current_preference[idx] || 0;
					return acc;
				},
				{} as Record<string, number>
			)
		};

		try {
			const response = await fetch('/interactive_methods/NIMBUS/?type=iterate', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					problem_id: problem.id,
					session_id: session_id,
					parent_state_id: parent_state_id,
					current_objectives: selected_iteration_objectives,
					num_desired: current_num_iteration_solutions,
					preference: preference
				})
			});

			const result = await response.json();
			// {
			// 	state_id: mockStateId,
			// 	previous_reference_point: originalData.previous_preference || preference,
			// 	current_solutions: solutionsList,
			// 	saved_solutions: [], // [] for now
			// 	all_solutions: solutionsList,   // Using same solutions for two lists for now
			// }
			if (result.success) {
				// Store the preference values that were just used for iteration
				last_iterated_preference = [...current_preference];
				current_state = result.data;
				selected_iteration_index = [0];
				update_iteration_selection(current_state);
				current_num_iteration_solutions = current_state.current_solutions.length
				console.log('NIMBUS iteration successful:', result.data);
			} else {
				console.error('NIMBUS iteration failed:', result.error);
			}
		} catch (error) {
			console.error('Error calling NIMBUS iterate:', error);
		}
	}

	// TODO: check if some information is missing, is there any validation or error handling to be added?
	async function getMaps(variables: Record<string, number | number[]>) {
		if (!problem) {
			console.error('No problem selected');
			return;
		}
		
		try {
			const response = await fetch('/interactive_methods/NIMBUS/?type=get_maps', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					problem_id: problem.id,
					solution: variables
				})
			});

			if (!response.ok) {
				throw new Error(`HTTP error! Status: ${response.status}`);
			}

			const result = await response.json();
			console.log(result)
			if (result.success) {
				const data = result.data;
				
				// Update state variables with the fetched data
				yearlist = data.years;
				
				// Apply the formatter function client-side
				for (let year of yearlist) {
					if (data.options[year].tooltip.formatterEnabled) {
						data.options[year].tooltip.formatter = function (params: any) {
							return `${params.name}`;
						};
					}
				}
				
				// Assign map options for each period
				mapOptions = {
					period1: data.options[yearlist[0]] || {},
					period2: data.options[yearlist[1]] || {},
					period3: data.options[yearlist[2]] || {}
				} as Record<PeriodKey, Record<string, any>>;
				
				geoJSON = data.map_json;
				mapName = data.map_name;
				mapDescription = data.description;
				compensation = Math.round(data.compensation * 100) / 100;
				
				console.log('Maps data loaded successfully');
			} else {
				console.error('Failed to get maps:', result.error);
			}
		} catch (error) {
			console.error('Error fetching maps:', error);
			// Could add UI notification here
		}
	}

	// Helper function to update current iteration objectives from the current state
	// TODO: rethink and see if changes needed, after StateWithResults has changed (Vili)
	// ASK COPILOT
	// ALSO, all helper functions could go to their own file? Where?
	//
	// NEW FORM OF RESPONSE:
	// {
	// 	state_id: mockStateId,
	// 	previous_reference_point: originalData.previous_preference || preference,
	// 	current_solutions: solutionsList,
	// 	saved_solutions: solutionsList, // Using same solutions for all three lists for now
	// 	all_solutions: solutionsList,   // Using same solutions for all three lists for now
		
	// 	_originalData: originalData
	// }
	// 	type SolutionList = {
	// 	objective_values: {
	// 		[key: string]: number | number[];
	// 	};
	// 	state_id: number;
	// 	result_index: number;
	// }[];
	function update_iteration_selection(state: ResponseState | null) {
		if (!problem) return;
		if (!state || !state.current_solutions || state.current_solutions.length === 0) return;
			const selectedSolution = state.current_solutions[selected_iteration_index[0]]; 
			if (selectedSolution && selectedSolution.objective_values) {
				// Convert objective_values to the format expected by the API
				const newObjectives: Record<string, number> = {};
				for (const [key, value] of Object.entries(selectedSolution.objective_values)) {
					newObjectives[key] = Array.isArray(value) ? value[0] : value;
				}
				selected_iteration_objectives = newObjectives;
				console.log(`Updated current objectives from solution `,selected_iteration_index[0]+1,`:`, selected_iteration_objectives);
				if (selectedSolution.optimal_variables) {
					getMaps(selectedSolution.optimal_variables);
				}
			} else {
				console.warn('Selected solution is invalid');
			}
	}

	// Helper function to update current intermediate objectives from the current state
	function update_intermediate_selection(state: ResponseState | null) {
		if (!problem) return;
		if (!state || !state.current_solutions || state.current_solutions.length === 0) return;
		selected_solutions_for_intermediate = selected_intermediate_indexes.map((i) => state.current_solutions[i]); 
	}

    // helper function to check if a solution is saved (exists in savedSolutions)
    function isSaved(solution: Solution): boolean {
		return current_state.saved_solutions.some(
			saved => saved.address_state === solution.address_state && saved.address_result === solution.address_result
		);
    }

	// Helper function to initialize preferences from previous state or ideal values
	// TODO: rethink and see if changes needed, after StateWithResults has changed (Vili)
	function update_preferences_from_state(state: ResponseState | null) {
		if (!problem) return;
		// Try to get previous preference from NIMBUS state
		if (state && 'previous_reference_point' in state && state.previous_reference_point) {
			// Extract aspiration levels from previous preference
			const previous_pref = state.previous_reference_point as {
				aspiration_levels?: Record<string, number>;
			};
			if (previous_pref.aspiration_levels) {
				current_preference = problem.objectives.map(
					(obj) => previous_pref.aspiration_levels![obj.symbol] ?? obj.ideal ?? 0
				);
				console.log('Initialized preferences from previous state:', current_preference);
				return;
			}
		}
		// Fallback to ideal values
		current_preference = problem.objectives.map((obj) => obj.ideal ?? 0);
		console.log('Initialized preferences from ideal values:', current_preference);
	}

	onMount(async () => {
		if ($methodSelection.selectedProblemId) {
			problem = problem_list.find(
				(p: ProblemInfo) => String(p.id) === String($methodSelection.selectedProblemId)
			);

			if (problem) {
				// Initialize NIMBUS state from the API
				await initialize_nimbus_state(problem.id);
			}
		}
	});

	// Initialize NIMBUS state by calling the API endpoint
	async function initialize_nimbus_state(problem_id: number) {
		try {
			const response = await fetch('/interactive_methods/NIMBUS/?type=initialize', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					problem_id: problem_id,
					session_id: null, // Use active session
					parent_state_id: null, // No parent for initialization
					solver: null // Use default solver
				})
			});

			const result = await response.json();

			if (result.success) {
				current_state = result.data;
				selected_iteration_index =[0];
				update_iteration_selection(current_state);
				update_preferences_from_state(current_state);
				current_num_iteration_solutions = current_state.current_solutions.length;
				// update names in all current_solutions and all_solutions that are saved
				for (let solution of current_state.current_solutions) {
					const savedIndex = current_state.saved_solutions.findIndex(
						saved => saved.address_state === solution.address_state && saved.address_result === solution.address_result
					);
					if (savedIndex !== -1) {
						// Solution exists in saved_solutions, update the name
						solution.name = current_state.saved_solutions[savedIndex].name;
					}
				}
				for (let solution of current_state.all_solutions) {
					const savedIndex = current_state.saved_solutions.findIndex(
						saved => saved.address_state === solution.address_state && saved.address_result === solution.address_result
					);
					if (savedIndex !== -1) {
						solution.name = current_state.saved_solutions[savedIndex].name;
					}
				}
			} else {
				console.error('NIMBUS initialization failed:', result.error);
			}
		} catch (error) {
			console.error('Error initializing NIMBUS:', error);
		}
	}

	// TODO: Understand: what is this?
	// Convert data to match AppSidebar interface
	let type_preferences = $state(PREFERENCE_TYPES.Classification);

	// Add the missing callback that updates internal state
	// This function is called when the user changes preferences in the AppSidebar
	// TODO: ask! in NIMBUS, there are no other preferences than classification?
	function handle_preference_change(data: {
		numSolutions: number;
		typePreferences: string;
		preferenceValues: number[];
		objectiveValues: number[];
	}) {
		current_num_iteration_solutions = data.numSolutions;
		type_preferences = data.typePreferences;
		current_preference = [...data.preferenceValues];
		console.log('Preference changed:', data);
	}
</script>

{#if mode === "final"}
	<div class="card">
		<div class="card-header">Solution Review</div>
		{#if problem && current_state?.current_solutions[selected_iteration_index[0]]}
			<div class="card-body">
				<h3>Selected Solution Objectives:</h3>
				<Table>
					<TableBody>
						<TableRow>
							{#each problem.objectives as objective}
								<TableHead>
									{objective.name}
									{objective.unit ? `/ ${objective.unit}` : ''}
								</TableHead>
							{/each}
						</TableRow>
						<TableRow>
							{#each problem.objectives as objective}
								<TableCell>
									{current_state.current_solutions[selected_iteration_index[0]].objective_values[
										objective.symbol
									]}
								</TableCell>
							{/each}
						</TableRow>
					</TableBody>
				</Table>
				<div class="grid h-full w-full gap-4 xl:grid-cols-2">
					<div class="min-h-[50rem] flex-1 rounded bg-gray-100 p-4">
						<span>Objective space</span>
					</div>
					<div class="min-h-[50rem] flex-1 rounded bg-gray-100 p-4">
						<span>Decision space</span>
					</div>
				</div>
			</div>
		{:else}
			<div class="card-body">
				<p>Error: Unable to display the selected solution.</p>
			</div>
		{/if}
	</div>
{:else}
	<BaseLayout showLeftSidebar={!!problem} showRightSidebar={false}>
		{#snippet leftSidebar()}
			<div class="mt-4">
				<ToggleGroup type="single" bind:value={mode}>
					<ToggleGroupItem value="iterate">Iterate or finish</ToggleGroupItem>
					<ToggleGroupItem value="intermediate">Find intermediate</ToggleGroupItem>
				</ToggleGroup>
			</div>
			{#if problem && mode==="iterate"}
				<AppSidebar
					{problem}
					preferenceTypes={[PREFERENCE_TYPES.Classification]}
					showNumSolutions={true}
					numSolutions={current_num_iteration_solutions}
					typePreferences={type_preferences}
					preferenceValues={current_preference}
					objectiveValues={Object.values(selected_iteration_objectives)}
					isIterationAllowed={is_iteration_allowed()}
					isFinishAllowed={true}
					minNumSolutions={1}
					maxNumSolutions={4}
					lastIteratedPreference={last_iterated_preference}
					onPreferenceChange={handle_preference_change}
					onIterate={handle_iterate}
					onFinish={handle_press_finish}
				/>
			{:else if problem && mode ==="intermediate"}
				<div class="flex flex-col">
					<IntermediateSidebar 
							{problem}
							currentSolutions={selected_solutions_for_intermediate}
							bind:numSolutions={current_num_intermediate_solutions}
							minNumSolutions={1}
							maxNumSolutions={4}
							onClick={handle_intermediate}
					/>
				</div>	
			{/if}
		{/snippet}

		{#snippet explorerControls()}
			<span>View: </span>
			<Combobox
				options={frameworks}
				defaultSelected={selected_type_solutions}
				onChange={handle_type_solutions_change}
			/>
		{/snippet}

		{#snippet visualizationArea()}
			{#if problem && current_state && current_state.current_solutions}
				{@const nonNullProblem = problem}
				{@const nonNullState = current_state}
				<!-- TODO: 
				 - this nonNullBlahblah is stupid! How to avoid it? Typing compaints
				 - lots of shit given to props. Make separate functions, see if you can simplify things -->
				<!-- Grid layout to place visualizations side by side with fixed height -->
				<div class="flex gap-4 h-full">
					<!-- Left side: VisualizationsPanel with constrained height -->
					<div class="flex-1">
						{#if mode === "iterate"}
							<!-- Iteration mode visualization -->
							<VisualizationsPanel
								problem={nonNullProblem}
								previousPreferenceValues={last_iterated_preference}
								previousPreferenceType={type_preferences}
								currentPreferenceValues={current_preference}
								currentPreferenceType={type_preferences}
								solutionsObjectiveValues={nonNullState.current_solutions.map(result => {
									return nonNullProblem.objectives.map(obj => {
										const value = result.objective_values[obj.symbol];
										return Array.isArray(value) ? value[0] : value;
									});
								})}
								solutionsDecisionValues={nonNullState.current_solutions.map(result => {
									if (!result.optimal_variables) return [];
									return Object.values(result.optimal_variables).filter(val => typeof val === 'number');
								})}
								externalSelectedIndexes={selected_iteration_index.length > 0 ? selected_iteration_index : null}
								onSelectSolution={handle_solution_click}
							/>
						{:else if mode === "intermediate"}
							<!-- Intermediate mode visualization -->
							<VisualizationsPanel
								problem={nonNullProblem}
								previousPreferenceValues={last_iterated_preference}
								previousPreferenceType={type_preferences}
								currentPreferenceValues={current_preference}
								currentPreferenceType={type_preferences}
								solutionsObjectiveValues={nonNullState.current_solutions.map(result => {
									return nonNullProblem.objectives.map(obj => {
										const value = result.objective_values[obj.symbol];
										return Array.isArray(value) ? value[0] : value;
									});
								})}
								solutionsDecisionValues={nonNullState.current_solutions.map(result => {
									if (!result.optimal_variables) return [];
									return Object.values(result.optimal_variables).filter(val => typeof val === 'number');
								})}
								externalSelectedIndexes={selected_intermediate_indexes.length > 0 ? selected_intermediate_indexes : null}
								onSelectSolution={handle_solution_click}
							/>
						{/if}
					</div>
					<!-- TODO: Map to its own component? Beautify the map-->
					<!-- Right side: Decision space placeholder, that is A MAP FOR UTOPIA-->
					 {#if mode === "iterate"}
						<div class="overflow-auto h-full flex-1">
							<div class="flex-1">
								
								{#if mapOptions[selectedPeriod] && Object.keys(mapOptions[selectedPeriod]).length > 0 && geoJSON}
								<div class="flex">
									<!-- Period selection toggle -->
									<div>
										<h3 class="text-lg">{mapName || 'Forest Map'}</h3>
										<ToggleGroup type="single" bind:value={selectedPeriod}>
											{#each yearlist as year, i}
											<ToggleGroupItem value={`period${i+1}`}>
												{year || `Period ${i+1}`}
											</ToggleGroupItem>
											{/each}
										</ToggleGroup>
										<div class="text-sm" style="white-space: pre-wrap;">{mapDescription}</div>
									</div>
									<!-- The actual map visualization -->
									<EchartsComponent
									option={mapOptions[selectedPeriod]}
									{geoJSON}
									{mapName}
									customStyle="height: 400px; "
									/>
								</div>
								{:else}
									<div class="placeholder">
									<p>Select a solution to view the map visualization</p>
									</div>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			{:else}
				<div class="flex h-full items-center justify-center text-gray-500">
					No problem data available for visualization
				</div>
			{/if}
		{/snippet}
		{#snippet numericalValues()}
			{#if problem && current_state?.current_solutions && current_state.current_solutions.length > 0}
				{#if mode === "iterate"}
					<SolutionTable
						{problem}
						solverResults={current_state.current_solutions}
						isSaved={isSaved}
						bind:selectedSolutions={selected_iteration_index}
						handle_save={handle_save}
						handle_row_click={handle_solution_click}
						bind:has_unsaved_changes={has_unsaved_changes}
					/>
				{:else if mode === "intermediate"}
					<SolutionTable
						{problem}
						solverResults={current_state.current_solutions}
						isSaved={isSaved}
						bind:selectedSolutions={selected_intermediate_indexes}
						handle_save={handle_save}
						handle_row_click={handle_solution_click}
						bind:has_unsaved_changes={has_unsaved_changes}
					/>
				{/if}
			{/if}
		{/snippet}
	</BaseLayout>
{/if}

<ConfirmationDialog
	bind:open={show_confirm_dialog}
	title="Confirm Final Choice"
	description="Are you sure you want to proceed with this solution as your final choice?"
	confirmText="Yes, Proceed"
	cancelText="Cancel"
	onConfirm={handle_finish}
	onCancel={() => console.log('Cancelled')}
/>
<ConfirmationDialog
	bind:open={show_save_confirm_dialog}
	title="Unsaved Changes"
	description="You have unsaved changes to solution names. Do you want to discard these changes and select another solution?"
	confirmText="Discard Changes"
	cancelText="Keep Editing"
	onConfirm={handle_solution_click_after_pop_up}
	onCancel={() => {
		console.log('Selection change cancelled, continuing editing');
		show_save_confirm_dialog = false;
		
		// Reset pending selection without making any changes
		pending_selection_target = -1;
	}}
/>
