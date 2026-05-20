/* Types specific for CUMULUS */

import type { ReferencePoint, CumulusFinalizeResponse } from '$lib/gen/endpoints/DESDEOFastAPI';
import type { BaseMethodResponse, PeriodKey, Solution } from '$lib/types';

export type ObjectiveValues = {
	[key: string]: number;
};

export type Response = BaseMethodResponse & {
	response_type:
		| 'cumulus.classification'
		| 'cumulus.initialization'
		| 'cumulus.intermediate'
		| 'cumulus.finalize'
		| 'cumulus.scenario_setup';
	previous_preference?: ReferencePoint;
	previous_objectives?: ObjectiveValues;
	reference_solution_1?: ObjectiveValues;
	reference_solution_2?: ObjectiveValues;
	// initialization: actual problem used (may differ when a combined scenario problem was built)
	problem_id?: number;
	// scenario_setup fields
	scenario_model_id?: number;
	objective_symbols?: string[];
	// finalize fields
	state_id?: number | null;
	final_solution?: Solution;
};

export type { ReferencePoint };
export type FinishResponse = CumulusFinalizeResponse;

export interface MapState {
	mapOptions: Record<PeriodKey, Record<string, any>>;
	yearlist: string[];
	selectedPeriod: PeriodKey;
	geoJSON: object | undefined;
	mapName: string | undefined;
	mapDescription: string | undefined;
}
