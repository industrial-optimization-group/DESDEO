/* Filling the reference-point cells of an objective at once, for views with a target per scenario. */

import type { Target } from '$lib/gen/endpoints/DESDEOFastAPI';
import { changeToRaw, percentToRaw, type Range } from './reference-point';

export type EntryMode = 'percent' | 'raw' | 'change';

export interface ObjectiveGroup {
	objective: string;
	maximize: boolean;
	targets: Target[];
}

/** The targets grouped by objective, in order of first appearance. */
export function groupByObjective(targets: Target[]): ObjectiveGroup[] {
	const groups: ObjectiveGroup[] = [];
	for (const target of targets) {
		const group = groups.find((g) => g.objective === target.objective);
		if (group) group.targets.push(target);
		else groups.push({ objective: target.objective, maximize: target.maximize, targets: [target] });
	}
	return groups;
}

/**
 * The targets with each objective's targets together in order of the objective's first appearance,
 * a target over all scenarios first and the others in the order of `leafOrder`.
 */
export function orderTargets(targets: Target[], leafOrder: string[]): Target[] {
	const objectives = [...new Set(targets.map((t) => t.objective))];
	const leafRank = (t: Target) => {
		if (t.leaf === null) return -1;
		const i = leafOrder.indexOf(t.leaf);
		return i === -1 ? leafOrder.length : i;
	};
	return [...targets].sort(
		(a, b) =>
			objectives.indexOf(a.objective) - objectives.indexOf(b.objective) || leafRank(a) - leafRank(b)
	);
}

/** The targets of the scenarios in `leaves` (all if null); a target over all scenarios is always in scope. */
export function scopedTargets(targets: Target[], leaves: string[] | null): Target[] {
	return targets.filter((t) => leaves === null || t.leaf === null || leaves.includes(t.leaf));
}

/** A fill entry: null if blank, else the number or why it is rejected. */
export function parseFill(
	entry: string,
	mode: EntryMode
): { value: number; warning: null } | { value: null; warning: string | null } {
	if (entry.trim() === '') return { value: null, warning: null };
	const value = Number(entry);
	if (!Number.isFinite(value)) return { value: null, warning: 'Not a number; not applied.' };
	if (mode === 'percent' && (value < 0 || value > 100)) {
		return { value: null, warning: 'Must be 0–100; not applied.' };
	}
	return { value, warning: null };
}

/**
 * The reference point with the entered value written into the cells of `targets`: the same raw
 * value, the same percent of each cell's own range, or the same change in percent of each cell's
 * range from its previous value. Cells without a range, or without a previous value in change
 * mode, are left as they are; so is everything for a blank or rejected entry.
 */
export function applyFill(
	point: Record<string, number>,
	targets: Target[],
	ranges: Record<string, Range>,
	previous: Record<string, number> | null,
	mode: EntryMode,
	entry: string
): { point: Record<string, number>; warning: string | null } {
	const parsed = parseFill(entry, mode);
	if (parsed.value === null) return { point, warning: parsed.warning };
	const entered = parsed.value;
	const next = { ...point };
	for (const target of targets) {
		const range = ranges[target.symbol];
		if (!range) continue;
		if (mode === 'raw') next[target.symbol] = entered;
		else if (mode === 'percent') next[target.symbol] = percentToRaw(entered, range);
		else {
			const prev = previous?.[target.symbol];
			if (prev !== undefined) next[target.symbol] = changeToRaw(entered, prev, range);
		}
	}
	return { point: next, warning: null };
}

/** Every group's non-blank fill entry applied to its scoped cells; warnings by objective for rejected entries. */
export function applyAllFills(
	point: Record<string, number>,
	groups: ObjectiveGroup[],
	entries: Record<string, string>,
	leaves: string[] | null,
	ranges: Record<string, Range>,
	previous: Record<string, number> | null,
	mode: EntryMode
): { point: Record<string, number>; warnings: Record<string, string> } {
	let next = point;
	const warnings: Record<string, string> = {};
	for (const group of groups) {
		const result = applyFill(
			next,
			scopedTargets(group.targets, leaves),
			ranges,
			previous,
			mode,
			entries[group.objective] ?? ''
		);
		next = result.point;
		if (result.warning) warnings[group.objective] = result.warning;
	}
	return { point: next, warnings };
}

/** The reference point with every cell of `targets` that has a range set to its own ideal. */
export function fillWithIdeals(
	point: Record<string, number>,
	targets: Target[],
	ranges: Record<string, Range>
): Record<string, number> {
	const next = { ...point };
	for (const target of targets) {
		const range = ranges[target.symbol];
		if (range) next[target.symbol] = range[0];
	}
	return next;
}

/**
 * The ranges of an objective's cells combined, as [ideal, nadir] in its direction: `union` from
 * the best ideal to the worst nadir, and `common`, the values within every cell's range, or null
 * if no single value is. Both are null without any ranged cell.
 */
export function objectiveSpan(
	targets: Target[],
	ranges: Record<string, Range>,
	maximize: boolean
): { union: Range | null; common: Range | null } {
	const cells = targets.flatMap((t) => (ranges[t.symbol] ? [ranges[t.symbol]] : []));
	if (cells.length === 0) return { union: null, common: null };
	const better = maximize ? Math.max : Math.min;
	const worse = maximize ? Math.min : Math.max;
	const ideals = cells.map(([ideal]) => ideal);
	const nadirs = cells.map(([, nadir]) => nadir);
	const union: Range = [better(...ideals), worse(...nadirs)];
	const common: Range = [worse(...ideals), better(...nadirs)];
	const empty = maximize ? common[0] < common[1] : common[0] > common[1];
	return { union, common: empty ? null : common };
}
