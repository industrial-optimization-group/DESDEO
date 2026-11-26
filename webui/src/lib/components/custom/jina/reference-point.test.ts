import { describe, it, expect } from 'vitest';
import {
	percentToRaw,
	rawToPercent,
	changeToRaw,
	rawToChange,
	midpoint,
	objectiveRanges,
	finitePoint,
	applyEntry,
	midpointPrefill,
	type Range
} from './reference-point';

const minimised: Range = [2, 10];
const maximised: Range = [10, 2];
const zeroWidth: Range = [5, 5];

describe('percent', () => {
	it('maps 100 to the ideal and 0 to the nadir of a minimised objective', () => {
		expect(percentToRaw(100, minimised)).toBe(2);
		expect(percentToRaw(0, minimised)).toBe(10);
		expect(percentToRaw(25, minimised)).toBe(8);
	});

	it('maps 100 to the ideal and 0 to the nadir of a maximised objective', () => {
		expect(percentToRaw(100, maximised)).toBe(10);
		expect(percentToRaw(0, maximised)).toBe(2);
		expect(percentToRaw(25, maximised)).toBe(4);
	});

	it('inverts percentToRaw', () => {
		for (const range of [minimised, maximised]) {
			for (const pct of [-20, 0, 33, 100, 140]) {
				expect(rawToPercent(percentToRaw(pct, range), range)).toBeCloseTo(pct);
			}
		}
	});

	it('handles zero-width ranges', () => {
		expect(percentToRaw(30, zeroWidth)).toBe(5);
		expect(rawToPercent(5, zeroWidth)).toBe(100);
		expect(Number.isFinite(rawToPercent(7, zeroWidth))).toBe(true);
	});
});

describe('change', () => {
	it('moves toward the ideal for a positive change', () => {
		expect(changeToRaw(25, 6, minimised)).toBe(4);
		expect(changeToRaw(25, 6, maximised)).toBe(8);
		expect(changeToRaw(-25, 6, minimised)).toBe(8);
		expect(changeToRaw(-25, 6, maximised)).toBe(4);
	});

	it('inverts changeToRaw', () => {
		for (const range of [minimised, maximised]) {
			for (const change of [-50, 0, 10, 75]) {
				expect(rawToChange(changeToRaw(change, 6, range), 6, range)).toBeCloseTo(change);
			}
		}
	});

	it('handles zero-width ranges', () => {
		expect(changeToRaw(40, 5, zeroWidth)).toBe(5);
		expect(rawToChange(9, 5, zeroWidth)).toBe(0);
	});
});

describe('objectiveRanges', () => {
	it('takes the best ideal and worst nadir over the targets of each objective', () => {
		const targets = [
			{ symbol: 'f_1_a', objective: 'f_1', maximize: false },
			{ symbol: 'f_1_b', objective: 'f_1', maximize: false },
			{ symbol: 'f_2_a', objective: 'f_2', maximize: true },
			{ symbol: 'f_2_b', objective: 'f_2', maximize: true }
		];
		const ranges: Record<string, Range> = {
			f_1_a: [1, 8],
			f_1_b: [3, 12],
			f_2_a: [20, 5],
			f_2_b: [15, 2]
		};
		expect(objectiveRanges(targets, ranges)).toEqual({ f_1: [1, 12], f_2: [20, 2] });
	});

	it('gives midpoints in either direction', () => {
		expect(midpoint(minimised)).toBe(6);
		expect(midpoint(maximised)).toBe(6);
	});
});

describe('finitePoint', () => {
	it('keeps finite entries of the given keys only', () => {
		const values = { a: 1, b: null, c: undefined, d: Number.NaN, e: 2 };
		expect(finitePoint(values, ['a', 'b', 'c', 'd', 'f'])).toEqual({ a: 1 });
	});
});

describe('midpointPrefill', () => {
	it('rounds midpoints to four significant digits and leaves objectives without a range empty', () => {
		expect(midpointPrefill(['a', 'b'], { a: [0, 2 / 3] })).toEqual({ a: 0.3333, b: null });
	});
});

describe('applyEntry', () => {
	const toRaw = (pct: number) => percentToRaw(pct, minimised);

	it('applies a valid entry', () => {
		expect(applyEntry('25', 6, toRaw, [0, 100])).toEqual({ value: 8, warning: null });
	});

	it('reverts to the value at focus, not a valid prefix, once the entry goes out of range', () => {
		// Typing 5000 passes through the valid prefixes 5 and 50 before leaving the range.
		const steps = ['5', '50', '500', '5000'].map((entry) => applyEntry(entry, 9, toRaw, [0, 100]));
		expect(steps[1]).toEqual({ value: 6, warning: null });
		expect(steps[3]).toEqual({ value: 9, warning: 'Must be 0–100; not applied.' });
	});

	it('keeps the value at focus for empty or non-numeric entries', () => {
		expect(applyEntry('', 9, toRaw, [0, 100])).toEqual({ value: 9, warning: null });
		expect(applyEntry('-', 9, toRaw, [0, 100])).toEqual({ value: 9, warning: null });
	});

	it('has no bounds unless given', () => {
		expect(applyEntry('5000', 6, (v) => v)).toEqual({ value: 5000, warning: null });
	});
});
