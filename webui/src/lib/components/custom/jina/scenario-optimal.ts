/* Chart lines, infeasible scenarios and range limits of designs optimised for one scenario. */

import type { JinaIterateResult, ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';
import type { Range } from './reference-point';
import { scenarioLines, type ChartLines } from './scenario-chart';

/** A successful result of the iterate state `stateId`, optimised for the scenario `leaf`. */
export interface OutcomeRow {
	stateId: number;
	leaf: string;
	result: JinaIterateResult;
}

/** Lines of scenario-optimal rows; `rowKeys` holds each line's row key. */
export interface OutcomeLines extends ChartLines {
	rowKeys: string[];
}

/** The key of a row: its state id and result name, as rows can share a design id. */
export function rowKey(stateId: number, name: string): string {
	return `${stateId}:${name}`;
}

/** One line per row and checked scenario with a successful outcome that has every objective. */
export function outcomeLines(
	rows: OutcomeRow[],
	leaves: string[],
	leafOrder: string[],
	objectives: string[],
	selected: string | null
): OutcomeLines {
	const keys = rows.map((row) => rowKey(row.stateId, row.result.name));
	const indices = rows.flatMap((row, i) => (row.result.design_id != null ? [i] : []));
	const leafObjectives = Object.fromEntries(
		indices.map((i) => [
			i,
			Object.fromEntries(
				Object.entries(rows[i].result.outcomes ?? {}).flatMap(([leaf, outcome]) =>
					outcome.status ? [[leaf, outcome.objectives ?? {}]] : []
				)
			)
		])
	);
	// Lines are built per row index, so rows sharing a design id stay separate.
	const lines = scenarioLines(
		indices,
		leafObjectives,
		leaves,
		leafOrder,
		objectives,
		selected === null ? null : keys.indexOf(selected)
	);
	return {
		...lines,
		designIds: lines.designIds.map((i) => rows[i].result.design_id!),
		labels: lines.designIds.map((i, line) => {
			const { leaf, result } = rows[i];
			return `#${result.design_id} ${result.name} (for ${leaf}) — ${lines.leaves[line]}`;
		}),
		rowKeys: lines.designIds.map((i) => keys[i])
	};
}

/** The failed scenarios of each row with their messages, by row key and in leaf order. */
export function infeasibleByRow(
	rows: OutcomeRow[],
	leafOrder: string[]
): Record<string, { leaf: string; message: string }[]> {
	return Object.fromEntries(
		rows.map(({ stateId, result }) => [
			rowKey(stateId, result.name),
			Object.entries(result.outcomes ?? {})
				.flatMap(([leaf, outcome]) => (outcome.status ? [] : [{ leaf, message: outcome.message }]))
				.sort((a, b) => leafOrder.indexOf(a.leaf) - leafOrder.indexOf(b.leaf))
		])
	);
}

/**
 * The problem with each objective's ideal and nadir widened to cover its values in `rows`, which are
 * in objective order. Null values are skipped, as are objectives without an ideal or a nadir.
 */
export function extendToValues(problem: ProblemInfo, rows: (number | null)[][]): ProblemInfo {
	const objectives = problem.objectives.map((objective, i) => {
		const { ideal, nadir, maximize } = objective;
		if (ideal == null || nadir == null) return objective;
		const values = rows.flatMap((row) => row[i] ?? []);
		const better = maximize ? Math.max : Math.min;
		const worse = maximize ? Math.min : Math.max;
		return { ...objective, ideal: better(ideal, ...values), nadir: worse(nadir, ...values) };
	});
	return { ...problem, objectives };
}

/** The value limited to the range, and whether it was outside by more than a rounding error. */
export function limitToRange(value: number, range: Range): { value: number; limited: boolean } {
	const [ideal, nadir] = range;
	const limited = Math.min(Math.max(value, Math.min(...range)), Math.max(...range));
	const tolerance = 1e-9 * Math.max(Math.abs(nadir - ideal), Math.abs(ideal), Math.abs(nadir));
	return { value: limited, limited: Math.abs(value - limited) > tolerance };
}
