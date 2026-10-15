import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';

const setObjectiveConstraints = vi.fn();
const modifyProblem = vi.fn();
const modifyProblemStatus = vi.fn();
const getScenarioAvailability = vi.fn();
const applyScenarioMeasures = vi.fn();

vi.mock('$lib/gen/endpoints/DESDEOFastAPI', () => ({
	setObjectiveConstraintsMethodCumulusObjectiveConstraintPost: (...args: unknown[]) =>
		setObjectiveConstraints(...args),
	modifyProblemMethodCumulusModifyProblemPost: (...args: unknown[]) => modifyProblem(...args),
	modifyProblemStatusMethodCumulusModifyProblemStatusStateIdGet: (...args: unknown[]) =>
		modifyProblemStatus(...args),
	getScenarioAvailabilityMethodCumulusScenarioAvailabilityGet: (...args: unknown[]) =>
		getScenarioAvailability(...args),
	applyScenarioMeasuresMethodCumulusApplyScenarioMeasuresPost: (...args: unknown[]) =>
		applyScenarioMeasures(...args),
	// The module is imported wholesale, so every other endpoint the handlers pull in has to exist.
	solveSolutionsMethodCumulusSolvePost: vi.fn(),
	getOrInitializeMethodCumulusGetOrInitializePost: vi.fn(),
	saveMethodCumulusSavePost: vi.fn(),
	deleteSaveMethodCumulusDeleteSavePost: vi.fn(),
	finalizeMethodCumulusFinalizePost: vi.fn(),
	solveIntermediateMethodCumulusIntermediatePost: vi.fn(),
	getUtopiaDataUtopiaPost: vi.fn(),
	getSolutionDescriptionSolutionDescriptionGetPost: vi.fn()
}));

const {
	set_objective_constraints,
	poll_modification_status,
	check_scenario_availability,
	apply_scenario_measures
} = await import('./handlers');
const { errorMessage } = await import('../../../stores/uiState');

import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';

/** A problem stub carrying only what the constraint handlers actually read. */
function make_problem(constraint_symbols: string[] = []): ProblemInfo {
	return {
		id: 7,
		constraints: constraint_symbols.map((symbol) => ({ symbol })),
		objectives: []
	} as unknown as ProblemInfo;
}

const SOFT_OK = {
	status: 200,
	data: { state_id: 99, hard_constraint_ids: [], soft_constraint_ids: [11] }
};

/** The modify-problem POST reply: a provisional problem, checks still pending. */
function modification_accepted(overrides: Record<string, unknown> = {}) {
	return {
		status: 200,
		data: {
			state_id: 42,
			problem_id: 8,
			original_problem_id: 7,
			is_ready: false,
			current_solution_feasible: true,
			...overrides
		}
	};
}

beforeEach(() => {
	vi.clearAllMocks();
	errorMessage.set(null);
	setObjectiveConstraints.mockResolvedValue(SOFT_OK);
});

describe('set_objective_constraints', () => {
	it('sends a soft-only list straight to the current problem', async () => {
		const result = await set_objective_constraints(make_problem(), 5, [
			{ func: 'f_1 - 100', type: '<=0 (soft)' }
		]);

		expect(modifyProblem).not.toHaveBeenCalled();
		expect(setObjectiveConstraints).toHaveBeenCalledWith({
			problem_id: 7,
			parent_state_id: 5,
			hard_constraints: [],
			soft_constraints: [{ name: 'f_1 - 100', symbol: 'oc_1', func: 'f_1 - 100', cons_type: '<=' }]
		});
		expect(result).toMatchObject({ state_id: 99, new_problem_id: null });
	});

	it('still posts an empty soft list, so removing every constraint clears them', async () => {
		await set_objective_constraints(make_problem(), null, []);

		expect(setObjectiveConstraints).toHaveBeenCalledWith(
			expect.objectContaining({ soft_constraints: [] })
		);
	});

	it('routes hard bounds through modify-problem and reports the new problem', async () => {
		modifyProblem.mockResolvedValue(modification_accepted());
		modifyProblemStatus
			.mockResolvedValueOnce({ status: 200, data: { is_ready: false } })
			.mockResolvedValueOnce({
				status: 200,
				data: { is_ready: true, problem_id: 8, problem_deleted: false, error: null }
			});

		const progress: string[] = [];
		const result = await set_objective_constraints(
			make_problem(),
			5,
			[{ func: 'f_1 - 100', type: '<=0' }],
			(message) => progress.push(message)
		);

		expect(modifyProblem).toHaveBeenCalledWith({
			problem_id: 7,
			parent_state_id: 5,
			modifications: {
				constraints: [{ name: 'f_1 - 100', symbol: 'oc_1', func: 'f_1 - 100', cons_type: '<=' }]
			}
		});
		expect(modifyProblemStatus).toHaveBeenCalledWith(42);
		expect(result).toMatchObject({ new_problem_id: 8, current_solution_excluded: false });
		expect(progress.length).toBeGreaterThan(0);
	});

	it('applies hard bounds first and stores the soft list against the new problem', async () => {
		modifyProblem.mockResolvedValue(modification_accepted());
		modifyProblemStatus.mockResolvedValue({
			status: 200,
			data: { is_ready: true, problem_id: 8, problem_deleted: false, error: null }
		});

		await set_objective_constraints(make_problem(), 5, [
			{ func: 'f_1 - 100', type: '<=0' },
			{ func: 'f_2 - 50', type: '<=0 (soft)' }
		]);

		expect(modifyProblem.mock.invocationCallOrder[0]).toBeLessThan(
			setObjectiveConstraints.mock.invocationCallOrder[0]
		);
		// The soft list goes to the rebuilt problem, parented on the modification state, and is
		// numbered past the hard bound so the two cannot collide.
		expect(setObjectiveConstraints).toHaveBeenCalledWith({
			problem_id: 8,
			parent_state_id: 42,
			hard_constraints: [],
			soft_constraints: [{ name: 'f_2 - 50', symbol: 'oc_2', func: 'f_2 - 50', cons_type: '<=' }]
		});
	});

	it('applies nothing when the discarded problem takes its status state with it', async () => {
		modifyProblem.mockResolvedValue(modification_accepted({ current_solution_feasible: false }));
		modifyProblemStatus.mockResolvedValue({ status: 404, data: { detail: 'State 42 not found.' } });

		const result = await set_objective_constraints(make_problem(), 5, [
			{ func: 'f_1 - 100', type: '<=0' },
			{ func: 'f_2 - 50', type: '<=0 (soft)' }
		]);

		expect(result).toBeNull();
		expect(setObjectiveConstraints).not.toHaveBeenCalled();
		expect(get(errorMessage)).toContain('discarded');
	});

	it('applies nothing when the bounds make the problem infeasible', async () => {
		modifyProblem.mockResolvedValue(modification_accepted({ current_solution_feasible: false }));
		modifyProblemStatus.mockResolvedValue({
			status: 200,
			data: {
				is_ready: true,
				problem_deleted: true,
				error: 'The modified problem has no feasible solution.'
			}
		});

		const result = await set_objective_constraints(make_problem(), 5, [
			{ func: 'f_1 - 100', type: '<=0' },
			{ func: 'f_2 - 50', type: '<=0 (soft)' }
		]);

		expect(result).toBeNull();
		expect(setObjectiveConstraints).not.toHaveBeenCalled();
		expect(get(errorMessage)).toContain('no feasible solution');
	});

	it('reports an accepted bound that excludes the current solution', async () => {
		modifyProblem.mockResolvedValue(modification_accepted({ current_solution_feasible: false }));
		modifyProblemStatus.mockResolvedValue({
			status: 200,
			data: { is_ready: true, problem_id: 8, problem_deleted: false, error: null }
		});

		const progress: string[] = [];
		const result = await set_objective_constraints(
			make_problem(),
			5,
			[{ func: 'f_1 - 100', type: '<=0' }],
			(message) => progress.push(message)
		);

		expect(result).toMatchObject({ new_problem_id: 8, current_solution_excluded: true });
		expect(progress[0]).toContain('outside the new bounds');
	});

	it('numbers new constraints past the ones the problem already carries', async () => {
		modifyProblem.mockResolvedValue(modification_accepted());
		modifyProblemStatus.mockResolvedValue({
			status: 200,
			data: { is_ready: true, problem_id: 8, problem_deleted: false, error: null }
		});

		// A second hard bound must be added, not silently replace `oc_1` and `oc_2`.
		await set_objective_constraints(make_problem(['oc_1', 'oc_2', 'g_1']), null, [
			{ func: 'f_3 - 10', type: '=0' }
		]);

		expect(modifyProblem).toHaveBeenCalledWith(
			expect.objectContaining({
				modifications: {
					constraints: [{ name: 'f_3 - 10', symbol: 'oc_3', func: 'f_3 - 10', cons_type: '=' }]
				}
			})
		);
	});

	it('keeps the session on the current problem when the soft list cannot be stored', async () => {
		modifyProblem.mockResolvedValue(modification_accepted());
		modifyProblemStatus.mockResolvedValue({
			status: 200,
			data: { is_ready: true, problem_id: 8, problem_deleted: false, error: null }
		});
		setObjectiveConstraints.mockResolvedValue({ status: 422, data: { detail: 'bad expression' } });

		const result = await set_objective_constraints(make_problem(), 5, [
			{ func: 'f_1 - 100', type: '<=0' },
			{ func: 'nonsense(', type: '<=0 (soft)' }
		]);

		expect(result).toBeNull();
		expect(get(errorMessage)).toContain('bad expression');
		expect(get(errorMessage)).toContain('stayed on the current one');
	});

	it('reports the failure when modify-problem itself is rejected', async () => {
		modifyProblem.mockResolvedValue({ status: 422, data: { detail: 'unknown symbol f_9' } });

		const result = await set_objective_constraints(make_problem(), 5, [
			{ func: 'f_9 - 1', type: '<=0' }
		]);

		expect(result).toBeNull();
		expect(modifyProblemStatus).not.toHaveBeenCalled();
		expect(setObjectiveConstraints).not.toHaveBeenCalled();
		expect(get(errorMessage)).toContain('unknown symbol f_9');
	});
});

describe('poll_modification_status', () => {
	it('polls until the background check reports it is ready', async () => {
		modifyProblemStatus
			.mockResolvedValueOnce({ status: 200, data: { is_ready: false } })
			.mockResolvedValueOnce({ status: 200, data: { is_ready: false } })
			.mockResolvedValueOnce({ status: 200, data: { is_ready: true, problem_id: 8 } });

		const outcome = await poll_modification_status(42, { interval_ms: 0 });

		expect(modifyProblemStatus).toHaveBeenCalledTimes(3);
		expect(outcome).toMatchObject({ kind: 'accepted', response: { problem_id: 8 } });
	});

	it('reads a rejection off a ready response', async () => {
		modifyProblemStatus.mockResolvedValue({
			status: 200,
			data: { is_ready: true, problem_deleted: true, error: 'smallest total violation is 0.4' }
		});

		const outcome = await poll_modification_status(42, { interval_ms: 0 });

		expect(outcome).toEqual({ kind: 'rejected', reason: 'smallest total violation is 0.4' });
	});

	it('reads a vanished state as a rejection', async () => {
		// Discarding an infeasible modification deletes the problem, and the state reporting the
		// outcome goes with it, so the poll that should have carried the verdict 404s instead.
		modifyProblemStatus.mockResolvedValue({ status: 404, data: { detail: 'State 42 not found.' } });

		const outcome = await poll_modification_status(42, { interval_ms: 0 });

		expect(modifyProblemStatus).toHaveBeenCalledTimes(1);
		expect(outcome).toMatchObject({ kind: 'rejected' });
	});

	it('gives up once the check outlasts the timeout', async () => {
		modifyProblemStatus.mockResolvedValue({ status: 200, data: { is_ready: false } });

		const outcome = await poll_modification_status(42, { interval_ms: 0, timeout_ms: 0 });

		expect(outcome).toEqual({ kind: 'failed' });
		expect(get(errorMessage)).toContain('longer than expected');
	});

	it('stops polling when the status endpoint fails outright', async () => {
		modifyProblemStatus.mockResolvedValue({ status: 500, data: { detail: 'boom' } });

		const outcome = await poll_modification_status(42, { interval_ms: 0 });

		expect(outcome).toEqual({ kind: 'failed' });
		expect(modifyProblemStatus).toHaveBeenCalledTimes(1);
		expect(get(errorMessage)).toContain('boom');
	});
});

describe('check_scenario_availability', () => {
	it('reports availability straight from the endpoint response', async () => {
		getScenarioAvailability.mockResolvedValue({
			status: 200,
			data: {
				available: true,
				base_problem_id: 7,
				scenario_model_id: 3,
				objective_symbols: ['f_1']
			}
		});

		const result = await check_scenario_availability(7);

		expect(getScenarioAvailability).toHaveBeenCalledWith({ problem_id: 7 });
		expect(result).toEqual({
			available: true,
			base_problem_id: 7,
			scenario_model_id: 3,
			objective_symbols: ['f_1']
		});
	});

	it('returns null when the endpoint fails', async () => {
		getScenarioAvailability.mockResolvedValue({ status: 500, data: { detail: 'boom' } });

		const result = await check_scenario_availability(7);

		expect(result).toBeNull();
	});
});

describe('apply_scenario_measures', () => {
	it('sends the chosen measures and returns the rebuilt problem state', async () => {
		applyScenarioMeasures.mockResolvedValue({ status: 200, data: { problem_id: 9 } });

		const result = await apply_scenario_measures(
			7,
			3,
			['f_1', 'f_2'],
			['expected_value'],
			{},
			'combined'
		);

		expect(applyScenarioMeasures).toHaveBeenCalledWith({
			problem_id: 7,
			name: 'combined',
			uncertainty_measures: [
				{ measure_type: 'expected_value', scenario_model_id: 3, symbols: ['f_1', 'f_2'] }
			]
		});
		expect(result).toEqual({ problem_id: 9 });
	});

	it('reports an error and returns null when the endpoint rejects the measures', async () => {
		applyScenarioMeasures.mockResolvedValue({ status: 422, data: { detail: 'no scenario model' } });

		const result = await apply_scenario_measures(7, 3, ['f_1'], ['expected_value']);

		expect(result).toBeNull();
		expect(get(errorMessage)).toContain('422');
	});
});
