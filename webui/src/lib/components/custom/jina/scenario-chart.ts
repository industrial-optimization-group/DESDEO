import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors';
import type { ObjectiveDB, ProblemInfo, Target } from '$lib/gen/endpoints/DESDEOFastAPI';
import { objectiveLabel } from './labels';
import { objectiveRanges, type Range } from './reference-point';
import { axisRange } from './view-problem';

/** Background of the chart area the scenario lines are drawn on. */
export const CHART_BACKGROUND = '#f3f4f6';
/** Opacity of unselected scenario lines, so coinciding lines of several scenarios stay visible. */
export const LINE_ALPHA = 0.8;
const LINE_SATURATION = 0.65;
const SELECTED_SATURATION = 0.75;
const MIN_LINE_CONTRAST = 3;
const MIN_SELECTED_CONTRAST = 4.5;

function channels(hex: string): [number, number, number] {
	return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as [number, number, number];
}

function toHex(values: number[]): string {
	return (
		'#' +
		values
			.map((v) =>
				Math.max(0, Math.min(255, Math.round(v)))
					.toString(16)
					.padStart(2, '0')
			)
			.join('')
	);
}

/** Hue in degrees, saturation and lightness in 0..1 of a '#rrggbb' colour. */
export function hexToHsl(hex: string): [number, number, number] {
	const [r, g, b] = channels(hex).map((c) => c / 255);
	const max = Math.max(r, g, b);
	const min = Math.min(r, g, b);
	const l = (max + min) / 2;
	const d = max - min;
	if (d === 0) return [0, 0, l];
	const s = d / (1 - Math.abs(2 * l - 1));
	const h =
		max === r
			? ((g - b) / d + (g < b ? 6 : 0)) * 60
			: max === g
				? ((b - r) / d + 2) * 60
				: ((r - g) / d + 4) * 60;
	return [h, s, l];
}

/** The '#rrggbb' colour of a hue in degrees and saturation and lightness in 0..1. */
export function hslToHex(h: number, s: number, l: number): string {
	const a = s * Math.min(l, 1 - l);
	const f = (n: number) => {
		const k = (n + h / 30) % 12;
		return l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1));
	};
	return toHex([f(0), f(8), f(4)].map((v) => v * 255));
}

/** The WCAG 2 contrast ratio of two opaque '#rrggbb' colours. */
export function contrastRatio(a: string, b: string): number {
	const luminance = (hex: string) => {
		const [r, g, bl] = channels(hex).map((c) => {
			const v = c / 255;
			return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
		});
		return 0.2126 * r + 0.7152 * g + 0.0722 * bl;
	};
	const [high, low] = [luminance(a), luminance(b)].sort((x, y) => y - x);
	return (high + 0.05) / (low + 0.05);
}

/** The opaque colour of `hex` drawn with opacity `alpha` over `background`. */
export function blend(hex: string, alpha: number, background: string): string {
	const fg = channels(hex);
	const bg = channels(background);
	return toHex(fg.map((c, i) => alpha * c + (1 - alpha) * bg[i]));
}

/** The distance in degrees between two hues around the colour circle. */
export function hueDistance(a: number, b: number): number {
	const d = Math.abs(a - b) % 360;
	return Math.min(d, 360 - d);
}

/**
 * Palette indices in an order that spreads hues: from index 0, each next entry is the remaining one
 * whose smallest hue distance to those already chosen is largest, the lowest index on ties.
 */
export function hueSpreadOrder(palette: string[]): number[] {
	const hues = palette.map((hex) => hexToHsl(hex)[0]);
	const order = [0];
	while (order.length < palette.length) {
		let best = -1;
		let bestDistance = -1;
		for (let i = 0; i < palette.length; i++) {
			if (order.includes(i)) continue;
			const distance = Math.min(...order.map((j) => hueDistance(hues[i], hues[j])));
			if (distance > bestDistance) {
				best = i;
				bestDistance = distance;
			}
		}
		order.push(best);
	}
	return order;
}

/** Scenario i takes the palette entry at position i of this order, so the first scenarios get distinct hues. */
const HUE_SPREAD_ORDER = hueSpreadOrder(COLOR_PALETTE);

/** The lightest colour of the hue and saturation, searching down from `start`, whose `drawn` form reaches `ratio` on the chart. */
function lightest(
	hue: number,
	saturation: number,
	start: number,
	ratio: number,
	drawn: (hex: string) => string = (hex) => hex
): { hex: string; lightness: number } {
	let lightness = start;
	let hex = hslToHex(hue, saturation, lightness);
	while (lightness > 0.05 && contrastRatio(drawn(hex), CHART_BACKGROUND) < ratio) {
		lightness -= 0.01;
		hex = hslToHex(hue, saturation, lightness);
	}
	return { hex, lightness };
}

/**
 * Saturation and lightness offset of each pass through the palette: scenarios beyond the first
 * ten repeat the hues, darker in the second pass and greyer in the third.
 */
const PASSES = [
	{ saturation: LINE_SATURATION, offset: 0 },
	{ saturation: 0.75, offset: -0.14 },
	{ saturation: 0.35, offset: -0.07 }
];

/**
 * The line and selected colours of scenario `index`: its hue (in hue-spread order) at a raised
 * saturation, the line as light as gives 3:1 on the chart as drawn (a darker or greyer variant in
 * later passes), the selected about 10 points darker and at least 4.5:1.
 */
function scenarioShades(index: number): { line: string; selected: string } {
	const [hue] = hexToHsl(COLOR_PALETTE[HUE_SPREAD_ORDER[index % HUE_SPREAD_ORDER.length]]);
	const drawn = (hex: string) => blend(hex, LINE_ALPHA, CHART_BACKGROUND);
	const base = lightest(hue, LINE_SATURATION, 0.55, MIN_LINE_CONTRAST, drawn);
	const pass = PASSES[Math.floor(index / HUE_SPREAD_ORDER.length) % PASSES.length];
	const line = lightest(
		hue,
		pass.saturation,
		base.lightness + pass.offset,
		MIN_LINE_CONTRAST,
		drawn
	);
	const selected = lightest(hue, SELECTED_SATURATION, line.lightness - 0.1, MIN_SELECTED_CONTRAST);
	return { line: line.hex, selected: selected.hex };
}

/** The opaque colour of scenario `index`, for swatches and names. */
export function scenarioColor(index: number): string {
	return scenarioShades(index).line;
}

/** The line colour of scenario `index`: translucent, or opaque and darker for the selected design. */
export function scenarioLineColor(index: number, selected = false): string {
	const shades = scenarioShades(index);
	if (selected) return shades.selected;
	return (
		shades.line +
		Math.round(LINE_ALPHA * 255)
			.toString(16)
			.padStart(2, '0')
	);
}

/** Lines of the objective-axes chart; `leaves` holds each line's scenario, or null for the aggregate. */
export interface ChartLines {
	designIds: number[];
	leaves: (string | null)[];
	labels: string[];
	values: number[][];
	colors: Record<string, string>;
	selected: number[];
}

/** Colours of the aggregate lines, outside the scenario palette. */
export const AGGREGATE_COLOR = '#374151';
export const AGGREGATE_SELECTED_COLOR = '#111827';

/**
 * The problem with the original objectives of the per-scenario `targets` as its objectives. Each
 * axis spans the per-scenario ranges of the scenarios in `leaves` (and of targets shared by all
 * scenarios), plus the aggregate's range if `aggregate` is given, widened if zero-width.
 */
export function scenarioProblem(
	problem: ProblemInfo,
	targets: Target[],
	ranges: Record<string, Range>,
	leaves: string[],
	aggregate: { targets: Target[]; ranges: Record<string, Range> } | null = null
): ProblemInfo {
	// Prefixed keys keep per-scenario and aggregate ranges apart where their symbols coincide.
	const spanned = [
		...targets
			.filter((t) => t.leaf === null || leaves.includes(t.leaf))
			.map((t) => ({ key: `s:${t.symbol}`, range: ranges[t.symbol], target: t })),
		...(aggregate?.targets ?? [])
			.filter((t) => t.leaf === null)
			.map((t) => ({ key: `a:${t.symbol}`, range: aggregate?.ranges[t.symbol], target: t }))
	];
	const envelopes = objectiveRanges(
		spanned.map(({ key, target }) => ({
			symbol: key,
			objective: target.objective,
			maximize: target.maximize
		})),
		Object.fromEntries(
			spanned.flatMap(({ key, range }) => (range ? [[key, range] as [string, Range]] : []))
		)
	);
	const seen = new Set<string>();
	const objectives: ObjectiveDB[] = [];
	for (const target of targets) {
		const sym = target.objective;
		if (seen.has(sym)) continue;
		seen.add(sym);
		const maximize = target.maximize;
		const env = envelopes[sym];
		const range = env ? axisRange(env, maximize) : null;
		objectives.push({
			func: null,
			name: objectiveLabel(problem, sym),
			symbol: sym,
			unit: problem.objectives.find((o) => o.symbol === sym)?.unit ?? null,
			maximize,
			ideal: range?.[0] ?? null,
			nadir: range?.[1] ?? null
		});
	}
	return { ...problem, objectives };
}

/** Whether every objective has a target over all scenarios, so the aggregate can be drawn on the objective axes. */
export function aggregateAvailable(targets: Target[], objectives: string[]): boolean {
	return objectives.every((o) => targets.some((t) => t.objective === o && t.leaf === null));
}

/** One aggregate line per design with its values of the targets over all scenarios, in objective order. */
export function aggregateLines(
	designIds: number[],
	targetValues: Record<number, Record<string, number> | undefined>,
	targets: Target[],
	objectives: string[],
	selectedId: number | null
): ChartLines {
	const lines: ChartLines = {
		designIds: [],
		leaves: [],
		labels: [],
		values: [],
		colors: {},
		selected: []
	};
	const symbols = objectives.map(
		(o) => targets.find((t) => t.objective === o && t.leaf === null)?.symbol
	);
	for (const id of designIds) {
		const values = symbols.map((sym) => (sym === undefined ? undefined : targetValues[id]?.[sym]));
		if (!values.every((v): v is number => typeof v === 'number')) continue;
		const i = lines.designIds.length;
		lines.designIds.push(id);
		lines.leaves.push(null);
		lines.labels.push(`#${id} — Aggregate`);
		lines.values.push(values);
		lines.colors[String(i)] = id === selectedId ? AGGREGATE_SELECTED_COLOR : AGGREGATE_COLOR;
		if (id === selectedId) lines.selected.push(i);
	}
	return lines;
}

/** The lines of all parts in order, with colours and selections re-indexed. */
export function concatLines(...parts: ChartLines[]): ChartLines {
	const lines: ChartLines = {
		designIds: [],
		leaves: [],
		labels: [],
		values: [],
		colors: {},
		selected: []
	};
	for (const part of parts) {
		const offset = lines.designIds.length;
		lines.designIds.push(...part.designIds);
		lines.leaves.push(...part.leaves);
		lines.labels.push(...part.labels);
		lines.values.push(...part.values);
		for (const [i, color] of Object.entries(part.colors)) {
			lines.colors[String(Number(i) + offset)] = color;
		}
		lines.selected.push(...part.selected.map((i) => i + offset));
	}
	return lines;
}

/** The scenarios and whether the aggregate are plotted by default: the aggregate alone in the aggregated view, all scenarios in the per-scenario view. */
export function defaultChartSelection(
	view: 'aggregated' | 'per_scenario',
	leaves: string[]
): { leaves: string[]; aggregate: boolean } {
	return view === 'aggregated'
		? { leaves: [], aggregate: true }
		: { leaves: [...leaves], aggregate: false };
}

/** Builds line-chart data for scenario objectives, skipping pairs with missing values. */
export function scenarioLines(
	designIds: number[],
	leafObjectives: Record<number, Record<string, Record<string, number>> | undefined>,
	leaves: string[],
	leafOrder: string[],
	objectives: string[],
	selectedId: number | null
): ChartLines {
	const resultDesignIds: number[] = [];
	const resultLeaves: string[] = [];
	const labels: string[] = [];
	const values: number[][] = [];
	const colors: Record<string, string> = {};
	const selected: number[] = [];

	for (const id of designIds) {
		for (const leaf of leaves) {
			const leafData = leafObjectives[id]?.[leaf];
			if (leafData === undefined) continue;
			const rowValues: number[] = [];
			let skip = false;
			for (const obj of objectives) {
				const val = leafData[obj];
				if (typeof val !== 'number') {
					skip = true;
					break;
				}
				rowValues.push(val);
			}
			if (skip) continue;

			const i = resultDesignIds.length;
			resultDesignIds.push(id);
			resultLeaves.push(leaf);
			labels.push('#' + id + ' \u2014 ' + leaf);
			values.push(rowValues);
			colors[String(i)] = scenarioLineColor(leafOrder.indexOf(leaf), id === selectedId);
			if (id === selectedId) {
				selected.push(i);
			}
		}
	}

	return { designIds: resultDesignIds, leaves: resultLeaves, labels, values, colors, selected };
}

/**
 * The reference point on the objective axes for the checked scenarios: each objective from its
 * target over all scenarios, else from the scenario's own target. Null with a note if the
 * scenarios' points differ; with no scenarios, only targets over all scenarios are used.
 */
export function scenarioReferencePoint(
	targets: Target[],
	point: Record<string, number>,
	objectives: string[],
	leaves: string[]
): { values: number[] | null; shared: boolean; note: string | null } {
	// Without scenarios, only the targets over all scenarios give the point.
	const polylineLeaves: (string | null)[] = leaves.length > 0 ? leaves : [null];
	const results: { values: number[]; shared: boolean }[] = [];
	for (const leaf of polylineLeaves) {
		const values: number[] = [];
		let allShared = true;
		let valid = true;
		for (const obj of objectives) {
			const nullTarget = targets.find((t) => t.objective === obj && t.leaf === null);
			let val: number | undefined;
			if (nullTarget !== undefined) {
				val = point[nullTarget.symbol];
			} else {
				const leafTarget = targets.find((t) => t.objective === obj && t.leaf === leaf);
				if (leafTarget === undefined) {
					valid = false;
					break;
				}
				val = point[leafTarget.symbol];
				allShared = false;
			}
			if (typeof val !== 'number') {
				valid = false;
				break;
			}
			values.push(val);
		}
		if (!valid) {
			return { values: null, shared: false, note: null };
		}
		results.push({ values, shared: allShared });
	}

	const first = results[0];
	let allEqual = true;
	for (let i = 1; i < results.length; i++) {
		const cur = results[i];
		if (cur.values.length !== first.values.length) {
			allEqual = false;
			break;
		}
		for (let j = 0; j < cur.values.length; j++) {
			if (cur.values[j] !== first.values[j]) {
				allEqual = false;
				break;
			}
		}
		if (!allEqual) break;
	}

	if (allEqual) {
		return { values: first.values, shared: first.shared, note: null };
	}
	return {
		values: null,
		shared: false,
		note: 'The reference point differs between the checked scenarios; check a single scenario to see it.'
	};
}

/** Removes lines whose design id appears in the hidden set. */
export function hideLines(
	lines: { designIds: number[]; labels: string[]; values: number[][] },
	hidden: number[]
): { designIds: number[]; labels: string[]; values: number[][] } {
	const hiddenSet = new Set(hidden);
	const designIds: number[] = [];
	const labels: string[] = [];
	const values: number[][] = [];
	for (let i = 0; i < lines.designIds.length; i++) {
		if (hiddenSet.has(lines.designIds[i])) continue;
		designIds.push(lines.designIds[i]);
		labels.push(lines.labels[i]);
		values.push(lines.values[i]);
	}
	return { designIds, labels, values };
}
