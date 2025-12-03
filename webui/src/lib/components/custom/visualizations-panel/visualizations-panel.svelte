<script lang="ts">
	/**
	 * Visualizations Panel Component
	 *
	 * @author Giomara Larraga <glarragw@jyu.fi>
	 * @author Stina Palomäki <palomakistina@gmail.com> (Enhancements & GNIMBUS support)
	 * @created July 2025
	 * @updated November 2025
	 *
	 * @description
	 * A versatile visualization panel for multi-objective optimization solutions in DESDEO.
	 * Will provide different visualization types (Parallel Coordinates, Bar Chart) for exploring TODO: Bar Chart
	 * solution spaces and comparing different solutions against preferences.
	 *
	 * @data_flow
	 * 1. Parent component (EMO/NIMBUS page etc.) performs optimization iteration
	 * 2. The corresponding method returns solutions with objective values, decision values, constraint values, etc.
	 * 3. Parent passes data to this component
	 * 4. Component transforms data for appropriate visualization format
	 * 5. User interacts with visualizations (selecting solutions, filtering)
	 * 6. Selected solutions are passed back to parent via onSelectSolution callback
	 *
	 * @props
	 * @property {ProblemInfo | null} problem - The optimization problem definition
	 * @property {number[][]} [previousPreferenceValues] - Previous iteration's preference values
	 * @property {string} previousPreferenceType - Type of previous preference (e.g., 'reference_point')
	 * @property {number[]} [currentPreferenceValues] - Current iteration's preference values
	 * @property {string} currentPreferenceType - Type of current preference
	 * @property {number[][]} [previousObjectiveValues] - Previous objective values for comparison
	 * @property {number[][]} [otherObjectiveValues] - Additional objective values (e.g., other users' solutions)
	 * @property {number[][]} [solutionsObjectiveValues] - Array of objective values for each solution
	 * @property {number[][]} [solutionsDecisionValues] - Array of decision variable values for each solution
	 * @property {function} [onSelectSolution] - Callback when user selects a solution
	 * @property {number | null} [externalSelectedIndex] - Index of solution to highlight (single-select mode)
	 * @property {number[] | null} [externalSelectedIndexes] - Indexes of solutions to highlight (multi-select mode)
	 * @property {{ [key: string]: string }} [lineLabels] - Custom labels for solution lines displayed in tooltips
	 * @property {{ currentRefLabel?: string, previousRefLabel?: string, previousSolutionLabels?: string[], otherSolutionLabels?: string[] }} [referenceDataLabels] - Labels for reference points and solutions
	 *
	 * @features
	 * - Visualization type selector (Parallel Coordinates/Bar Chart toggle), hidden until Bar Chart is implemented
	 * - Dynamic resizing to fit container
	 * - Solution selection with parent component synchronization
	 * - Reference point visualization
	 * - Previous solution comparison
	 * - Empty state handling
	 * - Interactive tooltips with customizable labels for solutions and reference points
	 * 
	 * @dependencies
	 * - ParallelCoordinates component for the core visualization
	 * - SegmentedControl for visualization type selection (prepared for future bar charts)
	 * - Helper functions for data transformation and reference data creation
	 * - ResizeObserver for responsive container monitoring
	 *
	 * @responsive_design
	 * - Automatically adjusts visualization height based on container size
	 * - Reserves space for controls and maintains usable visualization area
	 * - Handles container resize events for optimal display
	 */

	import type { components } from '$lib/api/client-types';
	import ParallelCoordinates from '$lib/components/visualizations/parallel-coordinates/parallel-coordinates.svelte';
	import { createReferenceData } from '$lib/helpers/preference-data-transforms';
	import {
		createObjectiveDimensions,
		transformObjectiveData
	} from '$lib/helpers/visualization-data-transform';
	import { onMount } from 'svelte';
	import { SegmentedControl } from '$lib/components/custom/segmented-control';

	// Type definitions from OpenAPI schema
	type ProblemInfo = components['schemas']['ProblemInfo'];

	/**
	 * Component Props Interface
	 *
	 * @interface Props
	 * @property {ProblemInfo | null} problem - The optimization problem definition including objectives, variables, and constraints
	 * @property {number[][]} previous_preference_values - Previous iteration's preference values for comparison
	 * @property {string} previous_preference_type - Type of previous preference (reference_point, preferred_solution, etc.)
	 * @property {number[]} currentPreferenceValues - Current iteration's preference values
	 * @property {string} currentPreferenceType - Type of current preference
	 * @property {number[][]} previousObjectiveValues - Optional previous objective values for comparison
	 * @property {number[][]} solutionsObjectiveValues - Array of objective value arrays for each solution from EMO
	 * @property {number[][]} solutionsDecisionValues - Array of decision variable arrays for each solution from EMO
	 * @property {function} onSelectSolution - Callback when user selects a solution from the table
	 * @property {number | null} externalSelectedIndex - Optional index of solution to highlight from external source
	 */
	interface Props {
		problem: ProblemInfo | null;
		previousPreferenceValues?: number[][];
		previousObjectiveValues?: number[][];
		otherObjectiveValues?: number[][]; // New prop for additional objective values
		currentPreferenceValues?: number[];
		previousPreferenceType: string;
		currentPreferenceType: string;
		solutionsObjectiveValues?: number[][];
		solutionsDecisionValues?: number[][];
		onSelectSolution?: (index: number) => void;
		externalSelectedIndex?: number | null;
		externalSelectedIndexes?: number[] | null;
		// Labels for different types of solutions
		lineLabels?: { [key: string]: string };
		referenceDataLabels?: {
			currentRefLabel?: string;
			previousRefLabel?: string;
			previousSolutionLabels?: string[];
			otherSolutionLabels?: string[];
		};
	}

	const {
		problem,
		previousPreferenceValues = [],
		previousObjectiveValues,
		otherObjectiveValues,
		currentPreferenceValues = [],
		previousPreferenceType,
		currentPreferenceType,
		solutionsObjectiveValues = [],
		solutionsDecisionValues = [],
		onSelectSolution,
		externalSelectedIndex = null,
		externalSelectedIndexes = null,
		lineLabels = {},
		referenceDataLabels = {}
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
		{
			let data = createReferenceData(
			currentPreferenceValues,
			previousPreferenceValues,
			problem,
			previousObjectiveValues,
			otherObjectiveValues,
			referenceDataLabels
		)
		data ? data.preferredRanges = undefined : ()=> []; // Disable preferred ranges display
		return data;
		}
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
		opacity: 1,
		enableBrushing: false
	};

	// State for line selection and filtering
	// Initialize with external selection if provided, otherwise null
	let selectedIndex = $state<number | null>(
		externalSelectedIndex !== null ? externalSelectedIndex : null
	);

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

	// Visualization type enum
	type VisualizationType = 'parallel' | 'bar';

	// Current visualization type state
	let visualizationType = $state<VisualizationType>('parallel');

	// Calculate dynamic height for visualizations
	const plotHeight = $derived(() => {
		// Reserve space for header with visualization selector, instructions, and table
		const reservedSpace = 50; // Increased to accommodate the visualization selector, adjust based on your layout, maybe a prop? TODO
		return Math.max(containerSize.height - reservedSpace, 10);
	});
</script>

<!-- 
/**
 * Component Template
 * 
 * The visualization components handle their own internal resizing,
 * so we provide a container with appropriate dimensions and selector controls.
 */
-->

<div bind:this={containerElement} class="flex h-full w-full flex-col space-y-4 overflow-hidden">
	{#if solutionsObjectiveValues.length > 0}
		<!-- Visualization Type Selector -->
		<div class="mb-2 flex items-center justify-between">
			<h3>Visualization</h3>
			<SegmentedControl
				bind:value={visualizationType}
				options={[
					{ value: 'parallel', label: 'Parallel Coordinates' },
					{ value: 'bar', label: 'Bar Chart' }
				]}
				class="justify-end invisible" 
			/> <!--To implement the bar chart, remove the invisible class above and add the visualization below-->
		</div>

		<!-- Visualization Container with dynamic height -->
		<div class="w-full border-t border-gray-200" style="height: {plotHeight()}px;">
			{#if visualizationType === 'parallel'}
				<ParallelCoordinates
					data={objectiveData()}
					dimensions={objectiveDimensions()}
					referenceData={referenceData()}
					options={plotOptions}
					{selectedIndex}
					multipleSelectedIndexes={externalSelectedIndexes}
					onLineSelect={handleLineSelect}
					{lineLabels}
				/>
			{:else if visualizationType === 'bar'}
				<!-- Placeholder for Bar Chart Visualization -->
				<div class="flex h-full items-center justify-center bg-gray-50 text-gray-500">
					<div class="text-center">
						<p>Bar Chart visualization coming soon</p>
						<p class="mt-2 text-sm">This will display objective values as interactive bar charts</p>
					</div>
				</div>
			{/if}
		</div>
	{:else}
		<div
			class="flex h-full items-center justify-center rounded border bg-gray-50 p-8 text-center text-gray-500"
		>
			No solutions available. Run the optimization to see results.
		</div>
	{/if}
</div>
