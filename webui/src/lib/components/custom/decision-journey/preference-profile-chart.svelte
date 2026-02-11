<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import type { PreferenceProfileEntry } from './journey-utils';
	import { formatNumber } from '$lib/helpers';

	interface Props {
		profile: PreferenceProfileEntry[];
	}

	let { profile }: Props = $props();

	let container: HTMLDivElement;
	let svg: SVGSVGElement;
	let width = $state(500);
	let resizeObserver: ResizeObserver;

	function scoreColor(score: number): string {
		const equalShare = profile.length > 0 ? 1 / profile.length : 0.5;
		if (score >= equalShare * 1.2) return '#059669'; // green – above average
		if (score >= equalShare * 0.8) return '#d97706'; // amber – around average
		return '#dc2626'; // red – below average
	}

	function drawChart() {
		if (!svg || profile.length === 0) return;

		// Sort by score descending
		const sorted = [...profile].sort((a, b) => b.preferenceScore - a.preferenceScore);

		const sel = d3.select(svg);
		sel.selectAll('*').remove();

		// Measure actual label widths using a temporary text element
		const tempG = sel.append('g').attr('opacity', 0);
		let maxLabelWidth = 0;
		for (const d of sorted) {
			const textEl = tempG.append('text').attr('font-size', '12px').text(d.label);
			const bbox = (textEl.node() as SVGTextElement).getBBox();
			maxLabelWidth = Math.max(maxLabelWidth, bbox.width);
			textEl.remove();
		}
		tempG.remove();

		const margin = { top: 8, right: 48, bottom: 8, left: 12 };
		const barHeight = 26;
		const gap = 8;
		const labelWidth = maxLabelWidth + 16;
		const innerWidth = Math.max(60, width - margin.left - margin.right - labelWidth);
		const computedHeight = margin.top + margin.bottom + sorted.length * (barHeight + gap) - gap;

		sel.attr('width', width).attr('height', computedHeight);

		const g = sel
			.append('g')
			.attr('transform', `translate(${margin.left + labelWidth},${margin.top})`);

		const xScale = d3.scaleLinear().domain([0, 1]).range([0, innerWidth]);

		for (let i = 0; i < sorted.length; i++) {
			const d = sorted[i];
			const y = i * (barHeight + gap);

			// Label
			g.append('text')
				.attr('x', -10)
				.attr('y', y + barHeight / 2)
				.attr('dy', '0.35em')
				.attr('text-anchor', 'end')
				.attr('font-size', '12px')
				.attr('fill', '#333')
				.text(d.label);

			// Bar background
			g.append('rect')
				.attr('x', 0)
				.attr('y', y)
				.attr('width', innerWidth)
				.attr('height', barHeight)
				.attr('fill', '#f3f4f6')
				.attr('rx', 3);

			// Bar fill
			g.append('rect')
				.attr('x', 0)
				.attr('y', y)
				.attr('width', Math.max(0, xScale(d.preferenceScore)))
				.attr('height', barHeight)
				.attr('fill', scoreColor(d.preferenceScore))
				.attr('rx', 3);

			// Score label
			g.append('text')
				.attr('x', xScale(d.preferenceScore) + 6)
				.attr('y', y + barHeight / 2)
				.attr('dy', '0.35em')
				.attr('font-size', '11px')
				.attr('fill', '#555')
				.text(`${formatNumber(d.preferenceScore * 100, 0)}%`);
		}
	}

	onMount(() => {
		resizeObserver = new ResizeObserver((entries) => {
			for (const entry of entries) {
				const rect = entry.contentRect;
				if (rect.width > 0) {
					width = rect.width;
				}
			}
		});
		resizeObserver.observe(container);
	});

	onDestroy(() => {
		resizeObserver?.disconnect();
	});

	$effect(() => {
		profile;
		width;
		drawChart();
	});
</script>

<div bind:this={container} class="w-full">
	<svg bind:this={svg} style="width: 100%;" />
</div>
