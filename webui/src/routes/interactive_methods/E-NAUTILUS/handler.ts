import type { components } from "$lib/api/client-types";
import { api } from "$lib/api/client";

type EnautilusStepRequest = components["schemas"]["EnautilusStepRequest"];
type ENautilusState = components["schemas"]["ENautilusState"];
type ENautilusResult = components["schemas"]["ENautilusResult"];
type ProblemGetRequest = components["schemas"]["ProblemGetRequest"];
type ProblemInfo = components["schemas"]["ProblemInfo"];

// Map from API response to what the UI expects
export function mapApiResponseToStepResponse(state: ENautilusState): ENautilusResult {
    return state.enautilus_results;
}

export async function initialize_enautilus_state(request: EnautilusStepRequest): Promise<ENautilusResult | null> {
    const response = await api.POST('/method/enautilus/step', { body: request });

    if (!response.data) {
        console.log("E-NAUTILUS init failed.");
        return null;
    }

    return mapApiResponseToStepResponse(response.data);
}

export async function step_enautilus(
    current_state: ENautilusResult,
    selected_index: number,
    problem_id: number,
    number_of_intermediate_points: number,
    iterations_left: number,
    representative_solutions_id: number
): Promise<ENautilusResult | null> {
    const selected_point = current_state.intermediate_points?.[selected_index];
    const reachable_indices = current_state.reachable_point_indices?.[selected_index];

    const request: EnautilusStepRequest = {
        problem_id: problem_id,
        representative_solutions_id: representative_solutions_id,
        current_iteration: current_state.current_iteration,
        iterations_left: iterations_left,
        selected_point: selected_point,
        reachable_point_indices: reachable_indices,
        number_of_intermediate_points: number_of_intermediate_points
    }

    console.log(request);

    const response = await api.POST('/method/enautilus/step', { body: request });

    if (!response.data) {
        console.error("E-NAUTILUS step failed.");
        return null;
    }

    return mapApiResponseToStepResponse(response.data);
}

export async function fetch_problem_info(request: ProblemGetRequest): Promise<ProblemInfo | null> {
    const response = await api.POST('/problem/get', { body: request });

    if (!response.data) {
        console.log("Could not fetch problem info.");
        return null;
    }

    return response.data;
}

export function points_to_list(points: Record<string, number>[]): number[][] {
    // Object.values preserves insertion order
    return points.map(
        (pt) => Object.values(pt)
    )
}