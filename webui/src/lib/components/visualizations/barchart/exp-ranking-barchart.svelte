<script lang="ts">
	/**
	 * Barchart.svelte
	 * --------------------------------
	 * Responsive bar chart component using D3 for visualizing trade-offs.
	 *
	 * @author Giomara Larraga <glarragw@jyu.fi>
	 * @created February 2026
	 *
	 * @props
	 * - data: Array<{ name: string; symbol: string; value: number; direction: 'max' | 'min' }>
	 * - selected_objective_symbol: string | null — Symbol of the selected objective to exclude from chart
	 * - options: { showLabels: boolean }
	 *
	 * @features
	 * - Horizontal bars sorted by absolute value
	 * - Consistent color mapping per objective
	 * - Responsive to container size
	 * - Excludes selected objective from visualization
	 */

	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import { COLOR_PALETTE } from '../utils/colors';

	// --- Props ---
	export let data: { name: string; symbol: string; value: number; direction: 'max' | 'min' }[] = [];
	export let axisRanges: [number, number][] = [];
	export let options: { showLabels: boolean } = {
		showLabels: true
	};

	export let onSelect: ((event: { value: string }) => void) | undefined = undefined;

	export let selected_objective_symbol: string | null = null;

	export let selectedBarSymbol: string | null = null;

	let selected_objective_name = '';

	$: {
		const obj = data.find((d) => d.symbol === selected_objective_symbol);
		selected_objective_name = obj ? obj.name : '';
	}

	// --- Internal state ---
	let width = 500;
	let height = 200;
	let svg: SVGSVGElement;
	let container: HTMLDivElement;
	let resizeObserver: ResizeObserver;
	let colorDict: Record<string, string> = {};
	//let selectedBarSymbol: string | null = null;

	function createColorDictionary(
		data: { name: string; symbol: string; value: number; direction: 'max' | 'min' }[]
	) {
		const color = d3
			.scaleOrdinal<string>()
			.domain(data.map((d) => d.name))
			.range(COLOR_PALETTE);
		const colorDict: Record<string, string> = {};
		data.forEach((d) => {
			colorDict[d.symbol] = color(d.name);
		});
		return colorDict;
	}

	function drawHorizontalChart(
		svgElement: d3.Selection<SVGGElement, unknown, null, undefined>,
		color: Record<string, string>,
		data_to_render: { name: string; symbol: string; value: number; direction: 'max' | 'min' }[],
		innerWidth: number,
		innerHeight: number,
		margin: { top: number; right: number; bottom: number; left: number },
		x: d3.ScaleLinear<number, number>,
		y: d3.ScaleBand<string>,
		xMin: number,
		xMax: number
	) {
		svgElement
			.append('g')
			.selectAll('rect')
			.data(data_to_render)
			.join('rect')
			.attr('y', (d) => y(d.name)!)
			.attr('height', y.bandwidth())
			.attr('x', x(0))
			.attr('width', (d) => Math.abs(x(d.value) - x(0)))
			.attr('fill', (d) => color[d.symbol])
			.attr('stroke', (d) => (selectedBarSymbol === d.symbol ? '#3b82f6' : 'none'))
			.attr('stroke-width', (d) => (selectedBarSymbol === d.symbol ? 3 : 0))
			.style('cursor', 'pointer')
			.on('click', (event, d) => {
				// Toggle selection: deselect if clicking the same bar
				selectedBarSymbol = selectedBarSymbol === d.symbol ? null : d.symbol;
				if (onSelect) {
					onSelect({ value: selectedBarSymbol ?? '' });
				}
				drawChart();
			});

		// Add rank numbers on the right side
		svgElement
			.append('g')
			.selectAll('text')
			.data(data_to_render)
			.join('text')
			.attr('x', xMax + 5)
			.attr('y', (d) => y(d.name)! + y.bandwidth() / 2)
			.attr('dy', '0.35em')
			.attr('font-size', '12px')
			.attr('fill', '#666')
			.text((d, i) => `#${i + 1}`);

		// Draw axes
		svgElement.append('g').attr('transform', `translate(0,${margin.top})`).call(d3.axisTop(x));
		svgElement.append('g').attr('transform', `translate(${margin.left},0)`).call(d3.axisLeft(y));
	}

	function drawChart(): void {
		let margin = { top: 0, right: 10, bottom: 0, left: 30 };

		// Adapt left margin based on longest objective name
		const longestNameLength = d3.max(data, (d) => d.name.length) ?? 0;
		margin.left = Math.max(10, longestNameLength * 5);

		colorDict = createColorDictionary(data);

		let data_to_use = [...data];
		if (selected_objective_symbol !== null && selected_objective_symbol !== undefined) {
			data_to_use = data_to_use.filter((d) => d.symbol !== selected_objective_symbol);
			data_to_use = data_to_use.sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
		}

		const innerWidth = width - margin.left - margin.right;
		const innerHeight = height - margin.top - margin.bottom;

		d3.select(svg).selectAll('*').remove();

		const svgElement = d3
			.select(svg)
			.attr('width', width)
			.attr('height', height)
			.append('g')
			.attr('transform', `translate(${margin.left}, ${margin.top})`);
		const y = d3
			.scaleBand()
			.domain(data_to_use.map((d) => d.name))
			.range([margin.top, innerHeight - margin.bottom])
			.padding(0.1);

		let xDomain: [number, number];

		let maxValue = d3.max(data_to_use, (d) => Math.abs(d.value)) ?? 1;

		xDomain = [0, maxValue];

		const x = d3
			.scaleLinear()
			.domain(xDomain)
			.nice()
			.range([margin.left, innerWidth - margin.right]);

		const xMin = x.range()[0];
		const xMax = x.range()[1];

		drawHorizontalChart(
			svgElement,
			colorDict,
			data_to_use,
			innerWidth,
			innerHeight,
			margin,
			x,
			y,
			xMin,
			xMax
		);

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

	$: data,
		options,
		width,
		height,
		selectedBarSymbol,
		axisRanges,
		selected_objective_symbol,
		onSelect,
		drawChart();
</script>

<div bind:this={container} style="aspect-ratio: 4 / 2; width: 100%;">
	<svg bind:this={svg} style="width: 100%; height: 100%;" />
</div>
