<!-- 
/**
 * Solutions Visualization Panel Component
 * 
 * This component displays the results from a multiobjective optimization algorithm
 * in various visual formats. The user can select which visualization to display, and select 
 * solutions from the visualizations for further analysis.
 * 
 * Data Flow:
 * 1. Parent component (EMO page, NIMBUS page, etc.) iterate.
 * 2. The corresponding method returns solutions with objective values, decision values, constaint values, etc.
 * 3. Parent passes solution arrays to this component.
 * 4. Component transforms data for visualization.
 * 5. User interacts with visualizations.
 * 6. Selected solutions are passed back to parent via onSelectSolution.
 * 
 * Author: Giomara Larraga (glarragw@jyu.fi)
 * Created: July 2025
 * 
 * @component VisualizationsPanel
 */
-->

<script lang="ts">
	import type { components } from '$lib/api/client-types';
	import ParallelCoordinates from '$lib/components/visualizations/parallel-coordinates/parallel-coordinates.svelte';
	import { PREFERENCE_TYPES, SIGNIFICANT_DIGITS } from '$lib/constants/index.js';
	import {
		calculateClassification,
		type PreferenceValue,
		formatNumber,
		type PreferenceType
	} from '$lib/helpers/index.js';

	// Type definitions from OpenAPI schema
	type ProblemInfo = components['schemas']['ProblemInfo'];

	/**
	 * Component Props Interface
	 *
	 * @interface Props
	 * @property {ProblemInfo | null} problem - The optimization problem definition including objectives, variables, and constraints
	 * @property {number[]} previous_preference_values - Previous iteration's preference values for comparison
	 * @property {string} previous_preference_type - Type of previous preference (reference_point, preferred_solution, etc.)
	 * @property {number[]} current_preference_values - Current iteration's preference values
	 * @property {string} current_preference_type - Type of current preference
	 * @property {number[][]} solutions_objective_values - Array of objective value arrays for each solution from EMO
	 * @property {number[][]} solutions_decision_values - Array of decision variable arrays for each solution from EMO
	 * @property {function} onSelectSolution - Callback when user selects a solution from the table
	 */
	interface Props {
		problem: ProblemInfo | null;
		previous_preference_values: number[];
		previous_preference_type: string;
		current_preference_values: number[];
		current_preference_type: string;
		solutions_objective_values?: number[][];
		solutions_decision_values?: number[][];
		onSelectSolution?: (index: number) => void;
	}

	const {
		problem,
		previous_preference_values,
		previous_preference_type,
		current_preference_values,
		current_preference_type,
		solutions_objective_values = [],
		solutions_decision_values = [],
		onSelectSolution
	}: Props = $props();

	/**
	 * Transform objective values into format expected by ParallelCoordinates
	 * Each solution becomes an object with named properties for each objective
	 */
	const objectiveData = $derived(() => {
		if (!solutions_objective_values.length || !problem?.objectives) return [];

		return solutions_objective_values.map((solution, index) => {
			const dataPoint: { [key: string]: number } = {};
			solution.forEach((value, objIndex) => {
				if (problem.objectives[objIndex]) {
					dataPoint[problem.objectives[objIndex].name] = value;
				}
			});
			return dataPoint;
		});
	});

	/**
	 * Create dimensions array for ParallelCoordinates
	 * Maps problem objectives to dimension definitions
	 */
	const objectiveDimensions = $derived(() => {
		if (!problem?.objectives) return [];

		return problem.objectives.map((obj) => ({
			name: obj.name,
			min: typeof obj.nadir === 'number' ? obj.nadir : undefined,
			max: typeof obj.ideal === 'number' ? obj.ideal : undefined,
			direction: obj.maximize ? ('max' as const) : ('min' as const)
		}));
	});

	/**
	 * Create reference data in the format expected by ParallelCoordinates
	 * Includes reference point and preferred ranges if available
	 */
	const referenceData = $derived(() => {
		if (!problem?.objectives) return undefined;

		// Create reference point from current preferences
		const referencePoint: { [key: string]: number } = {};
		if (current_preference_values.length > 0) {
			current_preference_values.forEach((value, index) => {
				if (problem.objectives[index]) {
					referencePoint[problem.objectives[index].name] = value;
				}
			});
		}

		// Optionally create preferred ranges (example: ±10% of reference point)
		const preferredRanges: { [key: string]: { min: number; max: number } } = {};
		if (current_preference_values.length > 0) {
			current_preference_values.forEach((value, index) => {
				if (problem.objectives[index]) {
					const objName = problem.objectives[index].name;
					const tolerance = Math.abs(value * 0.1); // 10% tolerance
					preferredRanges[objName] = {
						min: value - tolerance,
						max: value + tolerance
					};
				}
			});
		}

		return {
			referencePoint: Object.keys(referencePoint).length > 0 ? referencePoint : undefined,
			preferredRanges: Object.keys(preferredRanges).length > 0 ? preferredRanges : undefined
		};
	});

	/**
	 * Handle line selection from ParallelCoordinates
	 * Adapts the component's callback to match parent expectations
	 */
	function handleLineSelect(index: number | null, data: any) {
		if (index !== null && onSelectSolution) {
			onSelectSolution(index);
		}
	}

	/**
	 * Configuration options for the parallel coordinates plot
	 */
	const plotOptions = {
		showAxisLabels: true,
		highlightOnHover: true,
		strokeWidth: 2,
		opacity: 0.7,
		enableBrushing: true
	};

	// State for line selection and filtering
	let selectedIndex = $state<number | null>(null);
</script>

<!-- 
/**
 * Component Template
 * 
 * The template is organized into three main sections:
 * 1. Objective Space Visualization - Shows trade-offs between objectives
 * 2. Decision Space Visualization - Shows decision variable values
 * 3. Solutions Table - Interactive table for detailed inspection and selection
 * 
 * The layout uses responsive design with proper spacing and visual hierarchy.
 * Each section is conditionally rendered based on data availability.
 */
-->

<div class="space-y-4">
	{#if solutions_objective_values.length > 0}
		<!-- Objective Space Visualization with ParallelCoordinates -->
		<div>
			<ParallelCoordinates
				data={objectiveData()}
				dimensions={objectiveDimensions()}
				referenceData={referenceData()}
				options={plotOptions}
				{selectedIndex}
				onLineSelect={handleLineSelect}
			/>
		</div>
	{:else}
		<div class="rounded border bg-gray-50 p-8 text-center text-gray-500">
			No solutions available. Iterate to see results.
		</div>
	{/if}
</div>
