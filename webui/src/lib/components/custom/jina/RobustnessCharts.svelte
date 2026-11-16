<script lang="ts">
	/**
	 * The domain criterion of an evaluation at its thresholds: the share of scenarios meeting all
	 * thresholds as bars, the share meeting each threshold as a heatmap by design and objective,
	 * and the counts as a table. Clicking a design selects it; the selected design is highlighted.
	 */
	import type { EChartsOption } from 'echarts';
	import EChartsComponent from '$lib/components/custom/nimbus/echarts-component.svelte';
	import * as Table from '$lib/components/ui/table/index.js';
	import type { DomainCriterion, ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';
	import { cellOf, designAxis, domainCriterionShares, heatmapOption } from './robustness-charts';
	import { formatNumber, objectiveLabel } from './labels';

	let {
		problem,
		domainCriterion,
		objectives,
		nLeaves,
		selectedId = $bindable(null)
	}: {
		problem: ProblemInfo;
		domainCriterion: Record<string, DomainCriterion>;
		objectives: string[];
		nLeaves: number;
		selectedId?: number | null;
	} = $props();

	const SEQUENTIAL = ['#f8fafc', '#94a3b8', '#1e293b'];
	const BAR = '#64748b';
	const BAR_SELECTED = '#1e293b';

	let labels = $derived(objectives.map((o) => objectiveLabel(problem, o)));
	let shares = $derived(domainCriterionShares(domainCriterion, objectives, nLeaves));
	let rows = $derived(shares.perObjective.rows);

	let domainOption = $derived(
		heatmapOption({
			data: shares.perObjective,
			columns: labels,
			selectedId,
			range: [0, 1],
			rangeText: ['100%', '0%'],
			colors: SEQUENTIAL,
			label: (v) => (v === null ? '—' : `${Math.round(v * 100)}%`)
		})
	);

	let allOption = $derived<EChartsOption>({
		tooltip: { trigger: 'axis', valueFormatter: (v) => `${Math.round(Number(v) * 100)}%` },
		grid: { left: 60, right: 50, top: 10, bottom: 30 },
		xAxis: {
			type: 'value',
			min: 0,
			max: 1,
			axisLabel: { formatter: (v: number) => `${v * 100}%` }
		},
		yAxis: designAxis(rows, selectedId),
		series: [
			{
				type: 'bar',
				data: shares.all.map((v, i) => ({
					value: v ?? 0,
					itemStyle: { color: rows[i] === selectedId ? BAR_SELECTED : BAR }
				})),
				label: {
					show: true,
					position: 'right',
					formatter: (p: unknown) => `${Math.round((p as { value: number }).value * 100)}%`
				}
			}
		]
	});

	// Clicks select the design of the clicked cell or bar.
	const domainEvents = {
		click: (p: unknown) => {
			selectedId = rows[cellOf(p)[1]] ?? selectedId;
		}
	};
	const barEvents = {
		click: (p: { dataIndex: number }) => {
			selectedId = rows[p.dataIndex] ?? selectedId;
		}
	};

	// Heights grow with the designs; widths with the objectives, scrolling inside the card.
	let rowsHeight = $derived(Math.max(160, rows.length * 28 + 90));
	let columnsWidth = $derived(`min-width: ${120 + (labels.length + 1) * 90}px`);
</script>

<section class="space-y-3 rounded border bg-white p-3">
	<div>
		<h3 class="text-sm font-semibold">Domain criterion</h3>
		<p class="text-xs text-gray-500">
			Share of the {nLeaves} scenarios meeting all thresholds, and each threshold.
		</p>
	</div>
	<div style="height: {rowsHeight}px">
		<EChartsComponent option={allOption} events={barEvents} />
	</div>
	<div class="overflow-x-auto">
		<div style="height: {rowsHeight}px; {columnsWidth}">
			<EChartsComponent option={domainOption} events={domainEvents} />
		</div>
	</div>
	<div>
		<p class="text-xs text-gray-500">Scenarios meeting each threshold, of {nLeaves}.</p>
		<Table.Root>
			<Table.Header>
				<Table.Row>
					<Table.Head>Design</Table.Head>
					{#each objectives as obj, k (obj)}
						<Table.Head class="text-right">{labels[k]}</Table.Head>
					{/each}
					<Table.Head class="text-right">All thresholds</Table.Head>
					<Table.Head class="text-right">Mean</Table.Head>
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each rows as id (id)}
					{@const domain = domainCriterion[String(id)]}
					<Table.Row class={id === selectedId ? 'bg-blue-50 font-semibold' : ''}>
						<Table.Cell>#{id}</Table.Cell>
						{#each objectives as obj (obj)}
							<Table.Cell class="text-right">{domain.counts[obj] ?? '—'}</Table.Cell>
						{/each}
						<Table.Cell class="text-right">{domain.all_count}</Table.Cell>
						<Table.Cell class="text-right">{formatNumber(domain.mean_count)}</Table.Cell>
					</Table.Row>
				{/each}
			</Table.Body>
		</Table.Root>
	</div>
</section>
