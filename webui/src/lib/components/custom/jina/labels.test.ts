import { describe, it, expect } from 'vitest';
import { baselineFirst, compactNumber } from './labels';

describe('compactNumber', () => {
	it('abbreviates large values with SI suffixes', () => {
		expect(compactNumber(-32_123_456)).toBe('-32.1M');
		expect(compactNumber(7_890)).toBe('7.9k');
		expect(compactNumber(2_500_000_000)).toBe('2.5B');
	});

	it('keeps small values short', () => {
		expect(compactNumber(158.4)).toBe('158');
		expect(compactNumber(3.14159)).toBe('3.14');
		expect(compactNumber(0.012345)).toBe('0.012');
		expect(compactNumber(0)).toBe('0');
		expect(compactNumber(null)).toBe('—');
	});
});

describe('baselineFirst', () => {
	it('moves the baseline to the front and keeps the other leaves in order', () => {
		expect(baselineFirst(['a', 'b', 'c', 'd'], 'c')).toEqual(['c', 'a', 'b', 'd']);
		expect(baselineFirst(['a', 'b'], 'a')).toEqual(['a', 'b']);
	});

	it('keeps the order without a baseline among the leaves', () => {
		expect(baselineFirst(['a', 'b'], null)).toEqual(['a', 'b']);
		expect(baselineFirst(['a', 'b'], 'x')).toEqual(['a', 'b']);
	});
});
