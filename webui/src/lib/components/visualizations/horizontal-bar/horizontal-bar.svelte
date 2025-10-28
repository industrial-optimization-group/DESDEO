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
	 * - options: { decimalPrecision, showPreviousValue, showSelectedValueLabel, aspectRatio }
	 * - onSelect?: (value: number) => void — callback when selected value changes
	 *
	 * @features
	 * - Shows a solution bar, selected value (draggable), previous value marker, and ideal/nadir triangles.
	 * - Supports min/max direction, custom color, and value formatting.
	 * - Responsive to container width.
	 * - Calls `onSelect` callback when the selected value changes via drag.
	 * - Shows previousValue text in the top right corner.
	 * - Solution value marker with click event to set the selected value.
	 * - Click events on lower and upper bounds triangles to set the selected value.
	 * - Click event on previous value marker to set the selected value.
	 * - Click-anywhere functionality on the bar area to set the selected value.
	 *
	 * @notes
	 * - TODO: Add tooltip on hover to show exact values.
	 * - TODO: Validate the lower and upper bounds to ensure they are valid numbers.
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
		decimalPrecision: number;
		showPreviousValue: boolean;
		showSelectedValueLabel?: boolean;
		aspectRatio: string;
	} = {
		decimalPrecision: 2,
		showPreviousValue: true,
		showSelectedValueLabel: true,
		aspectRatio: 'aspect-[11/2]'
	};

	/** Callback called with the new selected value after dragging */
	export let onSelect: ((value: number) => void) | undefined = undefined;

	// --- Internal state ---
	let width = 500;
	let height = 70; // initial value, will be updated dynamically
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

		const margin = { top: 6, right: 30, bottom: 18, left: 30 };
		const innerWidth = width - margin.left - margin.right;
		const innerHeight = height - margin.top - margin.bottom;

		const x = d3
			.scaleLinear()
			.domain([axisRanges[0], axisRanges[1]])
			.range([margin.left, width - margin.right]);

		// --- Draw x-axis below the bar ---
		const xAxis = d3
			.axisBottom(x)
			.ticks(4)
			.tickFormat((d) => d.toString());

		const axisGroup = d3.select(svg)
			.append('g')
			.attr('transform', `translate(0,${height - margin.bottom})`)
			.call(xAxis);

		// Select all text elements within the axis and apply rotation
		axisGroup.selectAll('text')  
			.style('text-anchor', 'end')
			.attr('dx', '-.8em')
			.attr('dy', '.15em')
			.attr('transform', 'rotate(-65)');

		// --- Draw bar background ---
		d3.select(svg)
			.append('rect')
			.attr('x', x(axisRanges[0]))
			.attr('y', margin.top)
			.attr('width', x(axisRanges[1]) - x(axisRanges[0]))
			.attr('height', innerHeight)
			.attr('fill', direction === 'min' ? '#eee' : barColor)
			.attr('rx', 1);
		
			// --- Draw solution bar ---
		if (solutionValue !== undefined) {
			const solWidth = x(solutionValue) - x(axisRanges[0]);
			d3.select(svg)
				.append('rect')
				.attr('x', x(axisRanges[0]))
				.attr('y', margin.top)
				.attr('width', Math.max(0, solWidth))
				.attr('height', innerHeight)
				.attr('fill', direction === 'min' ? barColor : '#eee')
				.attr('rx', 1);
		}

		// --- Add click-anywhere functionality to the bar area ---
		d3.select(svg)
			.append('rect')
			.attr('x', margin.left)
			.attr('y', margin.top - 8) // Extend slightly above the bar
			.attr('width', innerWidth)
			.attr('height', innerHeight + 16) // Extend slightly below the bar
			.attr('fill', 'transparent') // Invisible but clickable
			.attr('cursor', 'pointer')
			.on('click', function(event) {
				// Get the mouse position relative to the SVG
				const [mouseX] = d3.pointer(event, this);
				
				// Convert pixel position to value
				const clickedValue = x.invert(mouseX);
				
				// Clamp the value to the axis ranges
				const clampedValue = Math.max(axisRanges[0], Math.min(axisRanges[1], clickedValue));
				
				// Round to the specified precision
				const roundedValue = roundToDecimal(clampedValue, options.decimalPrecision);
				
				selectedValue = roundedValue;
				if (onSelect) onSelect(roundedValue);
			});

		// --- Draw a marker for the solution value ---
		if (solutionValue !== undefined) {
		d3.select(svg)
			.append('polygon')
			.attr(
			'points',
			[
				[x(solutionValue) - 6, margin.top - 6], // bottom left
				[x(solutionValue) + 6, margin.top - 6], // bottom right
				[x(solutionValue), margin.top + 2]      // tip (pointing down)
			]
				.map((p) => p.join(','))
				.join(' ')
			)
			.attr('fill', '#444')
			.attr('cursor', 'pointer')
			.on('click', () => {
				selectedValue = solutionValue;
				if (onSelect) onSelect(solutionValue);
			});
		}

		// --- Draw lower bound triangle, pointing left ---
		d3.select(svg)
			.append('polygon')
			.attr(
				'points',
				[
					[x(axisRanges[0]) - 10, margin.top + innerHeight / 2], // tip (left)
					[x(axisRanges[0]), margin.top + 2], // top right
					[x(axisRanges[0]), margin.top + innerHeight - 2] // bottom right
				]
					.map((p) => p.join(','))
					.join(' ')
			)
			.attr('fill', '#fff')
			.attr('stroke', '#888')
			.attr('stroke-width', 2)
			.attr('cursor', 'pointer')
			.on('click', () => {
				selectedValue = axisRanges[0];
				if (onSelect) onSelect(axisRanges[0]);
			});

		// --- Draw upper bound triangle, pointing right ---
		d3.select(svg)
			.append('polygon')
			.attr(
				'points',
				[
					[x(axisRanges[1]) + 10, margin.top + innerHeight / 2], // tip (right)
					[x(axisRanges[1]), margin.top + 2], // top left
					[x(axisRanges[1]), margin.top + innerHeight - 2] // bottom left
				]
					.map((p) => p.join(','))
					.join(' ')
			)
			.attr('fill', '#fff')
			.attr('stroke', '#888')
			.attr('stroke-width', 2)
			.attr('cursor', 'pointer')
			.on('click', () => {
				selectedValue = axisRanges[1];
				if (onSelect) onSelect(axisRanges[1]);
			});

		// --- Draw previous value marker (if enabled) ---
		if (options.showPreviousValue && previousValue !== undefined) {
			d3.select(svg)
				.append('circle')
				.attr('cx', x(previousValue))
				.attr('cy', margin.top + innerHeight / 2)
				.attr('r', 6)
				.attr('fill', '#000')
				.attr('fill-opacity', 0.5)
				.attr('stroke', '#000')
				.attr('stroke-width', 2)
				.attr('cursor', 'pointer')
				.on('click', () => {
					selectedValue = previousValue;
					if (onSelect) onSelect(previousValue);
    			});
		}

		// --- Draw selected value marker (draggable) ---
		if (selectedValue !== undefined) {
			dragLine = d3
				.select(svg)
				.append('line')
				.attr('x1', x(selectedValue))
				.attr('x2', x(selectedValue))
				.attr('y1', margin.top - 8)
				.attr('y2', margin.top + innerHeight + 8)
				.attr('stroke', '#222')
				.attr('stroke-width', 2)
				.attr('cursor', 'ew-resize');

			dragCircle = d3
				.select(svg)
				.append('circle')
				.attr('cx', x(selectedValue))
				.attr('cy', margin.top + innerHeight / 2)
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
		if (options.showSelectedValueLabel && selectedValue !== undefined) {
			d3.select(svg)
				.append('text')
				.attr('x', x(selectedValue))
				.attr('y', margin.bottom + 52)
				.attr('text-anchor', 'middle')
				.attr('fill', '#222')
				.attr('font-size', 13)
				.text(`Selected: ${roundToDecimal(selectedValue, options.decimalPrecision)}`);
		}

		// --- Draw previous preference as text in the top right corner ---
		if (options.showPreviousValue && previousValue !== undefined) {
			d3.select(svg)
				.append('text')
				.attr('x', width - margin.right + 30)
				.attr('y', margin.top - 25)
				.attr('text-anchor', 'end')
				.attr('fill', '#222')
				.attr('font-size', 13)
				.text('Previous preference:')
				.append('tspan') // value to next line
				.attr('x', width - margin.right + 30) // Same x alignment
				.attr('dy', '1.2em') // Move down relative to the previous line
				.attr('text-anchor', 'end')
				.text(`${roundToDecimal(previousValue, options.decimalPrecision)}`);
						}
	}

	// --- Lifecycle: Responsive redraw ---
	onMount(() => {
		resizeObserver = new ResizeObserver((entries) => {
			for (const entry of entries) {
				const rect = entry.contentRect;
				width = rect.width;
				height = rect.height; // dynamically update height
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
		height,
		options,
		drawChart();
</script>

<!--
    Responsive container for the horizontal bar chart.
    Use the aspect ratio from options.
-->
<div class={options.aspectRatio} bind:this={container} style="width: 100%; height: 100%;">
	<svg bind:this={svg} style="width: 100%; height: 100%; overflow: visible;" />
</div>
