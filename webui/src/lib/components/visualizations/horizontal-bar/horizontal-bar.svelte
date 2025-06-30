<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import { COLOR_PALETTE } from '../utils/colors';

	export let value: number;
	export let direction: 'max' | 'min';
	export let preference: number;
	export let range: [number, number];

	export let options: { showLabels: boolean; orientation: string } = {
		showLabels: true,
		orientation: 'vertical'
	};

	// Remove export let width/height, use internal variables
	let width = 500;
	let height = 400;

	let svg: SVGSVGElement;
	let container: HTMLDivElement;
	let resizeObserver: ResizeObserver;

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

		/* 		const y = d3
			.scaleBand()
			.domain(data.map((d) => d.name))
			.range([margin.top, innerHeight - margin.bottom])
			.padding(0.1);

		const x = d3
			.scaleLinear()
			.domain([0, d3.max(data, (d) => d.value) ?? 0])
			.nice()
			.range([margin.left, innerWidth - margin.right]);

		const xMax = x.range()[1];

		svgElement
			.append('g')
			.selectAll('rect')
			.data(data)
			.join('rect')
			.attr('y', (d) => y(d.name)!)
			.attr('height', y.bandwidth())
			.attr('x', (d) => (d.direction === 'max' ? x(0) : x(d.value)))
			.attr('width', (d) => (d.direction === 'max' ? x(d.value) - x(0) : xMax - x(d.value)))
			.attr('fill', (d, i) => color(d.name)); */

		svgElement.append('g').attr('transform', `translate(0,${margin.top})`).call(d3.axisTop(x));
		svgElement.append('g').attr('transform', `translate(${margin.left},0)`).call(d3.axisLeft(y));
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
	});
	onDestroy(() => {
		resizeObserver.disconnect();
	});

	$: value, direction, preference, range, options, width, height, drawChart();
</script>

<div bind:this={container} style="aspect-ratio: 5 / 4; width: 100%;">
	<svg bind:this={svg} style="width: 100%; height: 100%;" />
</div>
