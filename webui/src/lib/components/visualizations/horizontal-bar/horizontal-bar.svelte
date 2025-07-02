<script lang="ts">
	/**
	 * Horizontal bar
	 * --------------------------------
	 *
	 * @author Giomara Larraga <glarragw@jyu.fi>
	 * @created June 2025
	 *
	 * @description
	 * Renders a single horizontal bar visualization using D3.
	 *
	 * @props
	 * - axisRanges: [number, number] — lower and upper bounds of the bar
	 * - solutionValue?: number — value to fill the bar up to
	 * - selectedValue?: number — draggable marker value
	 * - previousValue?: number — previous value marker
	 * - barColor: string — color of the solution bar
	 * - direction: 'max' | 'min' — whether lower or higher is better
	 * - options: { barHeight, decimalPrecision, showPreviousValue, aspectRatio }
	 * - onSelect?: (value: number) => void — callback when selected value changes
	 *
	 * @features
	 * - Shows a solution bar, selected value (draggable), previous value marker, and ideal/nadir triangles.
	 * - Supports min/max direction, custom color, and value formatting.
	 * - Responsive to container width.
	 * - Calls `onSelect` callback when the selected value changes via drag.
	 *
	 * @notes
	 * - TODO: Show previousValue text in the top right corner.
	 * - TODO: Add a marker to the solution value with a click event to set the selected value.
	 * - TODO: Add tooltip on hover to show exact values.
	 * - TODO: Add click event to the lower and upper bounds to set the selected value.
	 * - TODO: Add click event to previous value marker to set the selected value.
	 * - TODO: Vaidate the lower and upper bounds to ensure they are valid numbers.
	 * - TODO: Validate the solution value to ensure it is within the bounds.
	 * - TODO: Validate the text shown in the selected value to not be outside the svg bounds.
	 */

	import { onMount, onDestroy } from 'svelte';
	import { roundToDecimal } from '$lib/components/visualizations/utils/math';
	import * as d3 from 'd3';

	// --- Props ---
	export let axisRanges: [number, number] = [0, 1];
	export let solutionValue: number | undefined = undefined;
	export let selectedValue: number | undefined = undefined;
	export let previousValue: number | undefined = undefined;
	export let barColor: string = '#4f8cff';
	export let direction: 'max' | 'min' = 'min';

	export let options: {
		barHeight: number;
		decimalPrecision: number;
		showPreviousValue: boolean;
		aspectRatio: string;
	} = {
		barHeight: 32,
		decimalPrecision: 2,
		showPreviousValue: true,
		aspectRatio: 'aspect-[11/2]'
	};

	/** Callback called with the new selected value after dragging */
	export let onSelect: ((value: number) => void) | undefined = undefined;

	// --- Internal state ---
	let width = 500;
	let height = 70;
	let svg: SVGSVGElement;
	let container: HTMLDivElement;
	let dragLine: d3.Selection<SVGLineElement, unknown, null, undefined>;
	let dragCircle: d3.Selection<SVGCircleElement, unknown, null, undefined>;
	let resizeObserver: ResizeObserver;

	/**
	 * Draws the horizontal bar chart using D3.
	 */
	function drawChart() {
		d3.select(svg).selectAll('*').remove();

		const margin = { top: 2, right: 30, bottom: 2, left: 30 };
		const innerWidth = width - margin.left - margin.right;
		const innerHeight = height - margin.top - margin.bottom;

		const x = d3
			.scaleLinear()
			.domain([axisRanges[0], axisRanges[1]])
			.range([margin.left, width - margin.right]);

		// --- Draw x-axis below the bar ---
		const xAxis = d3
			.axisBottom(x)
			.ticks(6)
			.tickFormat((d) => d.toString());

		d3.select(svg)
			.append('g')
			.attr('transform', `translate(0,${innerHeight / 2 + options.barHeight})`)
			.call(xAxis);

		// --- Draw bar background ---
		d3.select(svg)
			.append('rect')
			.attr('x', x(axisRanges[0]))
			.attr('y', innerHeight / 2)
			.attr('width', x(axisRanges[1]) - x(axisRanges[0]))
			.attr('height', options.barHeight)
			.attr('fill', direction === 'min' ? '#eee' : barColor)
			.attr('rx', 1);

		// --- Draw solution bar ---
		if (solutionValue !== undefined) {
			const solWidth = x(solutionValue) - x(axisRanges[0]);
			d3.select(svg)
				.append('rect')
				.attr('x', x(axisRanges[0]))
				.attr('y', innerHeight / 2)
				.attr('width', Math.max(0, solWidth))
				.attr('height', options.barHeight)
				.attr('fill', direction === 'min' ? barColor : '#eee')
				.attr('rx', 1);
		}

		// --- Draw lower bound triangle, pointing left ---
		d3.select(svg)
			.append('polygon')
			.attr(
				'points',
				[
					[x(axisRanges[0]) - 10, innerHeight / 2 + options.barHeight / 2], // tip (left)
					[x(axisRanges[0]), innerHeight / 2 + 2], // top right
					[x(axisRanges[0]), innerHeight / 2 + options.barHeight - 2] // bottom right
				]
					.map((p) => p.join(','))
					.join(' ')
			)
			.attr('fill', '#fff')
			.attr('stroke', '#888')
			.attr('stroke-width', 2);

		// --- Draw upper bound triangle, pointing right ---
		d3.select(svg)
			.append('polygon')
			.attr(
				'points',
				[
					[x(axisRanges[1]) + 10, innerHeight / 2 + options.barHeight / 2], // tip (right)
					[x(axisRanges[1]), innerHeight / 2 + 2], // top left
					[x(axisRanges[1]), innerHeight / 2 + options.barHeight - 2] // bottom left
				]
					.map((p) => p.join(','))
					.join(' ')
			)
			.attr('fill', '#fff')
			.attr('stroke', '#888')
			.attr('stroke-width', 2);

		// --- Draw previous value marker (if enabled) ---
		if (options.showPreviousValue && previousValue !== undefined) {
			d3.select(svg)
				.append('circle')
				.attr('cx', x(previousValue))
				.attr('cy', innerHeight / 2 + options.barHeight / 2)
				.attr('r', 6)
				.attr('fill', '#000')
				.attr('fill-opacity', 0.5)
				.attr('stroke', '#000')
				.attr('stroke-width', 2);
		}

		// --- Draw selected value marker (draggable) ---
		if (selectedValue !== undefined) {
			dragLine = d3
				.select(svg)
				.append('line')
				.attr('x1', x(selectedValue))
				.attr('x2', x(selectedValue))
				.attr('y1', innerHeight / 2 - 8)
				.attr('y2', innerHeight / 2 + options.barHeight + 8)
				.attr('stroke', '#222')
				.attr('stroke-width', 2)
				.attr('cursor', 'ew-resize');

			dragCircle = d3
				.select(svg)
				.append('circle')
				.attr('cx', x(selectedValue))
				.attr('cy', innerHeight / 2 + options.barHeight / 2)
				.attr('r', 9)
				.attr('fill', '#fff')
				.attr('fill-opacity', 0.9)
				.attr('stroke', '#222')
				.attr('stroke-width', 2)
				.attr('cursor', 'ew-resize')
				.call(
					d3.drag<SVGCircleElement, unknown>().on('drag', function (event) {
						let px = Math.max(x(axisRanges[0]), Math.min(x(axisRanges[1]), event.x));
						const newValue = roundToDecimal(x.invert(px), options.decimalPrecision);
						selectedValue = newValue;
						dragCircle.attr('cx', px);
						dragLine.attr('x1', px).attr('x2', px);
						if (onSelect) onSelect(newValue);
					})
				);
		}

		// --- Draw selected value label ---
		if (selectedValue !== undefined) {
			d3.select(svg)
				.append('text')
				.attr('x', x(selectedValue))
				.attr('y', innerHeight / 2 - 12)
				.attr('text-anchor', 'middle')
				.attr('fill', '#222')
				.attr('font-size', 13)
				.text(`Selected: ${roundToDecimal(selectedValue, options.decimalPrecision)}`);
		}
	}

	// --- Lifecycle: Responsive redraw ---
	onMount(() => {
		resizeObserver = new ResizeObserver((entries) => {
			for (const entry of entries) {
				const rect = entry.contentRect;
				width = rect.width;
				drawChart();
			}
		});
		resizeObserver.observe(container);
		drawChart();
	});
	onDestroy(() => {
		resizeObserver.disconnect();
	});

	// --- Redraw on prop changes ---
	$: axisRanges,
		solutionValue,
		selectedValue,
		previousValue,
		barColor,
		direction,
		width,
		options,
		drawChart();
</script>

<!--
    Responsive container for the horizontal bar chart.
    Use the aspect ratio from options.
-->
<div class={options.aspectRatio} bind:this={container} style="width: 100%;">
	<svg bind:this={svg} style="width: 100%; height: 100px;" />
</div>
