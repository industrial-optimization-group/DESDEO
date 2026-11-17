import { describe, it, expect } from 'vitest';
import type { Antifragility, DomainCriterion } from '$lib/gen/endpoints/DESDEOFastAPI';
import { scenarioLines } from './scenario-chart';
import {
	antifragilityHeatmap,
	domainCriterionShares,
	evaluatedDesigns,
	evaluatedLeafObjectives,
	evaluatedLeaves,
	evaluatedObjectives,
	FAILING_LINE_COLOR,
	meetsAllThresholds,
	meetsThreshold,
	thresholdLines,
	upsideDownside,
	type Outcomes
} from './robustness-charts';

const outcomes: Outcomes = {
	'10': {
		a: { status: true, message: '', objectives: { f: 1, g: 9 } },
		b: { status: true, message: '', objectives: { f: 4, g: 5 } }
	},
	'2': {
		a: { status: true, message: '', objectives: { f: 2, g: 7 } },
		b: { status: false, message: 'infeasible' }
	}
};

describe('evaluated outcomes', () => {
	it('list designs ascending, leaves and objectives in order of appearance', () => {
		expect(evaluatedDesigns(outcomes)).toEqual([2, 10]);
		expect(evaluatedLeaves(outcomes)).toEqual(['a', 'b']);
		expect(evaluatedObjectives(outcomes)).toEqual(['f', 'g']);
	});

	it('keep only the leaves where the evaluation succeeded', () => {
		expect(evaluatedLeafObjectives(outcomes)).toEqual({
			10: { a: { f: 1, g: 9 }, b: { f: 4, g: 5 } },
			2: { a: { f: 2, g: 7 } }
		});
	});
});

describe('domainCriterionShares', () => {
	it('gives the share of scenarios meeting all and each threshold', () => {
		const domain: Record<string, DomainCriterion> = {
			'7': { counts: { f: 2, g: 4 }, mean_count: 3, all_count: 3 },
			'1': { counts: { f: 0 }, mean_count: 0, all_count: 0 }
		};
		const shares = domainCriterionShares(domain, ['f', 'g'], 4);
		expect(shares.all).toEqual([0, 0.75]);
		expect(shares.perObjective.rows).toEqual([1, 7]);
		expect(shares.perObjective.cells).toEqual([
			[0, 0, 0],
			[1, 0, null],
			[0, 1, 0.5],
			[1, 1, 1]
		]);
	});

	it('gives no shares without leaves', () => {
		const domain = { '1': { counts: { f: 0 }, mean_count: 0, all_count: 0 } };
		const shares = domainCriterionShares(domain, ['f'], 0);
		expect(shares.all).toEqual([null]);
		expect(shares.perObjective.cells).toEqual([[0, 0, null]]);
	});
});

describe('meetsThreshold', () => {
	it('compares in the objective direction', () => {
		expect(meetsThreshold(5, 5, false)).toBe(true);
		expect(meetsThreshold(6, 5, false)).toBe(false);
		expect(meetsThreshold(6, 5, true)).toBe(true);
	});
});

describe('meetsAllThresholds', () => {
	it('compares minimised objectives with at most the threshold', () => {
		expect(meetsAllThresholds({ f: 2 }, { f: 2 }, { f: false })).toBe(true);
		expect(meetsAllThresholds({ f: 2.1 }, { f: 2 }, { f: false })).toBe(false);
	});

	it('compares maximised objectives with at least the threshold', () => {
		expect(meetsAllThresholds({ g: 5 }, { g: 5 }, { g: true })).toBe(true);
		expect(meetsAllThresholds({ g: 4.9 }, { g: 5 }, { g: true })).toBe(false);
	});

	it('ignores objectives absent from the values', () => {
		expect(meetsAllThresholds({ f: 1 }, { f: 2, g: 5 }, { f: false, g: true })).toBe(true);
		expect(meetsAllThresholds({ f: 3 }, { f: 2, g: 5 }, { f: false, g: true })).toBe(false);
	});

	it('allows a relative tolerance at the threshold', () => {
		expect(meetsAllThresholds({ f: 4 + 1e-9 }, { f: 4 }, { f: false })).toBe(true);
		expect(meetsAllThresholds({ f: 4.01 }, { f: 4 }, { f: false })).toBe(false);
		expect(meetsAllThresholds({ g: 6 - 1e-9 }, { g: 6 }, { g: true })).toBe(true);
		expect(meetsAllThresholds({ g: 5.99 }, { g: 6 }, { g: true })).toBe(false);
	});

	it('is false when no thresholded objective is present', () => {
		expect(meetsAllThresholds({ h: 1 }, { f: 2 }, { f: false })).toBe(false);
		expect(meetsAllThresholds({ f: 1 }, {}, {})).toBe(false);
	});
});

describe('thresholdLines', () => {
	it('grays failing lines and draws them first', () => {
		const leafObjectives = { 1: { a: { f: 1 }, b: { f: 3 } } };
		const lines = scenarioLines([1], leafObjectives, ['a', 'b'], ['a', 'b'], ['f'], null);
		const result = thresholdLines(lines, leafObjectives, { f: 2 }, { f: false });
		expect(result.leaves).toEqual(['b', 'a']);
		expect(result.colors).toEqual({ '0': FAILING_LINE_COLOR, '1': lines.colors['0'] });
		expect(result.values).toEqual([[3], [1]]);
	});
});

const summary = (antifragility: number | null, up: number | null, down: number | null) => ({
	upside: up,
	downside: down,
	antifragility,
	n_gain: 0,
	n_loss: 0,
	upside_raw: null,
	downside_raw: null,
	max_loss_raw: null,
	best_gain_leaf: null,
	worst_loss_leaf: null,
	worst_outcome: null,
	taleb_class: antifragility !== null && antifragility > 0 ? ('antifragile' as const) : null,
	deviations: []
});

describe('antifragility charts', () => {
	const af: Record<string, Antifragility> = {
		'3': { objectives: { f: summary(0.5, 0.6, 0.2), g: summary(null, null, null) } },
		'1': { objectives: { f: summary(-1, 0, 0.7), g: summary(0, 0.1, 0.1) } }
	};

	it('give the index and class per design and objective', () => {
		const data = antifragilityHeatmap(af, ['f', 'g']);
		expect(data.rows).toEqual([1, 3]);
		expect(data.cells).toEqual([
			[0, 0, -1],
			[1, 0, 0],
			[0, 1, 0.5],
			[1, 1, null]
		]);
		expect(data.classes).toEqual([null, null, 'antifragile', null]);
	});

	it('give upside and downside where both exist', () => {
		expect(upsideDownside(af, ['f', 'g'])).toEqual([
			{ designId: 1, objective: 'f', upside: 0, downside: 0.7 },
			{ designId: 1, objective: 'g', upside: 0.1, downside: 0.1 },
			{ designId: 3, objective: 'f', upside: 0.6, downside: 0.2 }
		]);
	});
});
