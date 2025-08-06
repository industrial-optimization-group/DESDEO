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
	 * @property {number[]} currentPreferenceValues - Current iteration's preference values
	 * @property {string} currentPreferenceType - Type of current preference
	 * @property {number[][]} solutionsObjectiveValues - Array of objective value arrays for each solution from EMO
	 * @property {number[][]} solutionsDecisionValues - Array of decision variable arrays for each solution from EMO
	 * @property {function} onSelectSolution - Callback when user selects a solution from the table
	 * @property {number | null} externalSelectedIndex - Optional index of solution to highlight from external source
	 */
	interface Props {
		problem: ProblemInfo | null;
		previousPreferenceValues: number[];
		previousPreferenceType: string;
		currentPreferenceValues: number[];
		currentPreferenceType: string;
		solutionsObjectiveValues?: number[][];
		solutionsDecisionValues?: number[][];
		onSelectSolution?: (index: number) => void;
		externalSelectedIndex?: number | null;
		externalSelectedIndexes?: number[] | null;
	}

	const {
		problem,
		previousPreferenceValues,
		previousPreferenceType,
		currentPreferenceValues,
		currentPreferenceType,
		solutionsObjectiveValues = [],
		solutionsDecisionValues = [],
		onSelectSolution,
		externalSelectedIndex = null,
		externalSelectedIndexes = null,
	}: Props = $props();

	/**
	 * Transform objective values into format expected by ParallelCoordinates
	 * Each solution becomes an object with named properties for each objective
	 */
	const objectiveData = $derived(() => transformObjectiveData(solutionsObjectiveValues, problem));
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
		createReferenceData(currentPreferenceValues, previousPreferenceValues, problem)
	);

	/**
	 * Handle line selection from ParallelCoordinates
	 * Adapts the component's callback to match parent expectations
	 */
	function handleLineSelect(index: number | null, data: any) {
		// Only update internal selectedIndex in single-selection mode
		if (externalSelectedIndexes === null) {
			selectedIndex = index;
		}
    	
		// Notify parent component if callback provided
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
		enableBrushing: false
	};

	// State for line selection and filtering
	// Initialize with external selection if provided, otherwise null
	let selectedIndex = $state<number | null>(externalSelectedIndex !== null ? externalSelectedIndex : null);

	// Update internal selection when external selection changes
	$effect(() => {
		if (externalSelectedIndex !== null) {
			selectedIndex = externalSelectedIndex;
		}
	});

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
	{#if solutionsObjectiveValues.length > 0}
		<!-- Objective Space Visualization with dynamic height -->
		<!-- Use dynamic height that responds to container size -->
		<div class="w-full" style="height: {plotHeight()}px;">
			<ParallelCoordinates
				data={objectiveData()}
				dimensions={objectiveDimensions()}
				referenceData={referenceData()}
				options={plotOptions}
				{selectedIndex}
				multipleSelectedIndexes={externalSelectedIndexes}
				onLineSelect={handleLineSelect}
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
