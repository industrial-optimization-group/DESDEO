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
	export let options: { showLabels: boolean; orientation: 'horizontal' | 'vertical' } = {
		showLabels: true,
		orientation: 'horizontal'
	};

	// --- Internal state ---
	let width = 500;
	let height = 400;
	let svg: SVGSVGElement;
	let container: HTMLDivElement;
	let resizeObserver: ResizeObserver;

	/**
	 * Draws a horizontal bar chart using D3.
	 */
	function drawHorizontalChart(
		svgElement: d3.Selection<SVGGElement, unknown, null, undefined>,
		color: d3.ScaleOrdinal<string, string, never>,
		innerWidth: number,
		innerHeight: number,
		margin: { top: number; right: number; bottom: number; left: number },
		x: d3.ScaleLinear<number, number>,
		y: d3.ScaleBand<string>,
		xMin: number,
		xMax: number
	) {
		// Draw bars
		svgElement
			.append('g')
			.selectAll('rect')
			.data(data)
			.join('rect')
			.attr('y', (d) => y(d.name)!)
			.attr('height', y.bandwidth())
			.attr('x', (d) => (d.direction === 'min' ? x(0) : x(d.value)))
			.attr('width', (d) => (d.direction === 'min' ? x(d.value) - x(0) : xMax - x(d.value)))
			.attr('fill', (d) => color(d.name));

		// Draw axes
		svgElement.append('g').attr('transform', `translate(0,${margin.top})`).call(d3.axisTop(x));
		svgElement.append('g').attr('transform', `translate(${margin.left},0)`).call(d3.axisLeft(y));

		// Draw value labels if enabled
		if (options.showLabels) {
			svgElement
				.append('g')
				.selectAll('text')
				.data(data)
				.join('text')
				.attr('x', (d) => {
					const valueStr = d.value.toString();
					const approxTextWidth = valueStr.length * 7;
					let labelX = x(d.value);
					if (d.direction === 'min') {
						labelX += 5;
						if (labelX + approxTextWidth > xMax) labelX = xMax - approxTextWidth - 2;
					} else {
						labelX -= 5;
						if (labelX - approxTextWidth < xMin) labelX = xMin + approxTextWidth + 2;
					}
					return labelX;
				})
				.attr('y', (d) => y(d.name)! + y.bandwidth() / 2)
				.attr('dy', '0.35em')
				.attr('text-anchor', (d) => (d.direction === 'min' ? 'start' : 'end'))
				.text((d) => d.value);
		}
	}

	/**
	 * Draws a vertical bar chart using D3.
	 */
	function drawVerticalChart(
		svgElement: d3.Selection<SVGGElement, unknown, null, undefined>,
		color: d3.ScaleOrdinal<string, string, never>,
		innerWidth: number,
		innerHeight: number,
		margin: { top: number; right: number; bottom: number; left: number },
		x: d3.ScaleBand<string>,
		y: d3.ScaleLinear<number, number>,
		yMin: number,
		yMax: number
	) {
		// Draw bars
		svgElement
			.append('g')
			.selectAll('rect')
			.data(data)
			.join('rect')
			.attr('x', (d) => x(d.name)!)
			.attr('width', x.bandwidth())
			.attr('y', (d) => (d.direction === 'min' ? y(d.value) : yMax))
			.attr('height', (d) =>
				d.direction === 'min' ? y(0) - y(d.value) : y(0) - yMax - (y(0) - y(d.value))
			)
			.attr('fill', (d) => color(d.name));

		// Draw axes
		svgElement
			.append('g')
			.attr('transform', `translate(0,${innerHeight - margin.bottom})`)
			.call(d3.axisBottom(x));
		svgElement.append('g').attr('transform', `translate(${margin.left},0)`).call(d3.axisLeft(y));

		// Draw value labels if enabled
		if (options.showLabels) {
			svgElement
				.append('g')
				.selectAll('text')
				.data(data)
				.join('text')
				.attr('x', (d) => x(d.name)! + x.bandwidth() / 2)
				.attr('y', (d) => {
					let labelY = y(d.value);
					let approxTextHeight = 15;
					if (d.direction === 'min') {
						labelY -= 3;
						if (labelY > y(yMax)) labelY = y(yMax) - approxTextHeight;
					} else {
						labelY += approxTextHeight;
						if (labelY < y(yMin)) labelY = y(yMin) - approxTextHeight;
					}
					return labelY;
				})
				.attr('text-anchor', 'middle')
				.text((d) => d.value);
		}
	}

	/**
	 * Draws the bar chart (horizontal or vertical) using D3.
	 */
	function drawChart(): void {
		const margin = { top: 20, right: 20, bottom: 30, left: 40 };
		const innerWidth = width - margin.left - margin.right;
		const innerHeight = height - margin.top - margin.bottom;

		d3.select(svg).selectAll('*').remove();

		const svgElement = d3
			.select(svg)
			.attr('width', width)
			.attr('height', height)
			.append('g')
			.attr('transform', `translate(${margin.left}, ${margin.top})`);

		const color = d3
			.scaleOrdinal<string>()
			.domain(data.map((d) => d.name))
			.range(COLOR_PALETTE);

		if (options.orientation === 'horizontal') {
			const y = d3
				.scaleBand()
				.domain(data.map((d) => d.name))
				.range([margin.top, innerHeight - margin.bottom])
				.padding(0.1);

			const x = d3
				.scaleLinear()
				.domain([0, d3.max(data, (d) => d.value) ?? 0])
				.nice()
				.range([margin.left, innerWidth - margin.right]);

			const xMin = x.range()[0];
			const xMax = x.range()[1];

			drawHorizontalChart(svgElement, color, innerWidth, innerHeight, margin, x, y, xMin, xMax);
		} else {
			const x = d3
				.scaleBand()
				.domain(data.map((d) => d.name))
				.range([margin.left, innerWidth - margin.right])
				.padding(0.1);

			const y = d3
				.scaleLinear()
				.domain([0, d3.max(data, (d) => d.value) ?? 0])
				.nice()
				.range([innerHeight - margin.bottom, margin.top]);

			const yMin = y.range()[0];
			const yMax = y.range()[1];

			drawVerticalChart(svgElement, color, innerWidth, innerHeight, margin, x, y, yMin, yMax);
		}

		// Draw border around plot area
		svgElement
			.append('rect')
			.attr('x', margin.left)
			.attr('y', margin.top)
			.attr('width', innerWidth - margin.left - margin.right)
			.attr('height', innerHeight - margin.top - margin.bottom)
			.attr('fill', 'none')
			.attr('stroke', 'black')
			.attr('stroke-width', 1);
	}

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
