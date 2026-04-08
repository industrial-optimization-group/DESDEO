<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import type { JourneyStep, WhatIfSimulation } from './journey-utils';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors';
	import { formatNumber } from '$lib/helpers';

	interface Props {
		steps: JourneyStep[];
		objectiveKeys: string[];
		objectiveLabels: string[];
		objectiveMaximize: boolean[];
		tooltipEl?: HTMLDivElement;
		onStepClick?: (step: JourneyStep) => void;
		whatIfSimulation?: WhatIfSimulation | null;
		selectedIteration?: number | null;
	}

	let { steps, objectiveKeys, objectiveLabels, objectiveMaximize, tooltipEl = $bindable(), onStepClick, whatIfSimulation = null, selectedIteration = null }: Props = $props();

	let container: HTMLDivElement;
	let svg: SVGSVGElement;
	let width = $state(500);
	let height = $state(400);
	let resizeObserver: ResizeObserver;

	function fmtPct(val: number): string {
		const sign = val > 0 ? '+' : '';
		return `${sign}${formatNumber(val, 1)}%`;
	}

	function drawChart() {
		if (!svg || steps.length === 0 || objectiveKeys.length === 0) return;

		const legendRowHeight = 22;
		const legendRows = Math.ceil(objectiveKeys.length / 3);
		const legendTotalHeight = legendRows * legendRowHeight + 8;

		const margin = { top: 16, right: 24, bottom: 36 + legendTotalHeight, left: 60 };
		const innerWidth = width - margin.left - margin.right;
		const innerHeight = height - margin.top - margin.bottom;

		if (innerWidth < 40 || innerHeight < 40) return;

		const sel = d3.select(svg);
		sel.selectAll('*').remove();
		sel.attr('width', width).attr('height', height);

		const g = sel.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

		if (!tooltipEl) return;
		const tooltip = d3.select(tooltipEl);

		// X scale: iteration number (extend domain for what-if steps if needed)
		const iterations = steps.map((s) => s.iteration);
		if (whatIfSimulation?.steps) {
			for (const s of whatIfSimulation.steps) iterations.push(s.iteration);
		}
		const xMin = d3.min(iterations)!;
		const xMax = d3.max(iterations)!;
		const xScale = d3.scaleLinear().domain([xMin, xMax]).range([0, innerWidth]);

		// Y scale: normalized 0–1
		const yScale = d3.scaleLinear().domain([0, 1]).range([innerHeight, 0]);

		// Grid lines
		g.append('g')
			.selectAll('line')
			.data(yScale.ticks(5))
			.join('line')
			.attr('x1', 0)
			.attr('x2', innerWidth)
			.attr('y1', (d) => yScale(d))
			.attr('y2', (d) => yScale(d))
			.attr('stroke', '#e5e7eb')
			.attr('stroke-dasharray', '3,3');

		// Selected iteration highlight band
		if (selectedIteration != null) {
			const bandHalf = innerWidth / Math.max(xMax - xMin, 1) * 0.35;
			const cx = xScale(selectedIteration);
			g.append('rect')
				.attr('x', cx - bandHalf)
				.attr('y', 0)
				.attr('width', bandHalf * 2)
				.attr('height', innerHeight)
				.attr('fill', '#3b82f6')
				.attr('opacity', 0.08)
				.attr('rx', 4);
			g.append('line')
				.attr('x1', cx)
				.attr('x2', cx)
				.attr('y1', 0)
				.attr('y2', innerHeight)
				.attr('stroke', '#3b82f6')
				.attr('stroke-width', 1.5)
				.attr('stroke-dasharray', '4,3')
				.attr('opacity', 0.35);
		}

		// Axes
		const tickCount = Math.min(steps.length, 10);
		g.append('g')
			.attr('transform', `translate(0,${innerHeight})`)
			.call(
				d3
					.axisBottom(xScale)
					.ticks(tickCount)
					.tickFormat((d) => String(Math.round(d as number))),
			);

		g.append('text')
			.attr('x', innerWidth / 2)
			.attr('y', innerHeight + 32)
			.attr('fill', '#666')
			.attr('text-anchor', 'middle')
			.attr('font-size', '12px')
			.text('Iteration');

		g.append('g').call(d3.axisLeft(yScale).ticks(5));

		g.append('text')
			.attr('transform', 'rotate(-90)')
			.attr('x', -innerHeight / 2)
			.attr('y', -44)
			.attr('fill', '#666')
			.attr('text-anchor', 'middle')
			.attr('font-size', '11px')
			.text('Normalized value');

		// Lines + dots for each objective
		for (let k = 0; k < objectiveKeys.length; k++) {
			const key = objectiveKeys[k];
			const color = COLOR_PALETTE[k % COLOR_PALETTE.length];
			const label = objectiveLabels[k] ?? key;

			const data = steps.filter((s) => s.normalizedValues[key] != null);

			const line = d3
				.line<JourneyStep>()
				.x((d) => xScale(d.iteration))
				.y((d) => yScale(d.normalizedValues[key]))
				.curve(d3.curveLinear);

			g.append('path')
				.datum(data)
				.attr('fill', 'none')
				.attr('stroke', color)
				.attr('stroke-width', 2.5)
				.attr('d', line);

			g.selectAll(`.dot-${k}`)
				.data(data)
				.join('circle')
				.attr('cx', (d) => xScale(d.iteration))
				.attr('cy', (d) => yScale(d.normalizedValues[key]))
				.attr('r', 5)
				.attr('fill', color)
				.attr('stroke', '#fff')
				.attr('stroke-width', 1.5)
				.attr('cursor', 'pointer')
				.on('mouseenter', (_event: MouseEvent, d: JourneyStep) => {
					// Build tooltip: values + prioritized/sacrificed + max 2 alt % deltas
					let html = `<div style="font-weight:600;margin-bottom:4px;">Iteration ${d.iteration}</div>`;
					for (let j = 0; j < objectiveKeys.length; j++) {
						const oKey = objectiveKeys[j];
						const raw = d.rawValues[oKey];
						if (raw == null) continue;
						const oLabel = objectiveLabels[j] ?? oKey;
						const oColor = COLOR_PALETTE[j % COLOR_PALETTE.length];
						const dir = objectiveMaximize[j] ? 'max' : 'min';
						html += `<div style="display:flex;align-items:center;gap:4px;">`;
						html += `<span style="width:8px;height:8px;border-radius:50%;background:${oColor};flex-shrink:0;"></span>`;
						html += `<span>${oLabel} (${dir}): <b>${formatNumber(raw, 4)}</b></span>`;
						html += `</div>`;
					}

					if (d.tradeoffs && d.tradeoffs.length > 0 && d.alternativeDeltas) {
						html += `<div style="border-top:1px solid #e5e7eb;margin-top:6px;padding-top:5px;">`;

						// Prioritized / sacrificed
						const prioritized = d.tradeoffs
							.filter((t) => t.normalizedRank <= 0.25)
							.map((t) => objectiveLabels[objectiveKeys.indexOf(t.key)] ?? t.key);
						const sacrificed = d.tradeoffs
							.filter((t) => t.normalizedRank >= 0.75)
							.map((t) => objectiveLabels[objectiveKeys.indexOf(t.key)] ?? t.key);

						if (prioritized.length > 0) {
							html += `<div style="margin-bottom:3px;"><span style="color:#059669;font-weight:600;">Prioritized:</span> ${prioritized.join(', ')}</div>`;
						}
						if (sacrificed.length > 0) {
							html += `<div style="margin-bottom:3px;"><span style="color:#dc2626;font-weight:600;">Sacrificed:</span> ${sacrificed.join(', ')}</div>`;
						}

						// Show at most 2 alternatives with % deltas (compact single-line each)
						const maxShow = 2;
						const alts = d.alternativeDeltas;
						const shown = alts.slice(0, maxShow);
						for (const alt of shown) {
							const parts: string[] = [];
							for (let j = 0; j < objectiveKeys.length; j++) {
								const oKey = objectiveKeys[j];
								const pct = alt.pctDeltas[oKey];
								if (pct == null) continue;
								const isGood = objectiveMaximize[j] ? pct > 0 : pct < 0;
								const isBad = objectiveMaximize[j] ? pct < 0 : pct > 0;
								const c = isGood ? '#059669' : isBad ? '#dc2626' : '#666';
								parts.push(`<span style="color:${c}">${fmtPct(pct)}</span>`);
							}
							html += `<div style="margin-top:2px;">\u0394 opt ${alt.optionIdx + 1}: ${parts.join(' · ')}</div>`;
						}

						if (alts.length > maxShow) {
							html += `<div style="margin-top:4px;color:#6b7280;font-style:italic;">Click for full details (+${alts.length - maxShow} more)</div>`;
						} else if (alts.length > 0) {
							html += `<div style="margin-top:4px;color:#6b7280;font-style:italic;">Click for details</div>`;
						}

						html += `</div>`;
					}

					tooltip.html(html).style('opacity', '1');
				})
				.on('mousemove', (event: MouseEvent) => {
					const parentRect = tooltipEl.parentElement!.getBoundingClientRect();
					const tipRect = tooltipEl.getBoundingClientRect();
					const gap = 12;

					// Flip above cursor if tooltip would overflow bottom
					let top = event.clientY - parentRect.top + gap;
					if (event.clientY + gap + tipRect.height > parentRect.bottom) {
						top = event.clientY - parentRect.top - tipRect.height - gap;
					}

					// Flip left of cursor if tooltip would overflow right
					let left = event.clientX - parentRect.left + gap;
					if (event.clientX + gap + tipRect.width > parentRect.right) {
						left = event.clientX - parentRect.left - tipRect.width - gap;
					}

					tooltip
						.style('left', `${left}px`)
						.style('top', `${top}px`);
				})
				.on('mouseleave', () => {
					tooltip.style('opacity', '0');
				})
				.on('click', (_event: MouseEvent, d: JourneyStep) => {
					if (d.alternativeDeltas && onStepClick) {
						onStepClick(d);
					}
				});
		}

		// What-if simulation overlay (dashed lines + hollow circles)
		if (whatIfSimulation?.steps && whatIfSimulation.steps.length > 0) {
			const branchIdx = whatIfSimulation.branchStepIdx;
			const branchStep = branchIdx >= 0 && branchIdx < steps.length ? steps[branchIdx] : null;

			for (let k = 0; k < objectiveKeys.length; k++) {
				const key = objectiveKeys[k];
				const color = COLOR_PALETTE[k % COLOR_PALETTE.length];

				// Build combined path: branch point + simulated steps
				const simData: JourneyStep[] = [];
				if (branchStep && branchStep.normalizedValues[key] != null) {
					simData.push(branchStep);
				}
				for (const s of whatIfSimulation.steps) {
					if (s.normalizedValues[key] != null) simData.push(s);
				}

				if (simData.length < 2) continue;

				// Dashed line
				const simLine = d3
					.line<JourneyStep>()
					.x((d) => xScale(d.iteration))
					.y((d) => yScale(d.normalizedValues[key]))
					.curve(d3.curveLinear);

				g.append('path')
					.datum(simData)
					.attr('fill', 'none')
					.attr('stroke', color)
					.attr('stroke-width', 2.5)
					.attr('stroke-dasharray', '6,4')
					.attr('opacity', 0.7)
					.attr('d', simLine);

				// Hollow circle dots (skip branch point — it's already rendered)
				const simOnly = whatIfSimulation.steps.filter((s) => s.normalizedValues[key] != null);
				g.selectAll(`.sim-dot-${k}`)
					.data(simOnly)
					.join('circle')
					.attr('cx', (d) => xScale(d.iteration))
					.attr('cy', (d) => yScale(d.normalizedValues[key]))
					.attr('r', 5)
					.attr('fill', '#fff')
					.attr('stroke', color)
					.attr('stroke-width', 2)
					.attr('opacity', 0.85);
			}

			// "what-if" label at the end of the branch
			const lastSim = whatIfSimulation.steps[whatIfSimulation.steps.length - 1];
			const firstKey = objectiveKeys[0];
			if (lastSim.normalizedValues[firstKey] != null) {
				g.append('text')
					.attr('x', xScale(lastSim.iteration) + 8)
					.attr('y', yScale(lastSim.normalizedValues[firstKey]))
					.attr('fill', '#9ca3af')
					.attr('font-size', '10px')
					.attr('font-style', 'italic')
					.attr('dominant-baseline', 'middle')
					.text('what-if');
			}
		}

		// Legend: horizontal row(s) below the plot
		const legendY = innerHeight + 50;
		const colWidth = Math.floor(innerWidth / Math.min(objectiveKeys.length, 3));

		for (let k = 0; k < objectiveKeys.length; k++) {
			const color = COLOR_PALETTE[k % COLOR_PALETTE.length];
			const label = objectiveLabels[k] ?? objectiveKeys[k];
			const dir = objectiveMaximize[k] ? '\u2191' : '\u2193'; // ↑ or ↓
			const col = k % 3;
			const row = Math.floor(k / 3);
			const x = col * colWidth;
			const y = legendY + row * legendRowHeight;

			g.append('rect')
				.attr('x', x)
				.attr('y', y)
				.attr('width', 12)
				.attr('height', 12)
				.attr('rx', 2)
				.attr('fill', color);

			g.append('text')
				.attr('x', x + 18)
				.attr('y', y + 10)
				.attr('font-size', '11px')
				.attr('fill', '#444')
				.text(`${dir} ${label}`);
		}
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
		steps;
		objectiveKeys;
		objectiveLabels;
		objectiveMaximize;
		tooltipEl;
		whatIfSimulation;
		selectedIteration;
		width;
		height;
		drawChart();
	});
</script>

<div bind:this={container} class="h-full w-full overflow-hidden">
	<svg bind:this={svg} class="h-full w-full" />
</div>
