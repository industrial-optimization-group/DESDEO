<script module>
	import { defineMeta } from '@storybook/addon-svelte-csf';
	import ParallelCoordinates from '$lib/components/visualizations/parallel-coordinates/parallel-coordinates.svelte';

	const { Story } = defineMeta({
		title: 'Visualizations/ParallelCoordinates',
		component: ParallelCoordinates,
		tags: ['autodocs'],
		argTypes: {
			data: {
				control: 'object',
				description: 'Array of data points where each object has values for each dimension'
			},
			dimensions: {
				control: 'object',
				description: 'Array of dimension definitions with name, min, max, and direction'
			},
			referenceData: {
				control: 'object',
				description:
					'Optional reference data including reference points, ranges, and preferred solutions'
			},
			options: {
				control: 'object',
				description: 'Chart options for labels, hover, stroke width, opacity, and brushing'
			},
			selectedIndex: {
				control: 'number',
				description: 'Index of selected line (only one at a time, null for none)'
			},
			brushFilters: {
				control: 'object',
				description: 'Object with active brush filter ranges for each dimension'
			},
			onLineSelect: {
				action: 'lineSelected',
				description: 'Callback when a line is selected/deselected'
			},
			onBrushFilter: {
				action: 'brushFiltered',
				description: 'Callback when brush filters change'
			}
		},
		args: {
			data: [
				{ f1: 0.2, f2: 0.8, f3: 0.5, f4: 0.3 },
				{ f1: 0.7, f2: 0.3, f3: 0.9, f4: 0.1 },
				{ f1: 0.4, f2: 0.6, f3: 0.2, f4: 0.8 },
				{ f1: 0.1, f2: 0.9, f3: 0.7, f4: 0.5 },
				{ f1: 0.6, f2: 0.4, f3: 0.3, f4: 0.9 }
			],
			dimensions: [
				{ name: 'f1', min: 0, max: 1, direction: 'min' },
				{ name: 'f2', min: 0, max: 1, direction: 'max' },
				{ name: 'f3', min: 0, max: 1, direction: 'min' },
				{ name: 'f4', min: 0, max: 1, direction: 'max' }
			],
			options: {
				showAxisLabels: true,
				highlightOnHover: true,
				strokeWidth: 2,
				opacity: 0.7,
				enableBrushing: true
			},
			selectedIndex: null,
			brushFilters: {},
			referenceData: undefined
		}
	});
</script>

<!-- Default story - Perfect for testing brushing -->
<Story name="Default" let:args>
	<div style="padding: 20px;">
		<h3>Interactive Brushing Test</h3>
		<p>Try dragging vertically on any axis to create brush filters. Click lines to select them.</p>
		<ParallelCoordinates {...args} />
	</div>
</Story>

<!-- Story with line selection -->
<Story
	name="With Selected Line"
	args={{
		selectedIndex: 0,
		options: {
			showAxisLabels: true,
			highlightOnHover: true,
			strokeWidth: 2,
			opacity: 0.6,
			enableBrushing: true
		}
	}}
/>

<!-- Story with brushing disabled for comparison -->
<Story
	name="Brushing Disabled"
	args={{
		selectedIndex: 2,
		options: {
			showAxisLabels: true,
			highlightOnHover: true,
			strokeWidth: 2,
			opacity: 0.8,
			enableBrushing: false
		}
	}}
>
	<div style="padding: 20px;">
		<h3>No Brushing</h3>
		<p>This version has brushing disabled. You can only click to select lines.</p>
		<ParallelCoordinates {...args} />
	</div>
</Story>

<!-- Story with more data for better brushing demonstration -->
<Story
	name="Rich Dataset for Brushing"
	args={{
		data: [
			{ cost: 120, time: 45, quality: 0.8, reliability: 0.9 },
			{ cost: 80, time: 60, quality: 0.6, reliability: 0.7 },
			{ cost: 150, time: 30, quality: 0.9, reliability: 0.95 },
			{ cost: 100, time: 50, quality: 0.7, reliability: 0.8 },
			{ cost: 90, time: 55, quality: 0.75, reliability: 0.85 },
			{ cost: 130, time: 35, quality: 0.85, reliability: 0.9 },
			{ cost: 70, time: 65, quality: 0.65, reliability: 0.75 },
			{ cost: 160, time: 25, quality: 0.95, reliability: 0.98 },
			{ cost: 110, time: 40, quality: 0.8, reliability: 0.88 },
			{ cost: 95, time: 52, quality: 0.72, reliability: 0.82 }
		],
		dimensions: [
			{ name: 'cost', min: 50, max: 200, direction: 'min' },
			{ name: 'time', min: 20, max: 80, direction: 'min' },
			{ name: 'quality', min: 0.5, max: 1, direction: 'max' },
			{ name: 'reliability', min: 0.6, max: 1, direction: 'max' }
		],
		referenceData: {
			referencePoint: { cost: 100, time: 40, quality: 0.8, reliability: 0.85 }
		},
		selectedIndex: null,
		brushFilters: {},
		options: {
			showAxisLabels: true,
			highlightOnHover: true,
			strokeWidth: 2,
			opacity: 0.7,
			enableBrushing: true
		}
	}}
	let:args
>
	<div style="padding: 20px;">
		<h3>Multi-Objective Optimization Example</h3>
		<p><strong>Instructions:</strong></p>
		<ul>
			<li>Drag vertically on the <strong>cost</strong> axis to filter by cost range</li>
			<li>Drag on the <strong>quality</strong> axis to filter by quality range</li>
			<li>Try filtering on multiple axes simultaneously</li>
			<li>Click any visible line to select it</li>
		</ul>
		<ParallelCoordinates {...args} />
	</div>
</Story>

<!-- Story with reference data -->
<Story
	name="With Reference Point"
	args={{
		referenceData: {
			referencePoint: { f1: 0.3, f2: 0.7, f3: 0.4, f4: 0.6 }
		},
		selectedIndex: 1,
		options: {
			showAxisLabels: true,
			highlightOnHover: true,
			strokeWidth: 2,
			opacity: 0.8,
			enableBrushing: true
		}
	}}
/>

<!-- Story with preferred ranges -->
<Story
	name="With Preferred Ranges"
	args={{
		referenceData: {
			preferredRanges: {
				f1: { min: 0.1, max: 0.4 },
				f2: { min: 0.6, max: 0.9 },
				f3: { min: 0.2, max: 0.5 },
				f4: { min: 0.3, max: 0.7 }
			}
		},
		selectedIndex: 0,
		options: {
			showAxisLabels: true,
			highlightOnHover: true,
			strokeWidth: 2,
			opacity: 0.7,
			enableBrushing: true
		}
	}}
/>

<!-- Story with preferred and non-preferred solutions -->
<Story
	name="With Preferred Solutions"
	args={{
		referenceData: {
			preferredSolutions: [
				{ f1: 0.25, f2: 0.75, f3: 0.35, f4: 0.65 },
				{ f1: 0.15, f2: 0.85, f3: 0.25, f4: 0.55 }
			],
			nonPreferredSolutions: [{ f1: 0.8, f2: 0.2, f3: 0.9, f4: 0.1 }]
		},
		selectedIndex: 2,
		options: {
			showAxisLabels: true,
			highlightOnHover: true,
			strokeWidth: 2,
			opacity: 0.6,
			enableBrushing: true
		}
	}}
/>

<!-- Story with all reference data types -->
<Story
	name="Complete Reference Data"
	args={{
		data: [
			{ f1: 0.2, f2: 0.8, f3: 0.5, f4: 0.3 },
			{ f1: 0.7, f2: 0.3, f3: 0.9, f4: 0.1 },
			{ f1: 0.4, f2: 0.6, f3: 0.2, f4: 0.8 },
			{ f1: 0.1, f2: 0.9, f3: 0.7, f4: 0.5 },
			{ f1: 0.6, f2: 0.4, f3: 0.3, f4: 0.9 },
			{ f1: 0.3, f2: 0.7, f3: 0.4, f4: 0.6 }
		],
		referenceData: {
			referencePoint: { f1: 0.3, f2: 0.7, f3: 0.4, f4: 0.6 },
			preferredRanges: {
				f1: { min: 0.1, max: 0.4 },
				f2: { min: 0.6, max: 0.9 },
				f4: { min: 0.5, max: 0.8 }
			},
			preferredSolutions: [{ f1: 0.25, f2: 0.75, f3: 0.35, f4: 0.65 }],
			nonPreferredSolutions: [{ f1: 0.8, f2: 0.2, f3: 0.9, f4: 0.1 }]
		},
		selectedIndex: 0,
		options: {
			showAxisLabels: true,
			highlightOnHover: true,
			strokeWidth: 2,
			opacity: 0.7,
			enableBrushing: true
		}
	}}
/>

<!-- Story with many solutions for performance testing -->
<Story
	name="Many Solutions"
	args={{
		data: Array.from({ length: 50 }, (_, i) => ({
			f1: Math.random(),
			f2: Math.random(),
			f3: Math.random(),
			f4: Math.random()
		})),
		dimensions: [
			{ name: 'f1', min: 0, max: 1, direction: 'min' },
			{ name: 'f2', min: 0, max: 1, direction: 'max' },
			{ name: 'f3', min: 0, max: 1, direction: 'min' },
			{ name: 'f4', min: 0, max: 1, direction: 'max' }
		],
		referenceData: {
			referencePoint: { f1: 0.3, f2: 0.7, f3: 0.4, f4: 0.6 },
			preferredRanges: {
				f1: { min: 0.2, max: 0.5 },
				f2: { min: 0.5, max: 0.8 }
			}
		},
		selectedIndex: 5,
		brushFilters: {},
		options: {
			showAxisLabels: true,
			highlightOnHover: true,
			strokeWidth: 1,
			opacity: 0.5,
			enableBrushing: true
		}
	}}
/>

<!-- Interactive story for testing brushing -->
<Story
	name="Interactive Brushing Demo"
	args={{
		data: [
			{ cost: 120, time: 45, quality: 0.8, reliability: 0.9 },
			{ cost: 80, time: 60, quality: 0.6, reliability: 0.7 },
			{ cost: 150, time: 30, quality: 0.9, reliability: 0.95 },
			{ cost: 100, time: 50, quality: 0.7, reliability: 0.8 },
			{ cost: 90, time: 55, quality: 0.75, reliability: 0.85 },
			{ cost: 130, time: 35, quality: 0.85, reliability: 0.9 }
		],
		dimensions: [
			{ name: 'cost', min: 50, max: 200, direction: 'min' },
			{ name: 'time', min: 20, max: 80, direction: 'min' },
			{ name: 'quality', min: 0.5, max: 1, direction: 'max' },
			{ name: 'reliability', min: 0.6, max: 1, direction: 'max' }
		],
		referenceData: {
			referencePoint: { cost: 100, time: 40, quality: 0.8, reliability: 0.85 }
		},
		selectedIndex: null,
		brushFilters: {},
		options: {
			showAxisLabels: true,
			highlightOnHover: true,
			strokeWidth: 2,
			opacity: 0.7,
			enableBrushing: true
		}
	}}
/>

<!-- Story with all features combined -->
<Story
	name="Complete Example"
	args={{
		data: [
			{ f1: 0.2, f2: 0.8, f3: 0.5, f4: 0.3 },
			{ f1: 0.7, f2: 0.3, f3: 0.9, f4: 0.1 },
			{ f1: 0.4, f2: 0.6, f3: 0.2, f4: 0.8 },
			{ f1: 0.1, f2: 0.9, f3: 0.7, f4: 0.5 },
			{ f1: 0.6, f2: 0.4, f3: 0.3, f4: 0.9 },
			{ f1: 0.3, f2: 0.7, f3: 0.4, f4: 0.6 },
			{ f1: 0.8, f2: 0.2, f3: 0.6, f4: 0.4 },
			{ f1: 0.5, f2: 0.5, f3: 0.8, f4: 0.2 }
		],
		referenceData: {
			referencePoint: { f1: 0.3, f2: 0.7, f3: 0.4, f4: 0.6 },
			preferredRanges: {
				f1: { min: 0.1, max: 0.4 },
				f2: { min: 0.6, max: 0.9 }
			},
			preferredSolutions: [{ f1: 0.25, f2: 0.75, f3: 0.35, f4: 0.65 }],
			nonPreferredSolutions: [{ f1: 0.8, f2: 0.2, f3: 0.9, f4: 0.1 }]
		},
		selectedIndex: 0,
		brushFilters: {},
		options: {
			showAxisLabels: true,
			highlightOnHover: true,
			strokeWidth: 2,
			opacity: 0.7,
			enableBrushing: true
		}
	}}
	let:args
>
	<div style="padding: 20px;">
		<h3>Complete Feature Demonstration</h3>
		<p>
			This story shows all features: reference points, preferred ranges, preferred/non-preferred
			solutions, selection, and brushing.
		</p>
		<ParallelCoordinates {...args} />
	</div>
</Story>
