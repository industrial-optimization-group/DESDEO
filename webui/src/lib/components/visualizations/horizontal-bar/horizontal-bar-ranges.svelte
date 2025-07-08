<script lang="ts">
	/**
	 * Horizontal bar with two draggable bounds (lower and upper)
	 * --------------------------------
	 * @author Giomara Larraga <glarragw@jyu.fi>
	 * @created July 2025
	 *
	 * @description
	 * Renders a horizontal bar with two draggable markers for lower and upper bounds.
	 *
	 * @props
	 * - axisRanges: [number, number] — lower and upper bounds of the bar
	 * - lowerBound: number — current lower bound value (draggable)
	 * - upperBound: number — current upper bound value (draggable)
	 * - barColor: string — color of the bar
	 * - direction: 'max' | 'min'
	 * - options: { decimalPrecision, showPreviousValue, aspectRatio }
	 * - onChangeBounds?: (lower: number, upper: number) => void — callback when bounds change
	 *
	 * @features
	 * - Two draggable markers for lower and upper bounds.
	 * - Calls `onChangeBounds` when either marker is moved.
	 * - Responsive to container size.
	 */

	import { onMount, onDestroy } from 'svelte';
	import { roundToDecimal } from '$lib/components/visualizations/utils/math';
	import * as d3 from 'd3';

	export let axisRanges: [number, number] = [0, 1];
	export let lowerBound: number = 0.2;
	export let upperBound: number = 0.8;
	export let barColor: string = '#4f8cff';
	export let direction: 'max' | 'min' = 'min';

	export let options: {
		decimalPrecision: number;
		showPreviousValue: boolean;
		aspectRatio: string;
	} = {
		decimalPrecision: 2,
		showPreviousValue: true,
		aspectRatio: 'aspect-[11/2]'
	};

	export let onChangeBounds: ((lower: number, upper: number) => void) | undefined = undefined;

	let width = 500;
	let height = 70;
	let svg: SVGSVGElement;
	let container: HTMLDivElement;
	let resizeObserver: ResizeObserver;

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
			.ticks(6)
			.tickFormat((d) => d.toString());

		d3.select(svg)
			.append('g')
			.attr('transform', `translate(0,${height - margin.bottom})`)
			.call(xAxis);

		// --- Draw bar background ---
		d3.select(svg)
			.append('rect')
			.attr('x', x(axisRanges[0]))
			.attr('y', margin.top)
			.attr('width', x(axisRanges[1]) - x(axisRanges[0]))
			.attr('height', innerHeight)
			.attr('fill', '#eee')
			.attr('rx', 1);

		// --- Draw selected range bar ---
		const lowerPx = x(lowerBound);
		const upperPx = x(upperBound);
		d3.select(svg)
			.append('rect')
			.attr('x', Math.min(lowerPx, upperPx))
			.attr('y', margin.top)
			.attr('width', Math.abs(upperPx - lowerPx))
			.attr('height', innerHeight)
			.attr('fill', barColor)
			.attr('rx', 1)
			.attr('opacity', 0.7);

		// --- Draw lower bound marker (draggable) ---
		const dragLower = d3.drag<SVGCircleElement, unknown>().on('drag', function (event) {
			let px = Math.max(x(axisRanges[0]), Math.min(x(upperBound), event.x));
			const newLower = roundToDecimal(x.invert(px), options.decimalPrecision);
			if (newLower > upperBound) return;
			lowerBound = Math.min(newLower, upperBound);
			d3.select(this).attr('cx', x(lowerBound));
			if (onChangeBounds) onChangeBounds(lowerBound, upperBound);
			drawChart();
		});

		d3.select(svg)
			.append('circle')
			.attr('cx', x(lowerBound))
			.attr('cy', margin.top + innerHeight / 2)
			.attr('r', 9)
			.attr('fill', '#fff')
			.attr('stroke', barColor)
			.attr('stroke-width', 3)
			.attr('cursor', 'ew-resize')
			.call(dragLower);

		d3.select(svg)
			.append('text')
			.attr('x', x(lowerBound))
			.attr('y', margin.top - 12)
			.attr('text-anchor', 'middle')
			.attr('fill', barColor)
			.attr('font-size', 13)
			.text(`L: ${roundToDecimal(lowerBound, options.decimalPrecision)}`);

		// --- Draw upper bound marker (draggable) ---
		const dragUpper = d3.drag<SVGCircleElement, unknown>().on('drag', function (event) {
			let px = Math.max(x(lowerBound), Math.min(x(axisRanges[1]), event.x));
			const newUpper = roundToDecimal(x.invert(px), options.decimalPrecision);
			if (newUpper < lowerBound) return;
			upperBound = Math.max(newUpper, lowerBound);
			d3.select(this).attr('cx', x(upperBound));
			if (onChangeBounds) onChangeBounds(lowerBound, upperBound);
			drawChart();
		});

		d3.select(svg)
			.append('circle')
			.attr('cx', x(upperBound))
			.attr('cy', margin.top + innerHeight / 2)
			.attr('r', 9)
			.attr('fill', '#fff')
			.attr('stroke', barColor)
			.attr('stroke-width', 3)
			.attr('cursor', 'ew-resize')
			.call(dragUpper);

		d3.select(svg)
			.append('text')
			.attr('x', x(upperBound))
			.attr('y', margin.top - 12)
			.attr('text-anchor', 'middle')
			.attr('fill', barColor)
			.attr('font-size', 13)
			.text(`U: ${roundToDecimal(upperBound, options.decimalPrecision)}`);
	}

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

	$: axisRanges, lowerBound, upperBound, barColor, direction, width, height, options, drawChart();
</script>

<div class={options.aspectRatio} bind:this={container} style="width: 100%; height: 100%;">
	<svg bind:this={svg} style="width: 100%; height: 100%;" />
</div>
