/*Types specific for NIMBUS */

import type { components } from "$lib/api/client-types";
import type {Solution} from "$lib/types";

export type Response = {
	state_id: number | null,
	previous_preference?: components["schemas"]["ReferencePoint"],
    previous_objectives?: {
		[key: string]: number;
	},
	reference_solution_1?: {
		[key: string]: number;
	},
	reference_solution_2?: {
		[key: string]: number;
	},
	current_solutions: Solution[],
	saved_solutions: Solution[],
	all_solutions: Solution[],
};