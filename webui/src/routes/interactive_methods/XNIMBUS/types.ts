/*Types specific for NIMBUS */

import type { components } from "$lib/api/client-types";
import type { BaseMethodResponse } from "$lib/types";

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