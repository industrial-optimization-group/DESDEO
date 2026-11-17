import { describe, it, expect } from 'vitest';
import type { ProblemInfo, Target } from '$lib/gen/endpoints/DESDEOFastAPI';
import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors';
import {
	blend,
	CHART_BACKGROUND,
	contrastRatio,
	hexToHsl,
	hueDistance,
	hueSpreadOrder,
	hslToHex,
	LINE_ALPHA,
	scenarioColor,
	scenarioLineColor,
	scenarioProblem,
	scenarioLines,
	scenarioReferencePoint,
	hideLines,
	AGGREGATE_COLOR,
	AGGREGATE_SELECTED_COLOR,
	aggregateAvailable,
	aggregateLines,
	concatLines,
	defaultChartSelection,
	type ChartLines
} from './scenario-chart';

describe('hexToHsl and hslToHex', () => {
	it('convert both ways', () => {
		expect(hexToHsl('#ff0000')).toEqual([0, 1, 0.5]);
		expect(hslToHex(120, 1, 0.25)).toBe('#008000');
		const [h, sat, l] = hexToHsl('#a6b1e1');
		expect(hslToHex(h, sat, l)).toBe('#a6b1e1');
	});
});

describe('contrastRatio', () => {
	it('matches the WCAG ratios of black and white', () => {
		expect(contrastRatio('#000000', '#ffffff')).toBeCloseTo(21);
		expect(contrastRatio('#ffffff', '#ffffff')).toBeCloseTo(1);
	});
});

describe('scenario colours', () => {
	it('reuses the palette hues after ten scenarios', () => {
		expect(hexToHsl(scenarioColor(10))[0]).toBeCloseTo(hexToHsl(scenarioColor(0))[0], -1);
	});

	it('draws lines at 3:1 or more and selected lines at 4.5:1 or more on the chart', () => {
		COLOR_PALETTE.forEach((_, i) => {
			const drawn = blend(scenarioColor(i), LINE_ALPHA, CHART_BACKGROUND);
			expect(contrastRatio(drawn, CHART_BACKGROUND)).toBeGreaterThanOrEqual(3);
			expect(contrastRatio(scenarioLineColor(i, true), CHART_BACKGROUND)).toBeGreaterThanOrEqual(
				4.5
			);
		});
	});

	it('varies the colours of scenarios beyond the palette, all at 3:1 or more', () => {
		const lines = Array.from({ length: 30 }, (_, i) => scenarioColor(i));
		expect(new Set(lines).size).toBe(30);
		lines.forEach((line, i) => {
			const drawn = blend(line, LINE_ALPHA, CHART_BACKGROUND);
			expect(contrastRatio(drawn, CHART_BACKGROUND)).toBeGreaterThanOrEqual(3);
			expect(contrastRatio(scenarioLineColor(i, true), CHART_BACKGROUND)).toBeGreaterThanOrEqual(
				4.5
			);
		});
	});

	it('keeps the hue of its palette entry in hue-spread order, clearly saturated', () => {
		const order = hueSpreadOrder(COLOR_PALETTE);
		COLOR_PALETTE.forEach((_, i) => {
			const [hue] = hexToHsl(COLOR_PALETTE[order[i]]);
			for (const shade of [scenarioColor(i), scenarioLineColor(i, true)]) {
				const [h, sat] = hexToHsl(shade);
				const difference = Math.abs(((h - hue + 540) % 360) - 180);
				expect(difference).toBeLessThan(4);
				expect(sat).toBeGreaterThanOrEqual(0.45);
			}
		});
	});

	it('makes unselected lines translucent and selected lines opaque', () => {
		expect(scenarioLineColor(0)).toMatch(/^#[0-9a-f]{6}cc$/);
		expect(scenarioLineColor(0, true)).toMatch(/^#[0-9a-f]{6}$/);
		expect(scenarioLineColor(0).slice(0, 7)).toBe(scenarioColor(0));
	});
});

describe('scenarioProblem', () => {
	it('builds objectives with correct ideal, nadir, name, and unit', () => {
		const problem = {
			id: 1,
			name: 'Test',
			objectives: [
				{ func: null, name: 'Cost', symbol: 'f_1', unit: 'EUR', maximize: false },
				{ func: null, name: 'Time', symbol: 'f_2', unit: null, maximize: true }
			]
		} as unknown as ProblemInfo;

		const targets: Target[] = [
			{ symbol: 'f_1_a', objective: 'f_1', leaf: 'a', leaves: ['a', 'b'], maximize: false },
			{ symbol: 'f_1_b', objective: 'f_1', leaf: 'b', leaves: ['a', 'b'], maximize: false },
			{ symbol: 'f_2_a', objective: 'f_2', leaf: 'a', leaves: ['a'], maximize: true }
		];

		const ranges: Record<string, [number, number]> = {
			f_1_a: [1, 8],
			f_1_b: [3, 12],
			f_2_a: [5, 5]
		};

		const result = scenarioProblem(problem, targets, ranges, ['a', 'b']);

		expect(result.objectives).toHaveLength(2);
		const obj0 = result.objectives[0];
		expect(obj0.symbol).toBe('f_1');
		expect(obj0.name).toBe('Cost (EUR)');
		expect(obj0.unit).toBe('EUR');
		expect(obj0.maximize).toBe(false);
		expect(obj0.ideal).toBe(1);
		expect(obj0.nadir).toBe(12);

		const obj1 = result.objectives[1];
		expect(obj1.symbol).toBe('f_2');
		expect(obj1.name).toBe('Time');
		expect(obj1.unit).toBeNull();
		expect(obj1.ideal).not.toBe(obj1.nadir);
	});
});

describe('scenarioLines', () => {
	it('skips pairs with missing values and builds correct structure', () => {
		const designIds = [1, 2];
		const leafObjectives: Record<number, Record<string, Record<string, number>> | undefined> = {
			1: { a: { f_1: 10, f_2: 20 }, b: { f_1: 15, f_2: 25 } },
			2: { a: { f_1: 12, f_2: 22 }, b: { f_1: 14 } }
		};
		const leaves = ['b', 'a'];
		const leafOrder = ['a', 'b'];
		const objectives = ['f_1', 'f_2'];
		const selectedId = 1;

		const result = scenarioLines(
			designIds,
			leafObjectives,
			leaves,
			leafOrder,
			objectives,
			selectedId
		);

		expect(result.designIds).toEqual([1, 1, 2]);
		expect(result.leaves).toEqual(['b', 'a', 'a']);
		expect(result.labels).toEqual(['#1 \u2014 b', '#1 \u2014 a', '#2 \u2014 a']);
		expect(result.values).toEqual([
			[15, 25],
			[10, 20],
			[12, 22]
		]);
		expect(result.colors['0']).toBe(scenarioLineColor(1, true));
		expect(result.colors['1']).toBe(scenarioLineColor(0, true));
		expect(result.colors['2']).toBe(scenarioLineColor(0, false));
		expect(result.selected).toEqual([0, 1]);
	});
});

describe('scenarioReferencePoint', () => {
	it('returns shared values for aggregated targets (leaf null)', () => {
		const targets: Target[] = [
			{ symbol: 'f_1', objective: 'f_1', leaf: null, leaves: ['a', 'b'], maximize: false },
			{ symbol: 'f_2', objective: 'f_2', leaf: null, leaves: ['a', 'b'], maximize: false }
		];
		const point = { f_1: 10, f_2: 20 };
		const result = scenarioReferencePoint(targets, point, ['f_1', 'f_2'], ['a', 'b']);
		expect(result).toEqual({ values: [10, 20], shared: true, note: null });
	});

	it('returns per-leaf values with shared false', () => {
		const targets: Target[] = [
			{ symbol: 'f_1_a', objective: 'f_1', leaf: 'a', leaves: ['a'], maximize: false },
			{ symbol: 'f_2_a', objective: 'f_2', leaf: 'a', leaves: ['a'], maximize: false }
		];
		const point = { f_1_a: 10, f_2_a: 20 };
		const result = scenarioReferencePoint(targets, point, ['f_1', 'f_2'], ['a']);
		expect(result).toEqual({ values: [10, 20], shared: false, note: null });
	});

	it('returns note when leaves have different values', () => {
		const targets: Target[] = [
			{ symbol: 'f_1_a', objective: 'f_1', leaf: 'a', leaves: ['a', 'b'], maximize: false },
			{ symbol: 'f_1_b', objective: 'f_1', leaf: 'b', leaves: ['a', 'b'], maximize: false }
		];
		const point = { f_1_a: 10, f_1_b: 20 };
		const result = scenarioReferencePoint(targets, point, ['f_1'], ['a', 'b']);
		expect(result.values).toBeNull();
		expect(result.shared).toBe(false);
		expect(result.note).toBe(
			'The reference point differs between the checked scenarios; check a single scenario to see it.'
		);
	});

	it('returns null values when a point entry is missing', () => {
		const targets: Target[] = [
			{ symbol: 'f_1_a', objective: 'f_1', leaf: 'a', leaves: ['a'], maximize: false }
		];
		const point: Record<string, number> = {};
		const result = scenarioReferencePoint(targets, point, ['f_1'], ['a']);
		expect(result).toEqual({ values: null, shared: false, note: null });
	});

	it('uses only targets over all scenarios when no scenario is given', () => {
		const shared: Target[] = [
			{ symbol: 'E_f_1', objective: 'f_1', leaf: null, leaves: ['a', 'b'], maximize: false },
			{ symbol: 'f_2', objective: 'f_2', leaf: null, leaves: ['a', 'b'], maximize: true }
		];
		expect(scenarioReferencePoint(shared, { E_f_1: 1, f_2: 2 }, ['f_1', 'f_2'], [])).toEqual({
			values: [1, 2],
			shared: true,
			note: null
		});
		const perLeaf: Target[] = [
			{ symbol: 'f_1_a', objective: 'f_1', leaf: 'a', leaves: ['a'], maximize: false }
		];
		expect(scenarioReferencePoint(perLeaf, { f_1_a: 1 }, ['f_1'], [])).toEqual({
			values: null,
			shared: false,
			note: null
		});
	});
});

describe('hideLines', () => {
	it('drops entries whose design id is in the hidden set', () => {
		const lines = {
			designIds: [1, 2, 3],
			labels: ['#1 \u2014 a', '#2 \u2014 a', '#3 \u2014 a'],
			values: [[10], [20], [30]]
		};
		const result = hideLines(lines, [2]);
		expect(result.designIds).toEqual([1, 3]);
		expect(result.labels).toEqual(['#1 \u2014 a', '#3 \u2014 a']);
		expect(result.values).toEqual([[10], [30]]);
	});

	it('returns all lines when nothing is hidden', () => {
		const lines = {
			designIds: [1, 2],
			labels: ['#1 \u2014 a', '#2 \u2014 b'],
			values: [[1], [2]]
		};
		const result = hideLines(lines, []);
		expect(result.designIds).toEqual([1, 2]);
		expect(result.labels).toEqual(['#1 \u2014 a', '#2 \u2014 b']);
		expect(result.values).toEqual([[1], [2]]);
	});
});

describe('hueSpreadOrder', () => {
	const hues = COLOR_PALETTE.map((hex) => hexToHsl(hex)[0]);
	const minDistance = (indices: number[]) =>
		Math.min(
			...indices.flatMap((a, i) => indices.slice(i + 1).map((b) => hueDistance(hues[a], hues[b])))
		);

	it('is a deterministic permutation of the palette indices starting at 0', () => {
		const order = hueSpreadOrder(COLOR_PALETTE);
		expect(order).toEqual(hueSpreadOrder(COLOR_PALETTE));
		expect([...order].sort((a, b) => a - b)).toEqual(COLOR_PALETTE.map((_, i) => i));
		expect(order[0]).toBe(0);
	});

	it('spreads the first hues at least as far apart as the palette order', () => {
		const order = hueSpreadOrder(COLOR_PALETTE);
		const plain = COLOR_PALETTE.map((_, i) => i);
		for (const k of [4, 8]) {
			expect(minDistance(order.slice(0, k))).toBeGreaterThanOrEqual(minDistance(plain.slice(0, k)));
		}
	});

	it('measures hue distance around the circle', () => {
		expect(hueDistance(350, 10)).toBe(20);
		expect(hueDistance(10, 190)).toBe(180);
	});
});

const objectiveProblem = {
	id: 1,
	name: 'p',
	objectives: [
		{ func: null, name: 'Cost', symbol: 'f_1', maximize: false },
		{ func: null, name: 'Gain', symbol: 'g', maximize: true },
		{ func: null, name: 'Risk', symbol: 'h', maximize: false }
	]
} as unknown as ProblemInfo;

const perScenarioTargets: Target[] = [
	{ symbol: 'f_1_a', objective: 'f_1', leaf: 'a', leaves: ['a'], maximize: false },
	{ symbol: 'f_1_b', objective: 'f_1', leaf: 'b', leaves: ['b'], maximize: false },
	{ symbol: 'g_a', objective: 'g', leaf: 'a', leaves: ['a'], maximize: true },
	{ symbol: 'g_b', objective: 'g', leaf: 'b', leaves: ['b'], maximize: true },
	{ symbol: 'h', objective: 'h', leaf: null, leaves: ['a', 'b'], maximize: false }
];
const perScenarioRanges: Record<string, [number, number]> = {
	f_1_a: [1, 8],
	f_1_b: [3, 12],
	g_a: [20, 5],
	g_b: [30, 10],
	h: [2, 4]
};
const axes = (leaves: string[], aggregate: Parameters<typeof scenarioProblem>[4] = null) =>
	scenarioProblem(
		objectiveProblem,
		perScenarioTargets,
		perScenarioRanges,
		leaves,
		aggregate
	).objectives.map((o) => [o.symbol, o.ideal, o.nadir]);

describe('scenarioProblem axis ranges', () => {
	it('span only the checked scenarios, direction-aware, and always the shared targets', () => {
		expect(axes(['a'])).toEqual([
			['f_1', 1, 8],
			['g', 20, 5],
			['h', 2, 4]
		]);
		expect(axes(['b'])).toEqual([
			['f_1', 3, 12],
			['g', 30, 10],
			['h', 2, 4]
		]);
		expect(axes(['a', 'b'])).toEqual([
			['f_1', 1, 12],
			['g', 30, 5],
			['h', 2, 4]
		]);
	});

	it('keep all objectives without checked scenarios, with null ranges where nothing applies', () => {
		expect(axes([])).toEqual([
			['f_1', null, null],
			['g', null, null],
			['h', 2, 4]
		]);
	});

	it('include the aggregate ranges, kept apart from per-scenario ranges of the same symbol', () => {
		const aggregate = {
			targets: [
				{ symbol: 'E_f_1', objective: 'f_1', leaf: null, leaves: ['a', 'b'], maximize: false },
				{ symbol: 'g', objective: 'g', leaf: null, leaves: ['a', 'b'], maximize: true },
				{ symbol: 'h', objective: 'h', leaf: null, leaves: ['a', 'b'], maximize: false }
			],
			ranges: { E_f_1: [0, 9], g: [25, 1], h: [1, 3] } as Record<string, [number, number]>
		};
		expect(axes(['a'], aggregate)).toEqual([
			['f_1', 0, 9],
			['g', 25, 1],
			['h', 1, 4]
		]);
		expect(axes([], aggregate)).toEqual([
			['f_1', 0, 9],
			['g', 25, 1],
			['h', 1, 4]
		]);
	});
});

describe('aggregate lines', () => {
	const aggregated: Target[] = [
		{ symbol: 'E_f_1', objective: 'f_1', leaf: null, leaves: ['a', 'b'], maximize: false },
		{ symbol: 'E_g', objective: 'g', leaf: null, leaves: ['a', 'b'], maximize: true }
	];

	it('draw one line per design with all aggregated values, in objective order', () => {
		const lines = aggregateLines(
			[1, 2, 3],
			{ 1: { E_g: 5, E_f_1: 2 }, 2: { E_f_1: 1 }, 3: { E_f_1: 4, E_g: 6 } },
			aggregated,
			['f_1', 'g'],
			3
		);
		expect(lines).toEqual({
			designIds: [1, 3],
			leaves: [null, null],
			labels: ['#1 — Aggregate', '#3 — Aggregate'],
			values: [
				[2, 5],
				[4, 6]
			],
			colors: { '0': AGGREGATE_COLOR, '1': AGGREGATE_SELECTED_COLOR },
			selected: [1]
		});
	});

	it('are available only if every objective has a target over all scenarios', () => {
		expect(aggregateAvailable(aggregated, ['f_1', 'g'])).toBe(true);
		expect(aggregateAvailable(aggregated, ['f_1', 'g', 'h'])).toBe(false);
		expect(aggregateAvailable(perScenarioTargets, ['f_1', 'h'])).toBe(false);
	});

	it('concatenate with scenario lines, re-indexing colours and selections', () => {
		const a: ChartLines = {
			designIds: [1],
			leaves: [null],
			labels: ['#1 — Aggregate'],
			values: [[1]],
			colors: { '0': 'black' },
			selected: [0]
		};
		const b: ChartLines = {
			designIds: [1, 2],
			leaves: ['x', 'x'],
			labels: ['#1 — x', '#2 — x'],
			values: [[2], [3]],
			colors: { '0': 'red', '1': 'blue' },
			selected: [0]
		};
		expect(concatLines(a, b)).toEqual({
			designIds: [1, 1, 2],
			leaves: [null, 'x', 'x'],
			labels: ['#1 — Aggregate', '#1 — x', '#2 — x'],
			values: [[1], [2], [3]],
			colors: { '0': 'black', '1': 'red', '2': 'blue' },
			selected: [0, 1]
		});
	});
});

describe('defaultChartSelection', () => {
	it('plots the aggregate alone in the aggregated view and all scenarios in the per-scenario view', () => {
		expect(defaultChartSelection('aggregated', ['a', 'b'])).toEqual({
			leaves: [],
			aggregate: true
		});
		expect(defaultChartSelection('per_scenario', ['a', 'b'])).toEqual({
			leaves: ['a', 'b'],
			aggregate: false
		});
	});
});
