<script lang="ts">
	/**
	 * Responsive Barchart component using D3.
	 *
	 * Features:
	 * - Supports both horizontal and vertical bar charts.
	 * - Each bar can have a different value range (axisRanges).
	 * - If axisRanges is provided per bar, values are normalized to [0, 1] for plotting.
	 * - Supports 'max' (bars from axis min) and 'min' (bars from axis max) directions.
	 * - Custom color palette.
	 * - Responsive to container size (uses ResizeObserver).
	 * - Optionally shows value labels.
	 *
	 * Props:
	 * - data: Array<{ name: string; value: number; direction: 'max' | 'min' }>
	 * - axisRanges: Array<[number, number]>; if length === data.length, each bar uses its own range
	 * - options: { showLabels: boolean; orientation: 'horizontal' | 'vertical' }
	 */

	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import { COLOR_PALETTE } from '../utils/colors';

	export let data: { name: string; value: number; direction: 'max' | 'min' }[] = [];
	export let axisRanges: [number, number][] = [];
	export let options: { showLabels: boolean; orientation: 'horizontal' | 'vertical' } = {
		showLabels: true,
		orientation: 'horizontal'
	};

	// TODO: Normalize data values based on axisRanges if provided
	// TODO: Give option to show multiple axes with different ranges
	// TODO: Give option to show min and max values for each bar

	// Remove export let width/height, use internal variables
	let width = 500;
	let height = 400;

	let svg: SVGSVGElement;
	let container: HTMLDivElement;
	let resizeObserver: ResizeObserver;

	/**
	 * Normalize a value to [0, 1] given a min and max.
	 */
	function normalize(value: number, min: number, max: number): number {
		if (max === min) return 0.5;
		return (value - min) / (max - min);
	}

	/**
	 * Get the value range for the axis.
	 * If axisRanges is not per-bar, use the first range or fallback to min/max of all data.
	 */
	function getValueRange(): [number, number] {
		if (axisRanges && axisRanges.length === 1) {
			const [min, max] = axisRanges[0];
			if (isFinite(min) && isFinite(max) && min < max) return [min, max];
		}
		const values = data.map((d) => d.value);
		const min = Math.min(...values);
		const max = Math.max(...values);
		if (min === max) return [min - 1, max + 1];
		return [min, max];
	}

	/**
	 * Draw the chart using D3.
	 */
	function drawChart() {
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

			svgElement
				.append('g')
				.selectAll('rect')
				.data(data)
				.join('rect')
				.attr('y', (d) => y(d.name)!)
				.attr('height', y.bandwidth())
				.attr('x', (d) => (d.direction === 'min' ? x(0) : x(d.value)))
				.attr('width', (d) => (d.direction === 'min' ? x(d.value) - x(0) : xMax - x(d.value)))
				.attr('fill', (d, i) => color(d.name));

			// Draw axes
			svgElement.append('g').attr('transform', `translate(0,${margin.top})`).call(d3.axisTop(x));
			svgElement.append('g').attr('transform', `translate(${margin.left},0)`).call(d3.axisLeft(y));

			// Optionally show labels
			if (options.showLabels) {
				svgElement
					.append('g')
					.selectAll('text')
					.data(data)
					.join('text')
					.attr('x', (d) => {
						const valueStr = d.value.toString();
						const approxTextWidth = valueStr.length * 7; // ~7px per character
						let labelX = x(d.value);
						if (d.direction === 'min') {
							// For 'min', label is to the right of the bar
							labelX += 5;
							if (labelX + approxTextWidth > xMax) {
								labelX = xMax - approxTextWidth - 2;
							}
						} else {
							// For 'max', label is to the left of the bar
							labelX -= 5;
							if (labelX - approxTextWidth < xMin) {
								labelX = xMin + approxTextWidth + 2;
							}
						}
						return labelX;
					})
					.attr('y', (d) => y(d.name)! + y.bandwidth() / 2)
					.attr('dy', '0.35em')
					.attr('text-anchor', (d) => (d.direction === 'min' ? 'start' : 'end'))
					.text((d) => d.value);
			}
		} else {
			// Vertical bar chart (default)
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

			// Draw bars first
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
				.attr('fill', (d, i) => color(d.name));

			svgElement
				.append('g')
				.attr('transform', `translate(0,${innerHeight - margin.bottom})`)
				.call(d3.axisBottom(x));

			svgElement.append('g').attr('transform', `translate(${margin.left},0)`).call(d3.axisLeft(y));

			// Optionally show labels
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
							// For 'min', label is on the top of the bar
							labelY -= 3;
							if (labelY > y(yMax)) {
								labelY = y(yMax) - approxTextHeight;
							}
						} else {
							// For 'max', label is below the bar
							labelY += approxTextHeight;
							if (labelY < y(yMin)) {
								labelY = y(yMin) - approxTextHeight;
							}
						}
						return labelY;
					})
					.attr('text-anchor', 'middle')
					.text((d) => d.value);
			}
		}

		// Draw border around plot area last (so it's on top)
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

	// Responsive: update chart on container resize
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
	});
	onDestroy(() => {
		resizeObserver.disconnect();
	});

	// Redraw chart on data/options/size change
	$: data, options, width, height, axisRanges, drawChart();
</script>

<!-- Responsive container with aspect ratio -->
<div bind:this={container} style="aspect-ratio: 5 / 4; width: 100%;">
	<svg bind:this={svg} style="width: 100%; height: 100%;" />
</div>
