<script lang="ts">
	/**
	 * SCOREBands.svelte
	 * --------------------------------
	 * Parallel coordinates visualization for SCORE-bands method.
	 *
	 * @author Giomara Larraga <glarragw@jyu.fi>, Stina Palomäki <palomakistina@gmail.com> (modifications)
	 * @created June 2025
	 * @modified December 2025
	 *
	 * @description
	 * Visualizes SCORE-bands data using pre-calculated bands and medians from API.
	 * Supports cluster selection, axis styling, and cluster visibility controls.
	 *
	 * @current-implementation
	 * Uses pre-calculated bands/medians from SCORE API (raw data processing commented out).
	 *
	 * @props
	 * - bands: Record<string, Record<string, [number, number]>> — pre-calculated band limits
	 * - medians: Record<string, Record<string, number>> — pre-calculated median values
	 * - scales: Record<string, [number, number]> — normalization scales
	 * - axisNames: string[] — axis labels
	 * - axisPositions: number[] — axis positions (0-1)
	 * - clusterVisibility: Record<number, boolean> — cluster visibility
	 * - clusterColors: Record<number, string> — cluster colors
	 * - selectedBand: number | null — selected cluster ID
	 * - onBandSelect: function — band selection callback
	 *
	 * @features
	 * - Pre-calculated band visualization
	 * - Cluster selection and highlighting
	 * - Axis styling and labeling
	 * - Responsive cluster visibility
	 */

	import { onMount } from 'svelte';
	import * as d3 from 'd3';
	import { normalize_data } from '$lib/components/visualizations/utils/math';
	import type { AxisOptions } from './utils/types';
	import { getAxisOptions } from './utils/helpers';
	import { drawPreCalculatedCluster } from './components/band';

	// --- Props ---
	export let data: number[][] = []; // not used, kept in case future happens
	export let axisNames: string[] = [];
	export let axisPositions: number[] = [];
	export let axisSigns: number[] = [];
	export let groups: number[] = [];
	export let options: {
		bands: boolean;
		solutions: boolean;
		medians: boolean;
	} = {
		bands: true,
		solutions: true,
		medians: false
	};
	export let clusterVisibility: Record<number, boolean> | undefined;
	export let axisOrder: number[] = [];
	export let clusterColors: Record<number, string> = {};
	export let axisOptions: AxisOptions[] = [];
	export let onBandSelect: ((clusterId: number | null) => void) | undefined = undefined;
	export let onAxisSelect: ((axisIndex: number | null) => void) | undefined = undefined;
	export let selectedBand: number | null = null;
	export let selectedAxis: number | null = null;

	// Pre-calculated bands and medians from SCORE API (when raw data is not available)
	// bands = { "clusterId": { "axisName": [minValue, maxValue] } } - quantile-based band limits per cluster per axis
	export let bands: Record<string, Record<string, [number, number]>> = {};
	// medians = { "clusterId": { "axisName": medianValue } } - median value per cluster per axis
	export let medians: Record<string, Record<string, number>> = {};
	// scales = { "axisName": [minValue, maxValue] } - normalization scales for converting raw values to [0,1]
	export let scales: Record<string, [number, number]> | undefined = undefined;

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
	 * Draws SCORE-bands visualization using pre-calculated bands and medians
	 * Note: Raw data processing is commented out, using API data only
	 */
	function drawChart() {
		if (!container || axisNames.length === 0) return;
		// Allow rendering without data when we have bands/medians from API
		if (data.length === 0 && !options.bands && !options.medians) return;

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

		// Apply axis signs to flip axes if needed (only if we have data)
		const processedData =
			sortedData.length > 0
				? sortedData.map((row) =>
						row.map((val, i) => {
							const sign = sortedAxisSigns[i] || 1;
							return sign === -1 ? 1 - val : val; // Flip by inverting normalized value
						})
					)
				: [];

		// Y scales for each axis (using actual min/max from scales)
		const yScales = sortedAxisNames.map((axisName) => {
			if (scales && scales[axisName]) {
				const [min, max] = scales[axisName];
				return d3
					.scaleLinear()
					.domain([min, max])
					.range([height - margin.bottom, margin.top]);
			} else {
				// Fallback to normalized [0,1] if no scales provided
				return d3
					.scaleLinear()
					.domain([0, 1])
					.range([height - margin.bottom, margin.top]);
			}
		});

		// X positions for each axis
		const xPositions = sortedAxisPositions.map(
			(p) => margin.left + p * (width - margin.left - margin.right)
		);

		// --- Group data by cluster ---
		const grouped =
			processedData.length > 0 && groups.length > 0
				? d3.group(
						processedData.map((v, i) => ({ values: v, group: groups[i] })),
						(d) => d.group
					)
				: new Map();

		// --- Decide which drawing method to use ---
		// hasRawData: UI has list of solutions and calculates bands from them. This calculation is currently commented out.
		// hasPreCalculatedData: UI uses bands and medians pre-calculated by SCORE API, and might not have solutions at all.
		const hasRawData = processedData.length > 0 && groups.length > 0;
		const hasPreCalculatedData = Object.keys(bands).length > 0 && Object.keys(medians).length > 0;

		if (hasPreCalculatedData) {
			// --- Use pre-calculated bands and medians from SCORE API ---

			// Get unique cluster IDs from groups
			const uniqueClusterIds = [...new Set(groups)].sort((a, b) => a - b);

			// Draw all unselected clusters first
			uniqueClusterIds.forEach((clusterId) => {
				const clusterKey = clusterId.toString();
				if (!bands[clusterKey] || !medians[clusterKey]) return; // Skip if no data
				if (!effectiveClusterVisibility[clusterId]) return;
				if (selectedBand === clusterId) return; // skip selected cluster, draw it on top

				drawPreCalculatedCluster(
					svg,
					clusterId,
					bands,
					medians,
					sortedAxisNames,
					xPositions,
					yScales,
					clusterColors,
					sortedAxisSigns,
					options,
					false, // not selected
					onBandSelect
				);
			});

			// Draw selected cluster on top
			if (selectedBand !== null && effectiveClusterVisibility[selectedBand]) {
				const selectedClusterKey = selectedBand.toString();
				if (bands[selectedClusterKey] && medians[selectedClusterKey]) {
					drawPreCalculatedCluster(
						svg,
						selectedBand,
						bands,
						medians,
						sortedAxisNames,
						xPositions,
						yScales,
						clusterColors,
						sortedAxisSigns,
						options,
						true, // selected
						onBandSelect
					);
				}
			}
			// ORIGINAL VERSION USING RAW DATA TO CALCULATE BANDS
			// This version calculated bands from raw solution data instead of using pre-calculated API data

			// } else if (hasRawData) {
			// 	// --- Use raw data to calculate and draw bands ---
			// 	grouped.forEach((rows, groupId) => {
			// 		if (!effectiveClusterVisibility[groupId]) return;
			// 		if (selectedBand === groupId) return; // skip selected cluster here

			// 		drawBand(
			// 			svg,
			// 			rows,
			// 			groupId,
			// 			xPositions,
			// 			yScales,
			// 			clusterColors,
			// 			{
			// 				quantile: 0.25,
			// 				showMedian: options.medians,
			// 				showSolutions: options.solutions,
			// 				bandOpacity: 0.5
			// 			},
			// 			false, // not selected
			// 			onBandSelect
			// 		);
			// 	});

			// 	// --- Draw selected cluster on top ---
			// 	if (selectedBand !== null && effectiveClusterVisibility[selectedBand]) {
			// 		const selectedRows = grouped.get(selectedBand);
			// 		if (selectedRows) {
			// 			drawBand(
			// 				svg,
			// 				selectedRows,
			// 				selectedBand,
			// 				xPositions,
			// 				yScales,
			// 				clusterColors,
			// 				{
			// 					quantile: 0.25,
			// 					showMedian: options.medians,
			// 					showSolutions: options.solutions,
			// 					bandOpacity: 0.5
			// 				},
			// 				true, // selected styling
			// 				onBandSelect
			// 			);
			// 		}
			// 	}
		}

		// --- Draw axis lines and labels (always in front) ---
		xPositions.forEach((x, sortedIndex) => {
			const originalAxisIndex = effectiveAxisOrder[sortedIndex];
			const isSelected = selectedAxis === originalAxisIndex;
			const axisStyle = getAxisOptions(originalAxisIndex, axisOptions);

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
				// Get the actual value from the scale domain
				let actualValue: number;
				if (scales && scales[sortedAxisNames[sortedIndex]]) {
					const [min, max] = scales[sortedAxisNames[sortedIndex]];
					actualValue = min + tick * (max - min);
				} else {
					actualValue = tick;
				}

				const yPos = yScales[sortedIndex](actualValue);

				// Apply axis sign for flipped axes
				const sign = sortedAxisSigns[sortedIndex] || 1;
				const displayValue =
					sign === -1
						? scales && scales[sortedAxisNames[sortedIndex]]
							? scales[sortedAxisNames[sortedIndex]][0] +
								scales[sortedAxisNames[sortedIndex]][1] -
								actualValue
							: 1 - tick
						: actualValue;

				// Tick mark
				svg
					.append('line')
					.attr('x1', x - 5)
					.attr('y1', yPos)
					.attr('x2', x + 5)
					.attr('y2', yPos)
					.attr('stroke', '#666')
					.attr('stroke-width', 1);

				// Tick label (show actual scale values)
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
