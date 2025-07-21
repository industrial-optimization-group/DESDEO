<script lang="ts">
	/**
	 * Barchart.svelte
	 * --------------------------------
	 * Responsive bar chart component using D3.
	 *
	 * @author Giomara Larraga <glarragw@jyu.fi>
	 * @created June 2025
	 *
	 * @description
	 * Renders a responsive bar chart using D3.js.
	 * Supports both horizontal and vertical orientations, with customizable data ranges and colors.
	 *
	 * @props
	 * - data: Array<{ name: string; value: number; direction: 'max' | 'min' }>
	 *   - name: string — label for the bar
	 *   - value: number — value for the bar
	 *   - direction: 'max' | 'min' — if 'max', bar grows from axis min; if 'min', bar grows from axis max
	 * - axisRanges: Array<[number, number]>
	 *   - If provided and length === data.length, each bar uses its own range for normalization
	 * - options: {
	 *     showLabels: boolean; // show value labels on bars
	 *     orientation: 'horizontal' | 'vertical'; // chart orientation
	 *   }
	 *
	 * @features
	 * - Horizontal and vertical bar chart support
	 * - Each bar can have a different value range (axisRanges)
	 * - Custom color palette
	 * - Responsive to container size (ResizeObserver)
	 * - Optionally shows value labels
	 *
	 * @notes
	 * - TODO: Normalize data values based on axisRanges if provided.
	 * - TODO: Option to show multiple axes with different ranges.
	 * - TODO: Option to show min and max values for each bar.
	 */

	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import { COLOR_PALETTE } from '../utils/colors';
	import { normalize, getValueRange } from '../utils/math';

	// --- Props ---
	export let data: { name: string; value: number; direction: 'max' | 'min' }[] = [];
	export let axisRanges: [number, number][] = [];
	export let options: { showLabels: boolean } = {
		showLabels: true
	};

	// --- Internal state ---
	let width = 500;
	let height = 400;
	let svg: SVGSVGElement;
	let container: HTMLDivElement;
	let resizeObserver: ResizeObserver;

	/**
	 * Draws the bar chart (horizontal or vertical) using D3.
	 */
	function drawChart(): void {}

	// --- Responsive: update chart on container resize ---
	onMount(() => {
		resizeObserver = new ResizeObserver((entries) => {
			for (const entry of entries) {
				const rect = entry.contentRect;
				width = rect.width;
				height = rect.height;
				drawChart();
			}
		});
		resizeObserver.observe(container);
		drawChart();
	});
	onDestroy(() => {
		resizeObserver.disconnect();
	});

	// --- Redraw chart on data/options/size change ---
	$: data, options, width, height, axisRanges, drawChart();
</script>

<!--
    Responsive container for the bar chart.
    Aspect ratio is fixed to 5:4 for now.
-->
<div bind:this={container} style="aspect-ratio: 5 / 4; width: 100%;">
	<svg bind:this={svg} style="width: 100%; height: 100%;" />
</div>
