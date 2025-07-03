<script lang="ts">
	/**
	 * SCOREBands.svelte
	 * --------------------------------
	 * Parallel coordinates visualization with bands, medians, and solutions.
	 *
	 * @author Giomara Larraga <glarragw@jyu.fi>
	 * @created June 2025
	 *
	 * @description
	 * Visualizes multi-objective data as parallel axes, with optional bands (quantiles), medians, and individual solutions.
	 * Supports axis flipping, custom axis order, cluster coloring, and cluster visibility toggling.
	 *
	 * @work-in-progress
	 * This component is a work in progress. Features may change.
	 *
	 * @props
	 * - data: number[][] — rows: solutions, columns: objectives (normalized [0,1])
	 * - axisNames: string[] — names for each axis (objective)
	 * - axisPositions: number[] — normalized horizontal positions for axes (0 to 1)
	 * - axisSigns: number[] — 1 or -1 to flip axis direction
	 * - groups: number[] — cluster/group IDs for each row in data
	 * - options: {
	 *     bands: boolean;      // show quantile bands
	 *     solutions: boolean;  // show individual solutions
	 *     medians: boolean;    // show median line
	 *     quantile: number;    // quantile for bands (e.g., 0.25 for IQR)
	 *   }
	 * - clusterVisibility?: Record<number, boolean> — which clusters are visible
	 * - axisOrder?: number[] — custom axis order (default: [0, 1, 2, ...])
	 *
	 * @features
	 * - Cluster coloring (Tableau10)
	 * - Axis flipping and reordering
	 * - Responsive to prop changes
	 */

	import { onMount } from 'svelte';
	import * as d3 from 'd3';

	// --- Props ---
	export let data: number[][] = [];
	export let axisNames: string[] = [];
	export let axisPositions: number[] = [];
	export let axisSigns: number[] = [];
	export let groups: number[] = [];
	export let options: {
		bands: boolean;
		solutions: boolean;
		medians: boolean;
		quantile: number;
	} = {
		bands: true,
		solutions: true,
		medians: false,
		quantile: 0.5
	};
	export let clusterVisibility: Record<number, boolean> | undefined;
	export let axisOrder: number[] = [];

	// --- Derived state ---
	$: defaultAxisOrder = Array.from({ length: axisNames.length }, (_, i) => i);
	$: effectiveAxisOrder = axisOrder.length === axisNames.length ? axisOrder : defaultAxisOrder;
	$: uniqueClusters = Array.from(new Set(groups));
	$: effectiveClusterVisibility = clusterVisibility
		? clusterVisibility
		: Object.fromEntries(uniqueClusters.map((c) => [c, true]));

	// Sort axis-related arrays according to axisOrder
	$: sortedAxisNames = effectiveAxisOrder.map((i) => axisNames[i]);
	$: sortedAxisPositions = effectiveAxisOrder.map((i) => axisPositions[i]);
	$: sortedAxisSigns = effectiveAxisOrder.map((i) => axisSigns[i]);
	$: sortedData = data.map((row) => effectiveAxisOrder.map((i) => row[i]));

	let container: HTMLDivElement;

	/**
	 * Draws the parallel coordinates chart with bands, medians, and solutions.
	 */
	function drawChart() {
		const width = 800;
		const height = 600;
		const margin = { top: 20, right: 20, bottom: 30, left: 40 };

		// Remove previous SVG if it exists
		d3.select(container).selectAll('svg').remove();
		const svg = d3.select(container).append('svg').attr('width', width).attr('height', height);

		const colorScale = d3.scaleOrdinal(d3.schemeTableau10);
		const numAxes = sortedAxisNames.length;

		// Flip axes and normalize
		const flippedData = sortedData.map((row) => row.map((val, i) => val * sortedAxisSigns[i]));

		// Y scales for each axis (normalized [0,1])
		const yScales = sortedAxisNames.map((_, i) =>
			d3
				.scaleLinear()
				.domain([0, 1])
				.range([height - margin.bottom, margin.top])
		);

		// X positions for each axis
		const xPositions = sortedAxisPositions.map((p) => margin.left + p * (width - 2 * margin.left));

		// --- Draw axis lines and labels ---
		xPositions.forEach((x, i) => {
			svg
				.append('line')
				.attr('x1', x)
				.attr('y1', margin.top)
				.attr('x2', x)
				.attr('y2', height - margin.bottom)
				.attr('stroke', 'black');

			svg
				.append('text')
				.attr('x', x)
				.attr('y', margin.top - 10)
				.attr('text-anchor', 'middle')
				.text(sortedAxisNames[i]);
		});

		// --- Group data by cluster ---
		const grouped = d3.group(
			flippedData.map((v, i) => ({ values: v, group: groups[i] })),
			(d) => d.group
		);

		// --- Draw quantile bands for each cluster ---
		if (options.bands) {
			grouped.forEach((rows, groupId) => {
				if (!effectiveClusterVisibility[groupId]) return;
				const bandData = d3.transpose(rows.map((d) => d.values));
				const low = bandData.map((arr) => d3.quantile(arr, options.quantile)!);
				const high = bandData.map((arr) => d3.quantile(arr, 1 - options.quantile)!);

				const area = d3
					.area<number>()
					.x((_, i) => xPositions[i])
					.y0((_, i) => yScales[i](low[i]))
					.y1((_, i) => yScales[i](high[i]))
					.curve(d3.curveMonotoneX);

				svg
					.append('path')
					.datum(Array(numAxes).fill(0))
					.attr('fill', colorScale(groupId.toString()))
					.attr('opacity', 0.3)
					.attr('d', area);
			});
		}

		// --- Draw median line for each cluster ---
		if (options.medians) {
			grouped.forEach((rows, groupId) => {
				if (!effectiveClusterVisibility[groupId]) return;
				const median = d3.transpose(rows.map((d) => d.values)).map((arr) => d3.median(arr)!);

				const line = d3
					.line<number>()
					.x((_, i) => xPositions[i])
					.y((_, i) => yScales[i](median[i]))
					.curve(d3.curveCatmullRom.alpha(0.5));

				svg
					.append('path')
					.datum(median)
					.attr('fill', 'none')
					.attr('stroke', colorScale(groupId.toString()))
					.attr('stroke-width', 2)
					.attr('d', line);
			});
		}

		// --- Draw individual solutions for each cluster ---
		if (options.solutions) {
			grouped.forEach((rows, groupId) => {
				if (!effectiveClusterVisibility[groupId]) return;
				rows.forEach((d) => {
					const line = d3
						.line<number>()
						.x((_, i) => xPositions[i])
						.y((_, i) => yScales[i](d))
						.curve(d3.curveMonotoneX);

					svg
						.append('path')
						.datum(d.values)
						.attr('fill', 'none')
						.attr('stroke', colorScale(groupId.toString()))
						.attr('stroke-opacity', 0.3)
						.attr('stroke-width', 1)
						.attr('d', line);
				});
			});
		}
	}

	onMount(drawChart);

	// Redraw chart whenever any parameter or cluster visibility or axis order changes
	$: data,
		axisNames,
		axisPositions,
		axisSigns,
		groups,
		options,
		effectiveClusterVisibility,
		effectiveAxisOrder,
		drawChart();
</script>

<!--
    Container for the SCORE bands parallel coordinates visualization.
-->
<div bind:this={container}></div>
