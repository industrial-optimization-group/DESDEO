<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors';
	import { formatNumber } from '$lib/helpers';

	interface Props {
		options: Record<string, number>[];
		chosenIdx: number;
		objectiveKeys: string[];
		objectiveLabels: string[];
		objectiveMaximize: boolean[];
	}

	let { options, chosenIdx, objectiveKeys, objectiveLabels, objectiveMaximize }: Props = $props();

	let container: HTMLDivElement;
	let svg: SVGSVGElement;
	let width = $state(400);
	let height = $state(200);
	let resizeObserver: ResizeObserver;

	function drawChart() {
		if (!svg || options.length === 0 || objectiveKeys.length === 0) return;

		const margin = { top: 28, right: 16, bottom: 24, left: 16 };
		const innerWidth = width - margin.left - margin.right;
		const innerHeight = height - margin.top - margin.bottom;

		if (innerWidth < 40 || innerHeight < 30) return;

		const sel = d3.select(svg);
		sel.selectAll('*').remove();
		sel.attr('width', width).attr('height', height);

		const g = sel.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

		// X scale: one position per objective
		const xScale = d3
			.scalePoint<string>()
			.domain(objectiveKeys)
			.range([0, innerWidth])
			.padding(0.08);

		// Y scales: one per objective, fitted to the data range
		const yScales: Record<string, d3.ScaleLinear<number, number>> = {};
		for (const key of objectiveKeys) {
			const vals = options.map((o) => o[key]).filter((v) => v != null);
			const [lo, hi] = d3.extent(vals) as [number, number];
			const pad = (hi - lo) * 0.1 || 1;
			yScales[key] = d3
				.scaleLinear()
				.domain([lo - pad, hi + pad])
				.range([innerHeight, 0]);
		}

		// Draw axes
		for (let k = 0; k < objectiveKeys.length; k++) {
			const key = objectiveKeys[k];
			const x = xScale(key)!;
			const color = COLOR_PALETTE[k % COLOR_PALETTE.length];

			// Axis line
			g.append('g')
				.attr('transform', `translate(${x},0)`)
				.call(d3.axisLeft(yScales[key]).ticks(4).tickSize(-4))
				.selectAll('text')
				.attr('font-size', '9px');

			// Label
			const dir = objectiveMaximize[k] ? '\u2191' : '\u2193';
			g.append('text')
				.attr('x', x)
				.attr('y', -10)
				.attr('text-anchor', 'middle')
				.attr('font-size', '10px')
				.attr('font-weight', '600')
				.attr('fill', color)
				.text(`${dir} ${key}`);
		}

		// Line generator
		const lineGen = d3
			.line<[string, number]>()
			.x(([key]) => xScale(key)!)
			.y(([key, val]) => yScales[key](val))
			.curve(d3.curveLinear);

		// Draw non-chosen options first (muted)
		for (let i = 0; i < options.length; i++) {
			if (i === chosenIdx) continue;
			const pts: [string, number][] = objectiveKeys
				.filter((k) => options[i][k] != null)
				.map((k) => [k, options[i][k]]);

			g.append('path')
				.datum(pts)
				.attr('fill', 'none')
				.attr('stroke', '#94a3b8')
				.attr('stroke-width', 1.5)
				.attr('stroke-dasharray', '4,3')
				.attr('opacity', 0.6)
				.attr('d', lineGen);

			// Small dots
			for (const [key, val] of pts) {
				g.append('circle')
					.attr('cx', xScale(key)!)
					.attr('cy', yScales[key](val))
					.attr('r', 3)
					.attr('fill', '#94a3b8')
					.attr('opacity', 0.6);
			}

			// Label
			const lastKey = pts[pts.length - 1][0];
			g.append('text')
				.attr('x', xScale(lastKey)! + 6)
				.attr('y', yScales[lastKey](pts[pts.length - 1][1]))
				.attr('dy', '0.35em')
				.attr('font-size', '9px')
				.attr('fill', '#94a3b8')
				.text(`opt ${i + 1}`);
		}

		// Draw chosen option (highlighted)
		const chosenPts: [string, number][] = objectiveKeys
			.filter((k) => options[chosenIdx][k] != null)
			.map((k) => [k, options[chosenIdx][k]]);

		g.append('path')
			.datum(chosenPts)
			.attr('fill', 'none')
			.attr('stroke', '#3b82f6')
			.attr('stroke-width', 3)
			.attr('d', lineGen);

		// Larger dots for chosen
		for (let k = 0; k < objectiveKeys.length; k++) {
			const key = objectiveKeys[k];
			const val = options[chosenIdx][key];
			if (val == null) continue;
			const color = COLOR_PALETTE[k % COLOR_PALETTE.length];
			g.append('circle')
				.attr('cx', xScale(key)!)
				.attr('cy', yScales[key](val))
				.attr('r', 5)
				.attr('fill', color)
				.attr('stroke', '#fff')
				.attr('stroke-width', 1.5);
		}

		// Chosen label
		const lastKey = chosenPts[chosenPts.length - 1][0];
		g.append('text')
			.attr('x', xScale(lastKey)! + 8)
			.attr('y', yScales[lastKey](chosenPts[chosenPts.length - 1][1]))
			.attr('dy', '0.35em')
			.attr('font-size', '10px')
			.attr('font-weight', '600')
			.attr('fill', '#3b82f6')
			.text('chosen');
	}

	onMount(() => {
		resizeObserver = new ResizeObserver((entries) => {
			for (const entry of entries) {
				const rect = entry.contentRect;
				if (rect.width > 0 && rect.height > 0) {
					width = rect.width;
					height = rect.height;
				}
			}
		});
		resizeObserver.observe(container);
	});

	onDestroy(() => {
		resizeObserver?.disconnect();
	});

	$effect(() => {
		options;
		chosenIdx;
		objectiveKeys;
		width;
		height;
		drawChart();
	});
</script>

<div bind:this={container} class="h-full w-full">
	<svg bind:this={svg} class="h-full w-full" />
</div>
