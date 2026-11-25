import { describe, it, expect } from 'vitest';
import type { LeafOutcome, ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';
import { percentToRaw } from './reference-point';
import { scenarioLineColor } from './scenario-chart';
import {
	extendToValues,
	infeasibleByRow,
	limitToRange,
	outcomeLines,
	rowKey,
	type OutcomeRow
} from './scenario-optimal';

const solved = (f_1: number, f_2: number): LeafOutcome => ({
	status: true,
	message: 'Optimal',
	objectives: { f_1, f_2 }
});
const failed = (message: string): LeafOutcome => ({ status: false, message, objectives: {} });

const row = (
	stateId: number,
	name: string,
	design_id: number | null,
	outcomes: Record<string, LeafOutcome>,
	leaf = 'b'
): OutcomeRow => ({
	stateId,
	leaf,
	result: { name, success: true, message: '', design_id, outcomes }
});

const leafOrder = ['a', 'b', 'c'];
const objectives = ['f_1', 'f_2'];

describe('outcomeLines', () => {
	const rows = [
		row(5, 'balanced', 1, { b: solved(1, 2), a: solved(3, 4), c: solved(5, 6) }),
		row(5, 'emphasis_f_1', 1, { b: solved(7, 8), a: solved(9, 10), c: solved(11, 12) })
	];

	it('draws rows sharing a design id separately and selects only the selected row', () => {
		const lines = outcomeLines(rows, ['a', 'c'], leafOrder, objectives, rowKey(5, 'emphasis_f_1'));
		expect(lines).toEqual({
			designIds: [1, 1, 1, 1],
			rowKeys: ['5:balanced', '5:balanced', '5:emphasis_f_1', '5:emphasis_f_1'],
			leaves: ['a', 'c', 'a', 'c'],
			labels: [
				'#1 balanced (for b) — a',
				'#1 balanced (for b) — c',
				'#1 emphasis_f_1 (for b) — a',
				'#1 emphasis_f_1 (for b) — c'
			],
			values: [
				[3, 4],
				[5, 6],
				[9, 10],
				[11, 12]
			],
			colors: {
				'0': scenarioLineColor(0),
				'1': scenarioLineColor(2),
				'2': scenarioLineColor(0, true),
				'3': scenarioLineColor(2, true)
			},
			selected: [2, 3]
		});
	});

	it('tells rows of the same name in different states apart', () => {
		const sameName = [
			row(5, 'balanced', 1, { b: solved(1, 2) }),
			row(6, 'balanced', 1, { b: solved(3, 4), a: solved(5, 6) }, 'a')
		];
		const lines = outcomeLines(sameName, ['b'], leafOrder, objectives, rowKey(6, 'balanced'));
		expect(lines.rowKeys).toEqual(['5:balanced', '6:balanced']);
		expect(lines.labels).toEqual(['#1 balanced (for b) — b', '#1 balanced (for a) — b']);
		expect(lines.selected).toEqual([1]);
	});

	it('selects nothing without a selected row or with a row that is not given', () => {
		for (const selected of [null, rowKey(9, 'balanced')]) {
			expect(outcomeLines(rows, ['a'], leafOrder, objectives, selected).selected).toEqual([]);
		}
	});

	it('skips failed outcomes, missing objectives and rows without a design', () => {
		const partial = [
			// The status decides, even if a failed outcome has values.
			row(5, 'x', 1, { a: { ...solved(1, 2), status: false }, b: solved(3, 4) }),
			row(5, 'y', 2, { a: { status: true, message: '', objectives: { f_1: 1 } } }),
			row(5, 'z', null, { b: solved(5, 6) }),
			row(5, 'w', 3, { a: solved(7, 8) })
		];
		const lines = outcomeLines(partial, ['a', 'b'], leafOrder, objectives, rowKey(5, 'w'));
		expect(lines.rowKeys).toEqual(['5:x', '5:w']);
		expect(lines.designIds).toEqual([1, 3]);
		expect(lines.leaves).toEqual(['b', 'a']);
		expect(lines.selected).toEqual([1]);
	});
});

describe('infeasibleByRow', () => {
	it('lists the failed scenarios of each row in leaf order, which have no lines', () => {
		const leafOrder = ['c', 'a', 'b'];
		const rows = [
			row(5, 'balanced', 1, {
				a: failed('Model is infeasible.'),
				b: solved(1, 2),
				c: failed('Time limit reached.')
			}),
			row(5, 'emphasis_f_1', 1, { b: solved(1, 2), a: solved(3, 4), c: solved(5, 6) })
		];
		expect(infeasibleByRow(rows, leafOrder)).toEqual({
			'5:balanced': [
				{ leaf: 'c', message: 'Time limit reached.' },
				{ leaf: 'a', message: 'Model is infeasible.' }
			],
			'5:emphasis_f_1': []
		});
		const lines = outcomeLines(rows, leafOrder, leafOrder, objectives, null);
		expect(lines.rowKeys.map((key, i) => [key, lines.leaves[i]])).toEqual([
			['5:balanced', 'b'],
			['5:emphasis_f_1', 'c'],
			['5:emphasis_f_1', 'a'],
			['5:emphasis_f_1', 'b']
		]);
	});
});

describe('extendToValues', () => {
	const problem = {
		id: 1,
		name: 'p',
		objectives: [
			{ func: null, name: 'Cost', symbol: 'f_1', maximize: false, ideal: 0, nadir: 10 },
			{ func: null, name: 'Gain', symbol: 'f_2', maximize: true, ideal: 10, nadir: 0 }
		]
	} as unknown as ProblemInfo;
	const ranges = (p: ProblemInfo) => p.objectives.map((o) => [o.ideal, o.nadir]);

	it('widens the ranges in the direction of each objective', () => {
		const result = extendToValues(problem, [
			[-2, 12],
			[15, -1]
		]);
		expect(ranges(result)).toEqual([
			[-2, 15],
			[12, -1]
		]);
		expect(result.objectives.map((o) => o.symbol)).toEqual(['f_1', 'f_2']);
		expect(ranges(problem)).toEqual([
			[0, 10],
			[10, 0]
		]);
	});

	const positive = {
		...problem,
		objectives: problem.objectives.map((o) => ({ ...o, ideal: 5, nadir: 5 }))
	};

	it('changes nothing for values inside or no values', () => {
		expect(extendToValues(problem, [[3, 7]])).toEqual(problem);
		expect(extendToValues(problem, [])).toEqual(problem);
	});

	it('skips null values', () => {
		expect(extendToValues(positive, [[null, null]])).toEqual(positive);
		expect(
			ranges(
				extendToValues(positive, [
					[null, 6],
					[4, null]
				])
			)
		).toEqual([
			[4, 5],
			[6, 5]
		]);
	});

	it('keeps zero values', () => {
		expect(ranges(extendToValues(positive, [[0, 0]]))).toEqual([
			[0, 5],
			[5, 0]
		]);
	});

	it('leaves objectives without a range empty', () => {
		const empty = {
			...problem,
			objectives: problem.objectives.map((o) => ({ ...o, ideal: null, nadir: null }))
		};
		expect(extendToValues(empty, [[1, 2]])).toEqual(empty);
	});
});

describe('limitToRange', () => {
	it('limits values outside a range of either direction', () => {
		for (const range of [
			[0, 10],
			[10, 0]
		] as [number, number][]) {
			expect(limitToRange(-3, range)).toEqual({ value: 0, limited: true });
			expect(limitToRange(12, range)).toEqual({ value: 10, limited: true });
		}
	});

	it('keeps values inside and at the bounds', () => {
		for (const value of [0, 4, 10]) {
			expect(limitToRange(value, [10, 0])).toEqual({ value, limited: false });
		}
	});

	it('flags only values outside by more than the tolerance', () => {
		const range: [number, number] = [-4.95, 71.71];
		const rounded = percentToRaw(100, range);
		expect(rounded).toBeLessThan(-4.95);
		expect(limitToRange(rounded, range)).toEqual({ value: -4.95, limited: false });
		// The tolerance is 7.666e-8 here.
		expect(limitToRange(-4.95 - 7e-8, range)).toEqual({ value: -4.95, limited: false });
		expect(limitToRange(-4.95 - 8e-8, range)).toEqual({ value: -4.95, limited: true });
		expect(limitToRange(71.71 + 8e-8, range)).toEqual({ value: 71.71, limited: true });
	});

	it('scales the tolerance by the bounds when the range is narrow', () => {
		expect(limitToRange(1000 + 9e-7, [1000, 1000])).toEqual({ value: 1000, limited: false });
		expect(limitToRange(1000 + 2e-6, [1000, 1000])).toEqual({ value: 1000, limited: true });
	});
});
