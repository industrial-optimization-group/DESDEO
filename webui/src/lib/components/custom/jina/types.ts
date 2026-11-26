/* JINA states with their result kind narrowed. */

import type {
	JinaAntifragilityResponse,
	JinaStateResponse,
	JinaSetupResult,
	JinaIterateStateResult,
	JinaEvaluateResult,
	JinaSelectResult
} from '$lib/gen/endpoints/DESDEOFastAPI';

type View = 'aggregated' | 'per_scenario';
export type SolveView = View | 'scenario_optimal';
export type Measure = JinaSetupResult['measure'];

export type SetupState = JinaStateResponse & { result: JinaSetupResult };
export type IterateState = JinaStateResponse & { result: JinaIterateStateResult };
export type EvaluateState = JinaStateResponse & { result: JinaEvaluateResult };
export type SelectState = JinaStateResponse & { result: JinaSelectResult };

/** An antifragility analysis with the evaluation and objectives it was computed for. */
export interface AntifragilityResult {
	evaluateStateId: number;
	analysis: JinaAntifragilityResponse;
	objectives: string[];
}

/** The floor entries of an evaluation; an emptied entry holds null. */
export interface AntifragilityInputs {
	absoluteFloors: Record<string, number | null>;
	lossFloors: Record<string, number | null>;
}
