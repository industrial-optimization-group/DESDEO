import { describe, it, expect } from 'vitest';
import type { Target } from '$lib/gen/endpoints/DESDEOFastAPI';
import {
	applyAllFills,
	applyFill,
	fillWithIdeals,
	groupByObjective,
	objectiveSpan,
	orderTargets,
	parseFill,
	scopedTargets
} from './fill';

const cell = (objective: string, leaf: string | null, maximize = false): Target => ({
	symbol: leaf ? `${objective}_${leaf}` : objective,
	objective,
	leaf,
	leaves: leaf ? [leaf] : ['a', 'b', 'c'],
	maximize
});

// f is minimised in leaves a, b, c; g is maximised and exists only in a and c (sparse);
// h is shared by all leaves.
const targets = [
	cell('f', 'a'),
	cell('g', 'a', true),
	cell('f', 'b'),
	cell('f', 'c'),
	cell('g', 'c', true),
	cell('h', null)
];
const ranges: Record<string, [number, number]> = {
	f_a: [0, 10],
	f_b: [2, 12],
	f_c: [4, 20],
	g_a: [100, 50],
	g_c: [80, 40],
	h: [1, 3]
};
const point = { f_a: 5, f_b: 7, f_c: 12, g_a: 75, g_c: 60, h: 2 };

describe('groupByObjective', () => {
	it('groups the cells by objective in order of first appearance', () => {
		const groups = groupByObjective(targets);
		expect(groups.map((g) => [g.objective, g.maximize, g.targets.map((t) => t.symbol)])).toEqual([
			['f', false, ['f_a', 'f_b', 'f_c']],
			['g', true, ['g_a', 'g_c']],
			['h', false, ['h']]
		]);
	});
});

describe('orderTargets', () => {
	it('keeps the objective order and orders each objective by the leaf order', () => {
		const ordered = orderTargets(
			[cell('g', 'b', true), ...targets, cell('g', null, true)],
			['c', 'a', 'b']
		);
		expect(ordered.map((t) => t.symbol)).toEqual([
			'g',
			'g_c',
			'g_a',
			'g_b',
			'f_c',
			'f_a',
			'f_b',
			'h'
		]);
	});

	it('puts leaves missing from the leaf order last, in their given order', () => {
		const ordered = orderTargets([cell('f', 'x'), cell('f', 'b'), cell('f', 'y')], ['b']);
		expect(ordered.map((t) => t.symbol)).toEqual(['f_b', 'f_x', 'f_y']);
	});
});

describe('scopedTargets', () => {
	it('keeps the scoped leaves and shared targets', () => {
		expect(scopedTargets(targets, ['b']).map((t) => t.symbol)).toEqual(['f_b', 'h']);
		expect(scopedTargets(targets, null)).toHaveLength(6);
	});
});

describe('parseFill', () => {
	it('skips blanks and rejects non-numbers and out-of-range percents', () => {
		expect(parseFill('  ', 'raw')).toEqual({ value: null, warning: null });
		expect(parseFill('x', 'raw').warning).toMatch(/not applied/);
		expect(parseFill('150', 'percent').warning).toMatch(/0–100/);
		expect(parseFill('150', 'raw')).toEqual({ value: 150, warning: null });
	});
});

describe('applyFill', () => {
	const f = groupByObjective(targets)[0].targets;
	const g = groupByObjective(targets)[1].targets;

	it('writes the same raw value into every scoped cell', () => {
		const result = applyFill(point, scopedTargets(f, ['a', 'c']), ranges, null, 'raw', '6');
		expect(result).toEqual({ point: { ...point, f_a: 6, f_c: 6 }, warning: null });
	});

	it('writes the same percent of each cell range, differing raw values', () => {
		expect(applyFill(point, f, ranges, null, 'percent', '50').point).toEqual({
			...point,
			f_a: 5,
			f_b: 7,
			f_c: 12
		});
		// Maximised: 100% is the larger ideal.
		expect(applyFill(point, g, ranges, null, 'percent', '100').point).toMatchObject({
			g_a: 100,
			g_c: 80
		});
	});

	it('applies the same change from each previous value, skipping cells without one', () => {
		const previous = { f_a: 5, f_b: 7 };
		expect(applyFill(point, f, ranges, previous, 'change', '10').point).toEqual({
			...point,
			f_a: 4,
			f_b: 6
		});
	});

	it('leaves the point unchanged for blank or rejected entries', () => {
		expect(applyFill(point, f, ranges, null, 'raw', '')).toEqual({ point, warning: null });
		const rejected = applyFill(point, f, ranges, null, 'percent', '5000');
		expect(rejected.point).toBe(point);
		expect(rejected.warning).toMatch(/not applied/);
	});
});

describe('applyAllFills', () => {
	it('applies every non-blank entry and skips blank ones', () => {
		const groups = groupByObjective(targets);
		const result = applyAllFills(
			point,
			groups,
			{ f: '3', g: '', h: 'oops' },
			['a'],
			ranges,
			null,
			'raw'
		);
		expect(result.point).toEqual({ ...point, f_a: 3 });
		expect(Object.keys(result.warnings)).toEqual(['h']);
	});
});

describe('fillWithIdeals', () => {
	it('sets every cell to its own ideal', () => {
		expect(fillWithIdeals(point, targets, ranges)).toEqual({
			f_a: 0,
			f_b: 2,
			f_c: 4,
			g_a: 100,
			g_c: 80,
			h: 1
		});
	});
});

describe('objectiveSpan', () => {
	it('gives the union and the common band of a minimised objective', () => {
		const f = groupByObjective(targets)[0].targets;
		expect(objectiveSpan(f, ranges, false)).toEqual({ union: [0, 20], common: [4, 10] });
	});

	it('is direction-aware for a maximised objective', () => {
		const g = groupByObjective(targets)[1].targets;
		expect(objectiveSpan(g, ranges, true)).toEqual({ union: [100, 40], common: [80, 50] });
	});

	it('has no common band when no single value is in every range', () => {
		const disjoint = { f_a: [0, 1], f_b: [2, 3] } as Record<string, [number, number]>;
		expect(objectiveSpan([cell('f', 'a'), cell('f', 'b')], disjoint, false)).toEqual({
			union: [0, 3],
			common: null
		});
	});

	it('is empty without ranged cells', () => {
		expect(objectiveSpan([cell('f', 'a')], {}, false)).toEqual({ union: null, common: null });
	});
});
