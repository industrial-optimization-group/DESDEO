/* Display labels, number formatting and error messages for JINA components. */

import type { JinaScenarioModelInfo, ProblemInfo, Target } from '$lib/gen/endpoints/DESDEOFastAPI';
import type { Measure } from './types';

export const MEASURE_LABELS: Record<Measure, string> = {
	worst_case: 'Worst case',
	expected_value: 'Expected value',
	cvar: 'CVaR'
};

export function objectiveLabel(problem: ProblemInfo, symbol: string): string {
	const objective = problem.objectives.find((o) => o.symbol === symbol);
	const name = objective?.name ?? symbol;
	return objective?.unit ? `${name} (${objective.unit})` : name;
}

export function targetLabel(problem: ProblemInfo, target: Target): string {
	const label = objectiveLabel(problem, target.objective);
	return target.leaf ? `${label} — ${target.leaf}` : label;
}

/** `count` with the singular or plural noun. */
export function plural(count: number, singular: string, pluralForm = `${singular}s`): string {
	return `${count} ${count === 1 ? singular : pluralForm}`;
}

/** The model's id, leaf count and leaves; unless `full`, only the first few leaves. */
export function modelLabel(model: JinaScenarioModelInfo, full = false, shown = 3): string {
	const leaves =
		full || model.leaves.length <= shown
			? model.leaves.join(', ')
			: `${model.leaves.slice(0, shown).join(', ')}, …`;
	return `#${model.id} — ${plural(model.n_leaves, 'leaf', 'leaves')}: ${leaves}`;
}

/** An evaluation's state id and scenario model, the setup's or a stress test. */
export function evaluationLabel(stateId: number, modelId: number, setupModelId: number): string {
	const kind = modelId === setupModelId ? 'setup' : 'stress test';
	return `Evaluation ${stateId} — model #${modelId} (${kind})`;
}

/** The leaves with the baseline first and the others in their given order. */
export function baselineFirst(leaves: string[], baseline: string | null): string[] {
	if (baseline === null || !leaves.includes(baseline)) return leaves;
	return [baseline, ...leaves.filter((l) => l !== baseline)];
}

export function formatNumber(value: number | null | undefined, digits = 4): string {
	if (value === null || value === undefined || !Number.isFinite(value)) return '—';
	return Number(value.toPrecision(digits)).toString();
}

/** A number in compact SI form, e.g. "-32.1M", "7.9k", "158", "0.12". */
export function compactNumber(value: number | null | undefined): string {
	if (value === null || value === undefined || !Number.isFinite(value)) return '—';
	if (value === 0) return '0';
	const abs = Math.abs(value);
	const [divisor, suffix] =
		abs >= 1e9 ? [1e9, 'B'] : abs >= 1e6 ? [1e6, 'M'] : abs >= 1e3 ? [1e3, 'k'] : [1, ''];
	const scaled = value / divisor;
	if (!suffix && abs < 1) return formatNumber(value, 2);
	const digits = Math.abs(scaled) >= 100 ? 0 : Math.abs(scaled) >= 10 ? 1 : suffix ? 1 : 2;
	return `${Number(scaled.toFixed(digits))}${suffix}`;
}

/** Scalars as numbers; vectors and matrices by their first entries. */
export function formatValue(value: unknown): string {
	if (typeof value === 'number') return formatNumber(value);
	if (Array.isArray(value)) {
		const flat = (value as unknown[]).flat(2) as number[];
		const shown = flat.slice(0, 4).map((v) => formatNumber(v, 3));
		return `[${shown.join(', ')}${flat.length > 4 ? `, … (${flat.length})` : ''}]`;
	}
	return String(value);
}

/** The message of an error response: FastAPI's `detail` string, or its validation messages. */
export function errorDetail(status: number, data: unknown): string {
	const detail = (data as { detail?: unknown } | null)?.detail;
	if (typeof detail === 'string') return detail;
	if (Array.isArray(detail)) {
		return (detail as { msg?: string }[]).map((d) => d?.msg ?? JSON.stringify(d)).join('; ');
	}
	return `Request failed with status ${status}`;
}
