<script lang="ts">
	/**
	 * Charts and table of an antifragility analysis: the antifragility index on a diverging scale
	 * with Taleb classes, upside against downside per objective, and the index with gain / loss
	 * counts. Clicking a design selects it; the selected design is highlighted.
	 */
	import type { EChartsOption } from 'echarts';
	import EChartsComponent from '$lib/components/custom/nimbus/echarts-component.svelte';
	import * as Table from '$lib/components/ui/table/index.js';
	import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';
	import {
		antifragilityHeatmap,
		cellOf,
		evaluatedDesigns,
		heatmapOption,
		upsideDownside
	} from './robustness-charts';
	import { formatNumber, objectiveLabel } from './labels';
	import type { AntifragilityResult } from './types';

	let {
		problem,
		result,
		baselineLeaf,
		selectedId = $bindable(null)
	}: {
		problem: ProblemInfo;
		result: AntifragilityResult;
		baselineLeaf: string;
		selectedId?: number | null;
	} = $props();

	const DIVERGING = ['#b91c1c', '#f3f4f6', '#15803d'];
	const POINT = '#64748b';
	const POINT_SELECTED = '#1e293b';
	const TALEB_STYLES: Record<string, string> = {
		fragile: 'bg-red-100 text-red-800',
		robust: 'bg-gray-100 text-gray-800',
		antifragile: 'bg-green-100 text-green-800'
	};

	let labels = $derived(result.objectives.map((o) => objectiveLabel(problem, o)));
	let fragility = $derived(antifragilityHeatmap(result.analysis.antifragility, result.objectives));
	let points = $derived(upsideDownside(result.analysis.antifragility, result.objectives));
	let rows = $derived(evaluatedDesigns(result.analysis.antifragility));

	// The cell colour is the antifragility index; with floors the label is the Taleb class, and
	// fragile cells are outlined.
	let hasClasses = $derived(fragility.classes.some((c) => c !== null));
	let fragilityOption = $derived(
		heatmapOption({
			data: fragility,
			columns: labels,
			selectedId,
			range: [-1, 1],
			rangeText: ['+1 (gains)', '−1 (losses)'],
			colors: DIVERGING,
			label: (v, i) => {
				const cls = fragility.classes[i];
				if (hasClasses) return cls === 'fragile' ? '{fragile|fragile}' : (cls ?? '—');
				return v === null ? '—' : formatNumber(v, 2);
			},
			cellStyle: (i) =>
				fragility.classes[i] === 'fragile' ? { borderColor: '#7f1d1d', borderWidth: 2 } : undefined,
			tooltipExtra: (i) => (fragility.classes[i] ? ` (${fragility.classes[i]})` : '')
		})
	);

	// One upside-against-downside scatter per objective, each on its own scale.
	let scatterOptions = $derived(
		result.objectives.map((obj, k): EChartsOption => {
			const own = points.filter((p) => p.objective === obj);
			const top = Math.max(...own.flatMap((p) => [p.upside, p.downside]), 0) * 1.1 || 1;
			return {
				title: {
					text: labels[k],
					textStyle: { fontSize: 11, fontWeight: 'normal' },
					left: 'center'
				},
				tooltip: {
					trigger: 'item',
					alwaysShowContent: false,
					enterable: false,
					hideDelay: 0,
					formatter: (p: unknown) => {
						const { data } = p as { data: { designId: number; value: [number, number] } };
						return `#${data.designId} — ${labels[k]}<br>downside ${formatNumber(data.value[0], 3)}, upside ${formatNumber(data.value[1], 3)}`;
					}
				},
				grid: { left: 45, right: 15, top: 30, bottom: 35 },
				xAxis: {
					type: 'value',
					name: 'Downside',
					nameLocation: 'middle',
					nameGap: 22,
					min: 0,
					max: top,
					splitNumber: 3,
					axisLabel: { formatter: (v: number) => formatNumber(v, 2), hideOverlap: true }
				},
				yAxis: {
					type: 'value',
					name: 'Upside',
					min: 0,
					max: top,
					splitNumber: 3,
					axisLabel: { formatter: (v: number) => formatNumber(v, 2), hideOverlap: true }
				},
				series: [
					{
						type: 'scatter',
						colorBy: 'series',
						data: own.map((p) => ({
							value: [p.downside, p.upside],
							designId: p.designId,
							symbolSize: p.designId === selectedId ? 14 : 9,
							itemStyle: { color: p.designId === selectedId ? POINT_SELECTED : POINT }
						})),
						label: {
							show: true,
							position: 'right',
							fontSize: 10,
							formatter: (p: unknown) => `#${(p as { data: { designId: number } }).data.designId}`
						},
						// Coinciding points would stack their labels; the tooltip still names each design.
						labelLayout: { hideOverlap: true },
						markLine: {
							silent: true,
							symbol: 'none',
							lineStyle: { type: 'dashed', color: '#9ca3af' },
							data: [[{ coord: [0, 0] }, { coord: [top, top] }]]
						}
					}
				]
			};
		})
	);

	// Clicks select the design of the clicked cell or point.
	const fragilityEvents = {
		click: (p: unknown) => {
			selectedId = fragility.rows[cellOf(p)[1]] ?? selectedId;
		}
	};
	const scatterEvents = {
		click: (p: unknown) => {
			const id = (p as { data: { designId?: number } }).data.designId;
			if (typeof id === 'number') selectedId = id;
		}
	};

	// Heights grow with the designs; widths with the objectives, scrolling inside the card.
	let rowsHeight = $derived(Math.max(160, rows.length * 28 + 90));
	let columnsWidth = $derived(`min-width: ${120 + (labels.length + 1) * 90}px`);
</script>

<section class="space-y-3 rounded border bg-white p-3">
	<div>
		<h3 class="text-sm font-semibold">Antifragility relative to {baselineLeaf}</h3>
		<p class="text-xs text-gray-500">
			Colour = antifragility index, from −1 (only losses, red) to +1 (only gains, green).
			{hasClasses
				? 'Label = Taleb class from the floors; fragile cells are outlined.'
				: 'Give floors to see Taleb classes.'}
			Below: upside against downside per objective, each on its own scale; above the dashed line gains
			outweigh losses.
		</p>
	</div>
	<div class="overflow-x-auto">
		<div style="height: {rowsHeight}px; {columnsWidth}">
			<EChartsComponent option={fragilityOption} events={fragilityEvents} />
		</div>
	</div>
	<div class="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-2">
		{#each scatterOptions as option, k (result.objectives[k])}
			<div style="height: 220px">
				<EChartsComponent {option} events={scatterEvents} />
			</div>
		{/each}
	</div>
	<div>
		<p class="text-xs text-gray-500">
			Index from −1 (only losses) to 1 (only gains), with gains / losses in scenarios.
		</p>
		<Table.Root>
			<Table.Header>
				<Table.Row>
					<Table.Head>Design</Table.Head>
					{#each result.objectives as obj, k (obj)}
						<Table.Head class="text-right">{labels[k]}</Table.Head>
					{/each}
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each rows as id (id)}
					<Table.Row class={id === selectedId ? 'bg-blue-50 font-semibold' : ''}>
						<Table.Cell>#{id}</Table.Cell>
						{#each result.objectives as obj (obj)}
							{@const summary = result.analysis.antifragility[String(id)].objectives[obj]}
							<Table.Cell class="text-right">
								{#if summary}
									{formatNumber(summary.antifragility, 3)}
									<span class="text-xs text-gray-500">
										({summary.n_gain}/{summary.n_loss})
									</span>
									{#if summary.taleb_class}
										<span class="ml-1 rounded px-1 text-xs {TALEB_STYLES[summary.taleb_class]}">
											{summary.taleb_class}
										</span>
									{/if}
								{:else}
									—
								{/if}
							</Table.Cell>
						{/each}
					</Table.Row>
				{/each}
			</Table.Body>
		</Table.Root>
		<p class="mt-1 text-xs text-gray-600">
			Objectives with an upside for some design:
			{result.analysis.antifragile_objectives.length > 0
				? result.analysis.antifragile_objectives.map((o) => objectiveLabel(problem, o)).join(', ')
				: 'none'}
		</p>
	</div>
</section>
