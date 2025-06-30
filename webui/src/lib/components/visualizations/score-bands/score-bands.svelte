<script lang="ts">
	import { onMount } from 'svelte';
	import * as d3 from 'd3';
	// List of objective vectors (rows: solutions, columns: objectives)
	export let data: number[][] = [];

	// Names for each axis (objectives)
	export let axisNames: string[] = [];

	// Normalized horizontal positions for axes (0 to 1)
	export let axisPositions: number[] = [];

	// 1 or -1 to flip an axis direction
	export let axisSigns: number[] = [];

	// Cluster/group IDs for each row in data
	export let groups: number[] = [];

	// Options for rendering
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

	// New: clusterVisibility parameter (Record<number, boolean>)
	// If not provided, all clusters are visible by default
	export let clusterVisibility: Record<number, boolean> | undefined;

	// New: axisOrder parameter (default: [0, 1, 2, ...])
	export let axisOrder: number[] = [];
	$: defaultAxisOrder = Array.from({ length: axisNames.length }, (_, i) => i);
	$: effectiveAxisOrder = axisOrder.length === axisNames.length ? axisOrder : defaultAxisOrder;

	// Compute unique clusters
	$: uniqueClusters = Array.from(new Set(groups));

	// If clusterVisibility is not provided, show all clusters by default
	$: effectiveClusterVisibility = clusterVisibility
		? clusterVisibility
		: Object.fromEntries(uniqueClusters.map((c) => [c, true]));

	let container: HTMLDivElement;

	// Sort data and axis-related arrays according to axisOrder
	$: sortedAxisNames = effectiveAxisOrder.map((i) => axisNames[i]);
	$: sortedAxisPositions = effectiveAxisOrder.map((i) => axisPositions[i]);
	$: sortedAxisSigns = effectiveAxisOrder.map((i) => axisSigns[i]);
	$: sortedData = data.map((row) => effectiveAxisOrder.map((i) => row[i]));

	function drawChart() {
		const width = 800; // Width of the chart
		const height = 600; // Height of the chart
		const margin = { top: 20, right: 20, bottom: 30, left: 40 };
		// Remove previous SVG if it exists
		d3.select(container).selectAll('svg').remove();
		const svg = d3.select(container).append('svg').attr('width', width).attr('height', height);
		// Create scales for axes
		const colorScale = d3.scaleOrdinal(d3.schemeTableau10);
		const numAxes = sortedAxisNames.length;

		// Flip axes and normalize
		const flippedData = sortedData.map((row) => row.map((val, i) => val * sortedAxisSigns[i]));

		const yScales = sortedAxisNames.map((_, i) =>
			d3
				.scaleLinear()
				.domain([0, 1])
				.range([height - margin.bottom, margin.top])
		);

		const xPositions = sortedAxisPositions.map((p) => margin.left + p * (width - 2 * margin.left));

		// Draw axis lines
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

		// Group data by cluster
		const grouped = d3.group(
			flippedData.map((v, i) => ({ values: v, group: groups[i] })),
			(d) => d.group
		);

		// Draw bands
		if (options.bands) {
			grouped.forEach((rows, groupId) => {
				if (!effectiveClusterVisibility[groupId]) return; // Only draw if visible
				const bandData = d3.transpose(rows.map((d) => d.values));

				const low = bandData.map((arr) => d3.quantile(arr, options.quantile)!);
				const high = bandData.map((arr) => d3.quantile(arr, 1 - options.quantile)!);

				const area = d3
					.area<number>()
					.x((_, i) => xPositions[i])
					.y0((d, i) => yScales[i](low[i]))
					.y1((d, i) => yScales[i](high[i]))
					.curve(d3.curveMonotoneX);

				svg
					.append('path')
					.datum(Array(numAxes).fill(0))
					.attr('fill', colorScale(groupId.toString()))
					.attr('opacity', 0.3)
					.attr('d', area);
			});
		}

		// Draw medians
		if (options.medians) {
			grouped.forEach((rows, groupId) => {
				if (!effectiveClusterVisibility[groupId]) return; // Only draw if visible
				const median = d3.transpose(rows.map((d) => d.values)).map((arr) => d3.median(arr)!);

				const line = d3
					.line<number>()
					.x((_, i) => xPositions[i])
					.y((d, i) => yScales[i](median[i]))
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

		// Draw individual solutions
		if (options.solutions) {
			grouped.forEach((rows, groupId) => {
				if (!effectiveClusterVisibility[groupId]) return; // Only draw if visible
				rows.forEach((d) => {
					const line = d3
						.line<number>()
						.x((_, i) => xPositions[i])
						.y((d, i) => yScales[i](d))
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

<div bind:this={container}></div>
