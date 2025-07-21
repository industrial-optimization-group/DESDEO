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
	import { createReferenceData } from '$lib/helpers/preference-data-transforms';
	import {
		createObjectiveDimensions,
		transformObjectiveData
	} from '$lib/helpers/visualization-data-transform';
	import { onMount } from 'svelte';

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
	const objectiveData = $derived(() => transformObjectiveData(solutions_objective_values, problem));
	/**
	 * Create dimensions array for ParallelCoordinates
	 * Maps problem objectives to dimension definitions
	 */
	const objectiveDimensions = $derived(() => createObjectiveDimensions(problem));

	/**
	 * Create reference data in the format expected by ParallelCoordinates
	 * Includes reference point and preferred ranges if available
	 */
	const referenceData = $derived(() =>
		createReferenceData(current_preference_values, previous_preference_values, problem)
	);

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
	let brushFilters = $state<{ [dimension: string]: [number, number] }>({});

	// Add container size tracking
	let containerElement: HTMLDivElement;
	let containerSize = $state({ width: 0, height: 0 });

	onMount(() => {
		if (!containerElement) return;

		const resizeObserver = new ResizeObserver((entries) => {
			for (let entry of entries) {
				const { width, height } = entry.contentRect;
				containerSize = { width, height };
			}
		});

		resizeObserver.observe(containerElement);

		return () => {
			resizeObserver.disconnect();
		};
	});

	// Calculate dynamic height for ParallelCoordinates
	const plotHeight = $derived(() => {
		// Reserve space for header, instructions, and table
		const reservedSpace = 10; // Adjust based on your layout
		return Math.max(containerSize.height - reservedSpace, 10);
	});

	/**
	 * Handle brush filter changes
	 */
	function handleBrushFilter(filters: { [dimension: string]: [number, number] }) {
		brushFilters = filters;
		console.log('Brush filters updated:', filters);
	}
</script>

<!-- 
/**
 * Component Template
 * 
 * The ParallelCoordinates component handles its own resizing, so we just need
 * to provide a properly sized container and let it manage the rest.
 */
-->

<div bind:this={containerElement} class="flex h-full w-full flex-col space-y-4 overflow-hidden">
	{#if solutions_objective_values.length > 0}
		<!-- Objective Space Visualization with dynamic height -->
		<!-- Use dynamic height that responds to container size -->
		<div class="w-full" style="height: {plotHeight()}px;">
			<ParallelCoordinates
				data={objectiveData()}
				dimensions={objectiveDimensions()}
				referenceData={referenceData()}
				options={plotOptions}
				{selectedIndex}
				{brushFilters}
				onLineSelect={handleLineSelect}
				onBrushFilter={handleBrushFilter}
			/>
		</div>
	{:else}
		<div
			class="flex h-full items-center justify-center rounded border bg-gray-50 p-8 text-center text-gray-500"
		>
			No solutions available. Run the optimization to see results.
		</div>
	{/if}
</div>
