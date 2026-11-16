/* Data and ECharts options for the robustness charts: evaluated outcomes, domain criterion, antifragility. */

import type { EChartsOption } from 'echarts';
import type { Antifragility, DomainCriterion, LeafOutcome } from '$lib/gen/endpoints/DESDEOFastAPI';
import { formatNumber } from './labels';

/** Outcomes of an evaluation by design id (as a string) and leaf. */
export type Outcomes = Record<string, Record<string, LeafOutcome>>;

/** Rows of designs by columns of objectives; each cell is [column, row, value or null]. */
export interface HeatmapData {
	rows: number[];
	columns: string[];
	cells: [number, number, number | null][];
}

/** The design ids keying a record, in ascending order. */
export function evaluatedDesigns(byDesign: Record<string, unknown>): number[] {
	return Object.keys(byDesign)
		.map(Number)
		.sort((a, b) => a - b);
}

/** The leaves of the outcomes in order of first appearance. */
export function evaluatedLeaves(outcomes: Outcomes): string[] {
	return [...new Set(Object.values(outcomes).flatMap((leaves) => Object.keys(leaves)))];
}

/** The objectives with a value in the outcomes, in order of first appearance. */
export function evaluatedObjectives(outcomes: Outcomes): string[] {
	return [
		...new Set(
			Object.values(outcomes).flatMap((leaves) =>
				Object.values(leaves).flatMap((outcome) => Object.keys(outcome.objectives ?? {}))
			)
		)
	];
}

/** Objective values by design, leaf and objective, from the leaves where the evaluation succeeded. */
export function evaluatedLeafObjectives(
	outcomes: Outcomes
): Record<number, Record<string, Record<string, number>>> {
	return Object.fromEntries(
		Object.entries(outcomes).map(([id, leaves]) => [
			Number(id),
			Object.fromEntries(
				Object.entries(leaves).flatMap(([leaf, outcome]) =>
					outcome.status ? [[leaf, outcome.objectives ?? {}]] : []
				)
			)
		])
	);
}

function heatmap(
	rows: number[],
	columns: string[],
	value: (row: number, column: string) => number | null | undefined
): HeatmapData {
	return {
		rows,
		columns,
		cells: rows.flatMap((row, y) =>
			columns.map((column, x): [number, number, number | null] => [
				x,
				y,
				value(row, column) ?? null
			])
		)
	};
}

/** Whether a value meets a threshold: at most it for a minimised, at least it for a maximised objective. */
export function meetsThreshold(value: number, threshold: number, maximize: boolean): boolean {
	return maximize ? value >= threshold : value <= threshold;
}

/**
 * Shares of the `nLeaves` scenarios where each design meets the thresholds: of all thresholds at
 * once, and of each objective's threshold. Without leaves the shares are null.
 */
export function domainCriterionShares(
	domainCriterion: Record<string, DomainCriterion>,
	objectives: string[],
	nLeaves: number
): { all: (number | null)[]; perObjective: HeatmapData } {
	const rows = evaluatedDesigns(domainCriterion);
	const share = (count: number | undefined) =>
		nLeaves > 0 && count !== undefined ? count / nLeaves : null;
	return {
		all: rows.map((id) => share(domainCriterion[String(id)].all_count)),
		perObjective: heatmap(rows, objectives, (id, obj) =>
			share(domainCriterion[String(id)].counts[obj])
		)
	};
}

/** The antifragility index by design and objective, with the Taleb class of each cell. */
export function antifragilityHeatmap(
	antifragility: Record<string, Antifragility>,
	objectives: string[]
): HeatmapData & { classes: (string | null)[] } {
	const rows = evaluatedDesigns(antifragility);
	const data = heatmap(
		rows,
		objectives,
		(id, obj) => antifragility[String(id)]?.objectives[obj]?.antifragility
	);
	const classes = data.cells.map(
		([x, y]) => antifragility[String(rows[y])]?.objectives[objectives[x]]?.taleb_class ?? null
	);
	return { ...data, classes };
}

/** The upside and downside of each design and objective that has both. */
export function upsideDownside(
	antifragility: Record<string, Antifragility>,
	objectives: string[]
): { designId: number; objective: string; upside: number; downside: number }[] {
	return evaluatedDesigns(antifragility).flatMap((id) =>
		objectives.flatMap((objective) => {
			const summary = antifragility[String(id)]?.objectives[objective];
			return summary?.upside != null && summary.downside !== null
				? [{ designId: id, objective, upside: summary.upside, downside: summary.downside }]
				: [];
		})
	);
}

/** Design labels on a category axis, the selected one bold. */
export function designAxis(rows: number[], selectedId: number | null) {
	return {
		type: 'category' as const,
		data: rows.map((id) => `#${id}`),
		inverse: true,
		axisLabel: {
			formatter: (value: string) => (value === `#${selectedId}` ? `{sel|${value}}` : value),
			rich: { sel: { fontWeight: 'bold' as const, color: '#1d4ed8' } }
		}
	};
}

type Cell = [number, number, number | string];

/** The [column, row, value] of a heatmap event, whose data is the cell or an object holding it. */
export function cellOf(p: unknown): Cell {
	return (p as { value: Cell }).value;
}

/** A heatmap of designs by columns with a horizontal colour legend. */
export function heatmapOption(spec: {
	data: HeatmapData;
	columns: string[];
	selectedId: number | null;
	range: [number, number];
	rangeText: [string, string];
	colors: string[];
	label: (value: number | null, index: number) => string;
	cellStyle?: (index: number) => Record<string, unknown> | undefined;
	tooltipExtra?: (index: number) => string;
}): EChartsOption {
	const { data, columns } = spec;
	return {
		tooltip: {
			trigger: 'item',
			formatter: (p: unknown) => {
				const [x, y, v] = cellOf(p);
				const extra = spec.tooltipExtra?.((p as { dataIndex: number }).dataIndex) ?? '';
				return `#${data.rows[y]} — ${columns[x]}: ${typeof v === 'number' ? formatNumber(v) : '—'}${extra}`;
			}
		},
		grid: { left: 60, right: 20, top: 10, bottom: 80 },
		xAxis: {
			type: 'category',
			data: columns,
			axisLabel: { interval: 0, width: 85, overflow: 'break', lineHeight: 12, fontSize: 11 }
		},
		yAxis: designAxis(data.rows, spec.selectedId),
		visualMap: {
			min: spec.range[0],
			max: spec.range[1],
			calculable: false,
			orient: 'horizontal',
			left: 'right',
			bottom: 0,
			itemHeight: 80,
			text: spec.rangeText,
			inRange: { color: spec.colors }
		},
		series: [
			{
				type: 'heatmap',
				data: data.cells.map(([x, y, v], index) => {
					const value: Cell = [x, y, v ?? '-'];
					const itemStyle = spec.cellStyle?.(index);
					return itemStyle ? { value, itemStyle } : value;
				}),
				label: {
					show: true,
					fontSize: 10,
					rich: { fragile: { fontWeight: 'bold', color: '#7f1d1d', fontSize: 10 } },
					formatter: (p: unknown) => {
						const v = cellOf(p)[2];
						return spec.label(
							typeof v === 'number' ? v : null,
							(p as { dataIndex: number }).dataIndex
						);
					}
				}
			}
		]
	};
}
