import { describe, it, expect } from 'vitest';
import type { JinaIterateResult, ProblemInfo, Target } from '$lib/gen/endpoints/DESDEOFastAPI';
import { axisRange, pointArray, viewProblem, viewRows } from './view-problem';

const problem = {
	id: 1,
	name: 'p',
	objectives: [
		{ func: null, name: 'Cost', symbol: 'f_1', unit: 'EUR', maximize: false },
		{ func: null, name: 'Profit', symbol: 'f_2', maximize: true }
	]
} as unknown as ProblemInfo;

const targets: Target[] = [
	{ symbol: 'E_f_1', objective: 'f_1', leaf: null, leaves: ['a', 'b'], maximize: false },
	{ symbol: 'f_2_a', objective: 'f_2', leaf: 'a', leaves: ['a'], maximize: true }
];

describe('viewProblem', () => {
	it('makes one objective per target with its label, unit, direction and range', () => {
		const result = viewProblem(problem, targets, { E_f_1: [1, 9], f_2_a: [20, 5] });
		expect(result.id).toBe(1);
		expect(result.objectives).toEqual([
			{
				func: null,
				name: 'Cost (EUR)',
				symbol: 'E_f_1',
				unit: 'EUR',
				maximize: false,
				ideal: 1,
				nadir: 9
			},
			{
				func: null,
				name: 'Profit — a',
				symbol: 'f_2_a',
				unit: null,
				maximize: true,
				ideal: 20,
				nadir: 5
			}
		]);
	});

	it('leaves ideal and nadir empty without a range', () => {
		const result = viewProblem(problem, targets, {});
		expect(result.objectives.map((o) => [o.ideal, o.nadir])).toEqual([
			[null, null],
			[null, null]
		]);
	});
});

describe('viewRows', () => {
	it('draws one line per design with all its row names, in target order', () => {
		const results: JinaIterateResult[] = [
			{
				name: 'balanced',
				success: true,
				message: '',
				design_id: 1,
				target_values: { f_2_a: 7, E_f_1: 3 }
			},
			{ name: 'failed', success: false, message: 'x', design_id: null, target_values: {} },
			{ name: 'partial', success: true, message: '', design_id: 2, target_values: { E_f_1: 1 } },
			{
				name: 'emphasis_f_1',
				success: true,
				message: '',
				design_id: 1,
				target_values: { f_2_a: 8, E_f_1: 4 }
			},
			{
				name: 'other',
				success: true,
				message: '',
				design_id: 3,
				target_values: { f_2_a: 1, E_f_1: 2 }
			}
		];
		expect(viewRows(results, targets)).toEqual({
			designIds: [1, 3],
			labels: ['#1 balanced, emphasis_f_1', '#3 other'],
			values: [
				[3, 7],
				[2, 1]
			]
		});
	});
});

describe('axisRange', () => {
	it('keeps nonzero ranges', () => {
		expect(axisRange([1, 9], false)).toEqual([1, 9]);
	});

	it('widens zero-width ranges with the ideal on the better side', () => {
		expect(axisRange([200, 200], false)).toEqual([198, 202]);
		expect(axisRange([200, 200], true)).toEqual([202, 198]);
		expect(axisRange([0, 0], false)).toEqual([-0.5, 0.5]);
		expect(axisRange([1e-9, 1e-9], true)).toEqual([1e-9 + 1e-6, 1e-9 - 1e-6]);
	});
});

describe('pointArray', () => {
	it('orders a point by the targets and rejects incomplete points', () => {
		expect(pointArray({ f_2_a: 2, E_f_1: 1 }, targets)).toEqual([1, 2]);
		expect(pointArray({ E_f_1: 1 }, targets)).toBeNull();
	});
});
