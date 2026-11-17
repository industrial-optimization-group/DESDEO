/* Conversions between raw aspiration levels and their percent and change representations.

A range is [ideal, nadir] in the objective's original direction, so for a maximised objective
ideal > nadir. Percent: 100 = ideal, 0 = nadir. Change: percent of the range width moved toward
the ideal from the previous aspiration level. */

export type Range = [number, number];

export function percentToRaw(percent: number, [ideal, nadir]: Range): number {
	return nadir + (percent / 100) * (ideal - nadir);
}

/** A zero-width range has its ideal and nadir at the same value, which counts as 100. */
export function rawToPercent(raw: number, [ideal, nadir]: Range): number {
	const width = ideal - nadir;
	return width === 0 ? 100 : ((raw - nadir) / width) * 100;
}

export function changeToRaw(change: number, previous: number, [ideal, nadir]: Range): number {
	return previous + (change / 100) * (ideal - nadir);
}

/** On a zero-width range no change can move the value, so the change is 0. */
export function rawToChange(raw: number, previous: number, [ideal, nadir]: Range): number {
	const width = ideal - nadir;
	return width === 0 ? 0 : ((raw - previous) / width) * 100;
}

export function midpoint([ideal, nadir]: Range): number {
	return (ideal + nadir) / 2;
}

/** The range of each objective spanning the ranges of all its targets: the best ideal and worst nadir. */
export function objectiveRanges(
	targets: { symbol: string; objective: string; maximize: boolean }[],
	ranges: Record<string, Range>
): Record<string, Range> {
	const result: Record<string, Range> = {};
	for (const target of targets) {
		const range = ranges[target.symbol];
		if (!range) continue;
		const current = result[target.objective];
		if (!current) {
			result[target.objective] = [range[0], range[1]];
			continue;
		}
		const better = target.maximize ? Math.max : Math.min;
		const worse = target.maximize ? Math.min : Math.max;
		result[target.objective] = [better(current[0], range[0]), worse(current[1], range[1])];
	}
	return result;
}

/** The entries of `values` with finite numbers, limited to `keys`. */
export function finitePoint(
	values: Record<string, number | null | undefined>,
	keys: string[]
): Record<string, number> {
	const point: Record<string, number> = {};
	for (const key of keys) {
		const value = values[key];
		if (typeof value === 'number' && Number.isFinite(value)) point[key] = value;
	}
	return point;
}

export function roundSignificant(value: number, digits = 4): number {
	return Number(value.toPrecision(digits));
}

/** Input prefills: the midpoint of each objective's range, rounded for display, or null without a range. */
export function midpointPrefill(
	objectives: string[],
	ranges: Record<string, Range>
): Record<string, number | null> {
	return Object.fromEntries(
		objectives.map((obj) => [obj, ranges[obj] ? roundSignificant(midpoint(ranges[obj])) : null])
	);
}

/**
 * The aspiration level an entry being typed gives: the converted entry, or the level the input had
 * when focused if the entry is not a number or lies outside `bounds`, with a warning in the latter case.
 */
export function applyEntry(
	entry: string,
	atFocus: number,
	convert: (entered: number) => number,
	bounds?: [number, number]
): { value: number; warning: string | null } {
	const entered = Number(entry);
	if (entry.trim() === '' || !Number.isFinite(entered)) return { value: atFocus, warning: null };
	if (bounds && (entered < bounds[0] || entered > bounds[1])) {
		return { value: atFocus, warning: `Must be ${bounds[0]}–${bounds[1]}; not applied.` };
	}
	return { value: convert(entered), warning: null };
}
