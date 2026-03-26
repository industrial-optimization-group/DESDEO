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
	 */

	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import { COLOR_PALETTE } from '../utils/colors';
	import { derived } from 'svelte/store';

	// --- Props ---
	export let data: { name: string; symbol: string; value: number; direction: 'max' | 'min' }[] = [];
	export let axisRanges: [number, number][] = [];
	export let options: { showLabels: boolean; type: 'multipliers' | 'tradeoffs' } = {
		showLabels: true,
		type: 'multipliers'
	};

	export let onSelect: ((event: { value: string }) => void) | undefined = undefined;

	export let selected_objective_symbol: string | null = null;

	let selected_objective_name = '';

	$: {
		const obj = data.find((d) => d.symbol === selected_objective_symbol);
		selected_objective_name = obj ? obj.name : '';
	}

	// --- Internal state ---
	let width = 500;
	let height = 400;
	let svg: SVGSVGElement;
	let container: HTMLDivElement;
	let resizeObserver: ResizeObserver;
	let originalData: typeof data = [];
	let tooltip: HTMLDivElement;

	function normalizeData(
		data: { name: string; symbol: string; value: number; direction: 'max' | 'min' }[]
	) {
		let normalized_data = data;
		// Normalize data values between 0 and 1
		const values = normalized_data.map((d) => d.value);
		const minValue = Math.min(...values);
		const maxValue = Math.max(...values);
		if (maxValue > minValue) {
			normalized_data = normalized_data.map((d) => ({
				...d,
				value: (d.value - minValue) / (maxValue - minValue)
			}));
		} else {
			normalized_data = normalized_data.map((d) => ({
				...d,
				value: 0
			}));
		}
		return normalized_data;
	}

	/**
	 * Draws a horizontal bar chart using D3.
	 *
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
		xMax: number,
		tooltipSelection: d3.Selection<HTMLDivElement, unknown, null, undefined>
	) {
		// Draw bars
		svgElement
			.append('g')
			.selectAll('rect')
			.data(data)
			.join('rect')
			.attr('y', (d) => y(d.name)!)
			.attr('height', y.bandwidth())
			.attr('x', (d) => {
				// For negative values, start from value position; for positive, start from 0
				return d.value < 0 ? x(d.value) : x(0);
			})
			.attr('width', (d) => Math.abs(x(d.value) - x(0)))
			.attr('fill', (d) => color(d.name))
			.style('cursor', 'pointer') // Add this line
			.on('mouseenter', (event, d) => {
				tooltipSelection
					.style('opacity', 1)
					.classed('text-sm', true)
					.html(
						selected_objective_symbol == d.symbol
							? `<span class="text-primary font-semibold">${selected_objective_name}</span> is the objective function you want to improve`
							: `Improving one unit in <span class="text-primary font-semibold">${selected_objective_name}</span> would impair <span class="text-primary font-semibold">${d.name}</span> by ${Math.abs(d.value).toFixed(3)} units.`
					);
			})
			.on('mousemove', (event) => {
				const [xPos, yPos] = d3.pointer(event, container);
				tooltipSelection.style('left', `${xPos + 12}px`).style('top', `${yPos + 12}px`);
			})
			.on('mouseleave', () => {
				tooltipSelection.style('opacity', 0);
			});

		// Add tooltip to each bar

		// Draw axes
		svgElement.append('g').attr('transform', `translate(0,${margin.top})`).call(d3.axisTop(x));
		svgElement.append('g').attr('transform', `translate(${margin.left},0)`).call(d3.axisLeft(y));

		// Draw zero line if domain includes negative values
		if (x.domain()[0] < 0 && x.domain()[1] > 0) {
			svgElement
				.append('line')
				.attr('x1', x(0))
				.attr('x2', x(0))
				.attr('y1', margin.top)
				.attr('y2', innerHeight - margin.bottom)
				.attr('stroke', 'black')
				.attr('stroke-width', 2);
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
		yMax: number,
		tooltipSelection: d3.Selection<HTMLDivElement, unknown, null, undefined>
	) {
		// Draw bars

		data.forEach(
			(
				element: { name: string; symbol: string; value: number; direction: 'max' | 'min' },
				index
			) => {
				svgElement
					.append('g')
					.selectAll('rect')
					.data([element])
					.join('rect')
					.attr('x', (d) => x(d.name)!)
					.attr('width', x.bandwidth())
					.attr('y', (d) => y(d.value))
					/*.attr('height', (d) =>
					d.direction === 'min' ? y(0) - y(d.value) : y(0) - yMax - (y(0) - y(d.value))
				)*/
					.attr('height', (d) => y(0) - y(d.value))

					.style('cursor', 'pointer')
					.on('click', (event, d) => {
						if (onSelect) {
							onSelect({ value: element.symbol });
							selected_objective_symbol = element.symbol;
						}
					})

					.attr('fill', (d) => color(d.name));

				// Highlight selected bar
				if (onSelect && element.symbol === selected_objective_symbol) {
					svgElement
						.append('rect')
						.attr('x', x(element.name)!)
						.attr('width', x.bandwidth())
						.attr('y', (d) => y(element.value))
						.attr('height', y(0) - y(element.value))
						.attr('fill', 'none')
						.attr('stroke', 'blue')
						.attr('stroke-width', 2);
				}
			}
		);

		// Draw axes
		svgElement
			.append('g')
			.attr('transform', `translate(0,${innerHeight - margin.bottom})`)
			.call(d3.axisBottom(x))
			.selectAll('text')
			.attr('transform', 'rotate(-35)')
			.style('text-anchor', 'end')
			.style('font-size', '10px')
			.each(function () {
				const text = d3.select(this);
				const fullText = text.text();
				if (fullText.length > 18) {
					text.text(fullText.substring(0, 16) + '…');
				}
			});
		svgElement.append('g').attr('transform', `translate(${margin.left},0)`).call(d3.axisLeft(y));
	}

	/**
	 * Draws the bar chart (horizontal or vertical) using D3.
	 */
	function drawChart(): void {
		let margin = { top: 0, right: 1, bottom: 30, left: 30 };

		if (options.type == 'tradeoffs') {
			margin = { top: 0, right: 1, bottom: 30, left: 30 };
			// Normalize all except the selected objective
			// Use the absotlute data values for normalization

			let data_to_use = data;
			if (selected_objective_symbol !== null && selected_objective_symbol !== undefined) {
				data_to_use = data.map((d, i) =>
					d.symbol === selected_objective_symbol ? { ...d, value: 1 } : { ...d, value: d.value }
				);
				//data = normalizeData(data_to_use);
				data = data_to_use;
			}
		} else {
			margin = { top: 10, right: 11, bottom: 60, left: 20 };
			data = normalizeData(data);
		}
		//const margin = { top: 20, right: 20, bottom: 30, left: 40 };
		const innerWidth = width - margin.left - margin.right;
		const innerHeight = height - margin.top - margin.bottom;

		d3.select(svg).selectAll('*').remove();

		const svgElement = d3
			.select(svg)
			.attr('width', width)
			.attr('height', height)
			.append('g')
			.attr('transform', `translate(${margin.left}, ${margin.top})`);

		const tooltipSelection = d3.select(tooltip);

		const color = d3
			.scaleOrdinal<string>()
			.domain(data.map((d) => d.name))
			.range(COLOR_PALETTE);

		if (options.type === 'tradeoffs') {
			const y = d3
				.scaleBand()
				.domain(data.map((d) => d.name))
				.range([margin.top, innerHeight - margin.bottom])
				.padding(0.1);

			let xDomain: [number, number];

			let minValue = d3.max(data, (d) => Math.abs(d.value)) ?? 0;
			let maxValue = d3.max(data, (d) => Math.abs(d.value)) ?? 1;

			xDomain = [-1 * minValue, maxValue];

			const x = d3
				.scaleLinear()
				.domain(xDomain)
				.nice()
				.range([margin.left, innerWidth - margin.right]);

			const xMin = x.range()[0];
			const xMax = x.range()[1];

			drawHorizontalChart(
				svgElement,
				color,
				innerWidth,
				innerHeight,
				margin,
				x,
				y,
				xMin,
				xMax,
				tooltipSelection
			);
		} else {
			const x = d3
				.scaleBand()
				.domain(data.map((d) => d.name))
				.range([margin.left, innerWidth - margin.right])
				.padding(0.1);

			let yDomain: [number, number];
			if (axisRanges.length > 0) {
				const allMins = axisRanges.map((r) => r[0]);
				const allMaxs = axisRanges.map((r) => r[1]);
				yDomain = [Math.min(...allMins), Math.max(...allMaxs)];
			} else {
				yDomain = [0, d3.max(data, (d) => d.value) ?? 0];
			}

			const y = d3
				.scaleLinear()
				.domain(yDomain)
				.nice()
				.range([innerHeight - margin.bottom, margin.top]);

			const yMin = y.range()[0];
			const yMax = y.range()[1];

			drawVerticalChart(
				svgElement,
				color,
				innerWidth,
				innerHeight,
				margin,
				x,
				y,
				yMin,
				yMax,
				tooltipSelection
			);
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
		selected_objective_symbol = null;

		tooltip = document.createElement('div');
		tooltip.className = 'bar-tooltip';
		tooltip.style.opacity = '0';
		container.appendChild(tooltip);

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
		if (tooltip) {
			tooltip.remove();
		}
	});

	// --- Redraw chart on data/options/size change ---
	$: data, options, width, height, axisRanges, selected_objective_symbol, onSelect, drawChart();

	// Reset selected objective index when data changes
	$: if (data) {
		originalData = data;
		// Normalize data values between 0 and 1
		/*const values = data.map((d) => d.value);
		const minValue = Math.min(...values);
		const maxValue = Math.max(...values);
		if (maxValue > minValue) {
			data = data.map((d) => ({
				...d,
				value: (d.value - minValue) / (maxValue - minValue)
			}));
		} else {
			data = data.map((d) => ({
				...d,
				value: 0
			}));
		}*/
		//selected_objective_index = null;
	}
</script>

<!--
    Responsive container for the bar chart.
    Aspect ratio is fixed to 5:4 for now.
-->
<div bind:this={container} style="aspect-ratio: 4 / 4; width: 100%;">
	<svg bind:this={svg} style="width: 100%; height: 100%;" />
</div>

<style>
	.bar-tooltip {
		position: absolute;
		pointer-events: none;
		background: rgba(0, 0, 0, 0.75);
		color: #fff;
		padding: 4px 8px;
		border-radius: 4px;
		font-size: 12px;
		box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
		transition: opacity 120ms ease-in-out;
	}
</style>
