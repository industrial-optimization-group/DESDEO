/* Types specific for the reference point method. */

import type { ReferencePoint, NIMBUSFinalizeResponse, RPMState } from "$lib/gen/endpoints/DESDEOFastAPI";
import type { PeriodKey, Solution } from "$lib/types";

// Type for objective values in reference points and solutions
export type ObjectiveValues = {
    [key: string]: number;
};

export type RPMPageState = RPMState & {
	current_solutions: Solution[];
	saved_solutions: Solution[];
	all_solutions: Solution[];
	previous_preference?: ReferencePoint;
	previous_objectives?: ObjectiveValues;
	reference_solution_1?: ObjectiveValues;
	reference_solution_2?: ObjectiveValues;
	response_type?: 'rpm.finalize';
	final_solution?: Solution;
	state_id?: number | null;
};

export type { ReferencePoint };
export type FinishResponse = NIMBUSFinalizeResponse;

export interface MapState {
		mapOptions: Record<PeriodKey, Record<string, any>>;
		yearlist: string[];
		selectedPeriod: PeriodKey;
		geoJSON: object | undefined;
		mapName: string | undefined;
		mapDescription: string | undefined;
	}
