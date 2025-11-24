/*Types specific for NIMBUS */

import type { components } from "$lib/api/client-types";
import type { BaseMethodResponse, PeriodKey } from "$lib/types";

// Type for objective values in reference points and solutions
export type ObjectiveValues = {
    [key: string]: number;
};

// General response type that includes all possible fields
export type Response = BaseMethodResponse & {
    previous_preference?: components["schemas"]["ReferencePoint"];
    previous_objectives?: ObjectiveValues;
    reference_solution_1?: ObjectiveValues;
    reference_solution_2?: ObjectiveValues;
};

export type ReferencePoint = components["schemas"]["ReferencePoint"];
export type FinishResponse = components["schemas"]["NIMBUSFinalizeResponse"];

export interface MapState {
		mapOptions: Record<PeriodKey, Record<string, any>>;
		yearlist: string[];
		selectedPeriod: PeriodKey;
		geoJSON: object | undefined;
		mapName: string | undefined;
		mapDescription: string | undefined;
	}