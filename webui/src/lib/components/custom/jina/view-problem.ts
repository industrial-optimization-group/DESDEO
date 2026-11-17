/* A problem whose objectives are the targets of a JINA view, for the shared visualizations. */

import type {
	JinaIterateResult,
	ObjectiveDB,
	ProblemInfo,
	Target
} from '$lib/gen/endpoints/DESDEOFastAPI';
import { targetLabel } from './labels';
import type { Range } from './reference-point';

/**
 * A drawable axis range: a zero-width range (ideal equal to nadir) is widened around its value by
 * 1% of the value (at least 1e-6), or by 0.5 at zero, with the ideal on the better side.
 */
export function axisRange(range: Range, maximize: boolean): Range {
	const [ideal, nadir] = range;
	if (ideal !== nadir) return range;
	const pad = ideal === 0 ? 0.5 : Math.max(1e-6, Math.abs(ideal) * 0.01);
	return maximize ? [ideal + pad, ideal - pad] : [ideal - pad, ideal + pad];
}

/** The problem with one objective per target, named by its label, with ideal and nadir from `ranges`. */
export function viewProblem(
	problem: ProblemInfo,
	targets: Target[],
	ranges: Record<string, Range>
): ProblemInfo {
	const objectives: ObjectiveDB[] = targets.map((target) => {
		const range = ranges[target.symbol] ? axisRange(ranges[target.symbol], target.maximize) : null;
		return {
			func: null,
			name: targetLabel(problem, target),
			symbol: target.symbol,
			unit: problem.objectives.find((o) => o.symbol === target.objective)?.unit ?? null,
			maximize: target.maximize,
			ideal: range?.[0] ?? null,
			nadir: range?.[1] ?? null
		};
	});
	return { ...problem, objectives };
}

/**
 * One chart line per design: the successful results with a value for every target, grouped by
 * design, labelled with the design id and the names of all its rows, with the values of its first row
 * in target order.
 */
export function viewRows(
	results: JinaIterateResult[],
	targets: Target[]
): { designIds: number[]; labels: string[]; values: number[][] } {
	const lines = new Map<number, { names: string[]; values: number[] }>();
	for (const r of results) {
		if (!r.success || r.design_id == null) continue;
		if (!targets.every((t) => typeof r.target_values?.[t.symbol] === 'number')) continue;
		const line = lines.get(r.design_id);
		if (line) line.names.push(r.name);
		else {
			lines.set(r.design_id, {
				names: [r.name],
				values: targets.map((t) => r.target_values![t.symbol])
			});
		}
	}
	const designIds = [...lines.keys()];
	return {
		designIds,
		labels: designIds.map((id) => `#${id} ${lines.get(id)!.names.join(', ')}`),
		values: designIds.map((id) => lines.get(id)!.values)
	};
}

/** A point by target symbol as an array in target order; null if a target is missing. */
export function pointArray(point: Record<string, number>, targets: Target[]): number[] | null {
	const values = targets.map((t) => point[t.symbol]);
	return values.every((v) => typeof v === 'number') ? values : null;
}
