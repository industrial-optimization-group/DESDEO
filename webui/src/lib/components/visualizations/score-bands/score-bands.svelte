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
	 * - data: number[][] — rows: solutions, columns: objectives (any range, will be normalized internally)
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
	 * - clusterColors?: Record<number, string> — colors for each cluster
	 * - axisOptions?: Array<{color?: string; strokeWidth?: number; strokeDasharray?: string}> — styling options for each axis
	 * - axisOrder?: number[] — custom axis order (default: [0, 1, 2, ...])
	 * - onBandSelect?: function — callback when a band is selected
	 * - onAxisSelect?: function — callback when an axis is selected
	 * - selectedBand?: number | null — currently selected band cluster ID
	 * - selectedAxis?: number | null — currently selected axis index
	 *
	 * @features
	 * - Automatic data normalization to [0,1] range
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
	export let clusterColors: Record<number, string> = {};
	export let axisOptions: Array<{
		color?: string;
		strokeWidth?: number;
		strokeDasharray?: string;
	}> = [];
	export let onBandSelect: ((clusterId: number | null) => void) | undefined = undefined;
	export let onAxisSelect: ((axisIndex: number | null) => void) | undefined = undefined;
	export let selectedBand: number | null = null;
	export let selectedAxis: number | null = null;

	// --- Helper function to get cluster color ---
	function getClusterColor(clusterId: number): string {
		return clusterColors[clusterId] || '#999999'; // fallback gray color
	}

	// --- Helper function to get axis color ---
	function getAxisColor(axisIndex: number): string {
		// Get color from axisOptions or use default
		return axisOptions[axisIndex]?.color || '#333333';
	}

	// --- Helper function to get axis style options ---
	function getAxisOptions(axisIndex: number): {
		color: string;
		strokeWidth: number;
		strokeDasharray: string;
	} {
		const options = axisOptions[axisIndex] || {};
		return {
			color: options.color || '#333333',
			strokeWidth: options.strokeWidth || 1,
			strokeDasharray: options.strokeDasharray || 'none'
		};
	}

	// --- Internal normalization function ---
	function normalize_data(input_data: number[][]): number[][] {
		if (input_data.length === 0) return input_data;

		const num_objectives = input_data[0].length;
		const normalized_data: number[][] = [];

		// Find min and max for each objective
		const min_values = new Array(num_objectives).fill(Infinity);
		const max_values = new Array(num_objectives).fill(-Infinity);

		// Calculate min and max for each column
		for (const row of input_data) {
			for (let j = 0; j < num_objectives; j++) {
				min_values[j] = Math.min(min_values[j], row[j]);
				max_values[j] = Math.max(max_values[j], row[j]);
			}
		}

		// Normalize each row
		for (const row of input_data) {
			const normalized_row: number[] = [];
			for (let j = 0; j < num_objectives; j++) {
				const range = max_values[j] - min_values[j];
				if (range === 0) {
					// If all values are the same, set to 0.5
					normalized_row.push(0.5);
				} else {
					const normalized_value = (row[j] - min_values[j]) / range;
					normalized_row.push(normalized_value);
				}
			}
			normalized_data.push(normalized_row);
		}

		return normalized_data;
	}

	// --- Derived state ---
	$: defaultAxisOrder = Array.from({ length: axisNames.length }, (_, i) => i);
	$: effectiveAxisOrder = axisOrder.length === axisNames.length ? axisOrder : defaultAxisOrder;
	$: uniqueClusters = Array.from(new Set(groups));
	$: effectiveClusterVisibility = clusterVisibility
		? clusterVisibility
		: Object.fromEntries(uniqueClusters.map((c) => [c, true]));

	// Normalize data internally
	$: normalizedData = normalize_data(data);

	// Sort axis-related arrays according to axisOrder
	$: sortedAxisNames = effectiveAxisOrder.map((i) => axisNames[i]);
	$: sortedAxisPositions = effectiveAxisOrder.map((i) => axisPositions[i]);
	$: sortedAxisSigns = effectiveAxisOrder.map((i) => axisSigns[i]);
	$: sortedData = normalizedData.map((row) => effectiveAxisOrder.map((i) => row[i]));

	let container: HTMLDivElement;

	/**
	 * Draws the parallel coordinates chart with bands, medians, and solutions.
	 */
	function drawChart() {
		if (!container || data.length === 0 || axisNames.length === 0) return;

		const width = 800;
		const height = 600;
		const margin = { top: 40, right: 40, bottom: 40, left: 40 };

		// Remove previous SVG if it exists
		d3.select(container).selectAll('svg').remove();
		const svg = d3.select(container).append('svg').attr('width', width).attr('height', height);

		// Add background click handler to clear selections
		svg.on('click', () => {
			if (onBandSelect) onBandSelect(null);
			if (onAxisSelect) onAxisSelect(null);
		});

		const numAxes = sortedAxisNames.length;

		// Apply axis signs to flip axes if needed
		const processedData = sortedData.map((row) =>
			row.map((val, i) => {
				const sign = sortedAxisSigns[i] || 1;
				return sign === -1 ? 1 - val : val; // Flip by inverting normalized value
			})
		);

		// Y scales for each axis (normalized [0,1])
		const yScales = sortedAxisNames.map(() =>
			d3
				.scaleLinear()
				.domain([0, 1])
				.range([height - margin.bottom, margin.top])
		);

		// X positions for each axis
		const xPositions = sortedAxisPositions.map(
			(p) => margin.left + p * (width - margin.left - margin.right)
		);

		// --- Group data by cluster ---
		const grouped = d3.group(
			processedData.map((v, i) => ({ values: v, group: groups[i] })),
			(d) => d.group
		);

		// --- Draw quantile bands for each cluster (unselected bands first) ---
		if (options.bands) {
			// First draw unselected bands
			grouped.forEach((rows, groupId) => {
				if (!effectiveClusterVisibility[groupId] || selectedBand === groupId) return;

				const bandData = d3.transpose(rows.map((d) => d.values));
				const low = bandData.map((arr) => d3.quantile(arr.sort(d3.ascending), options.quantile)!);
				const high = bandData.map(
					(arr) => d3.quantile(arr.sort(d3.ascending), 1 - options.quantile)!
				);

				const area = d3
					.area<number>()
					.x((_, i) => xPositions[i])
					.y0((_, i) => yScales[i](low[i]))
					.y1((_, i) => yScales[i](high[i]))
					.curve(d3.curveMonotoneX);

				const bandElement = svg
					.append('path')
					.datum(Array(numAxes).fill(0))
					.attr('fill', getClusterColor(groupId))
					.attr('opacity', 0.5)
					.attr('stroke', 'none')
					.attr('stroke-width', 0)
					.attr('d', area)
					.style('cursor', 'pointer');

				// Add click handler for band selection
				if (onBandSelect) {
					bandElement.on('click', (event) => {
						event.stopPropagation();
						const newSelection = selectedBand === groupId ? null : groupId;
						onBandSelect(newSelection);
					});
				}
			});

			// Then draw selected band in front of other bands
			if (selectedBand !== null && effectiveClusterVisibility[selectedBand]) {
				const selectedRows = grouped.get(selectedBand);
				if (selectedRows) {
					const bandData = d3.transpose(selectedRows.map((d) => d.values));
					const low = bandData.map((arr) => d3.quantile(arr.sort(d3.ascending), options.quantile)!);
					const high = bandData.map(
						(arr) => d3.quantile(arr.sort(d3.ascending), 1 - options.quantile)!
					);

					const area = d3
						.area<number>()
						.x((_, i) => xPositions[i])
						.y0((_, i) => yScales[i](low[i]))
						.y1((_, i) => yScales[i](high[i]))
						.curve(d3.curveMonotoneX);

					const selectedBandElement = svg
						.append('path')
						.datum(Array(numAxes).fill(0))
						.attr('fill', getClusterColor(selectedBand))
						.attr('opacity', 0.7)
						.attr('stroke', '#000')
						.attr('stroke-width', 2)
						.attr('d', area)
						.style('cursor', 'pointer');

					// Add click handler for selected band
					if (onBandSelect) {
						selectedBandElement.on('click', (event) => {
							event.stopPropagation();
							onBandSelect(null);
						});
					}
				}
			}
		}

		// --- Draw median line for each cluster (after bands, before axes) ---
		if (options.medians) {
			grouped.forEach((rows, groupId) => {
				if (!effectiveClusterVisibility[groupId]) return;

				const medians = d3
					.transpose(rows.map((d) => d.values))
					.map((arr) => d3.median(arr.sort(d3.ascending))!);

				const line = d3
					.line<number>()
					.x((_, i) => xPositions[i])
					.y((_, i) => yScales[i](medians[i]))
					.curve(d3.curveMonotoneX);

				svg
					.append('path')
					.datum(medians)
					.attr('fill', 'none')
					.attr('stroke', getClusterColor(groupId))
					.attr('stroke-width', 3)
					.attr('opacity', 0.8)
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
						.y((val, i) => yScales[i](val))
						.curve(d3.curveMonotoneX);

					svg
						.append('path')
						.datum(d.values)
						.attr('fill', 'none')
						.attr('stroke', getClusterColor(groupId))
						.attr('stroke-opacity', 0.4)
						.attr('stroke-width', 1)
						.attr('d', line);
				});
			});
		}

		// --- Draw axis lines and labels (always in front) ---
		xPositions.forEach((x, sortedIndex) => {
			const originalAxisIndex = effectiveAxisOrder[sortedIndex];
			const isSelected = selectedAxis === originalAxisIndex;
			const axisStyle = getAxisOptions(originalAxisIndex);

			// Axis line
			const axisLine = svg
				.append('line')
				.attr('x1', x)
				.attr('y1', margin.top)
				.attr('x2', x)
				.attr('y2', height - margin.bottom)
				.attr('stroke', isSelected ? '#e15759' : axisStyle.color)
				.attr('stroke-width', isSelected ? 3 : axisStyle.strokeWidth)
				.attr('stroke-dasharray', isSelected ? 'none' : axisStyle.strokeDasharray)
				.style('cursor', 'pointer');

			// Add click handler for axis selection
			if (onAxisSelect) {
				axisLine.on('click', (event) => {
					event.stopPropagation();
					const newSelection = selectedAxis === originalAxisIndex ? null : originalAxisIndex;
					onAxisSelect(newSelection);
				});
			}

			// Axis label
			const axisLabel = svg
				.append('text')
				.attr('x', x)
				.attr('y', margin.top - 10)
				.attr('text-anchor', 'middle')
				.attr('font-size', '12px')
				.attr('font-weight', isSelected ? 'bold' : 'bold')
				.attr('fill', isSelected ? '#e15759' : axisStyle.color)
				.text(sortedAxisNames[sortedIndex])
				.style('cursor', 'pointer');

			// Add click handler for axis label selection
			if (onAxisSelect) {
				axisLabel.on('click', (event) => {
					event.stopPropagation();
					const newSelection = selectedAxis === originalAxisIndex ? null : originalAxisIndex;
					onAxisSelect(newSelection);
				});
			}

			// Add tick marks and labels
			const tickValues = [0, 0.25, 0.5, 0.75, 1];
			tickValues.forEach((tick) => {
				const yPos = yScales[sortedIndex](tick);

				// Adjust tick label based on axis sign
				const sign = sortedAxisSigns[sortedIndex] || 1;
				const displayValue = sign === -1 ? 1 - tick : tick;

				// Tick mark
				svg
					.append('line')
					.attr('x1', x - 5)
					.attr('y1', yPos)
					.attr('x2', x + 5)
					.attr('y2', yPos)
					.attr('stroke', '#666')
					.attr('stroke-width', 1);

				// Tick label (adjusted for axis direction)
				svg
					.append('text')
					.attr('x', x + 10)
					.attr('y', yPos + 3)
					.attr('font-size', '10px')
					.attr('fill', '#666')
					.text(displayValue.toFixed(2));
			});
		});
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
		selectedBand,
		selectedAxis,
		axisOptions,
		drawChart();
</script>

<!--
    Container for the SCORE bands parallel coordinates visualization.
-->
<div bind:this={container} class="flex h-full w-full items-center justify-center"></div>

<style>
	div {
		min-height: 400px;
	}
</style>
