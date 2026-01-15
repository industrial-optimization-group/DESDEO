import type { ENautilusStepRequest, ENautilusStepResponse, ProblemGetRequest, ProblemInfo } from "$lib/gen/models";
import type { stepMethodEnautilusStepPostResponse } from "$lib/gen/endpoints/DESDEOFastAPI";
import { stepMethodEnautilusStepPost, getProblemProblemGetPost } from "$lib/gen/endpoints/DESDEOFastAPI";
import type { getProblemProblemGetPostResponse } from "$lib/gen/endpoints/DESDEOFastAPI";

export async function initialize_enautilus_state(request: ENautilusStepRequest): Promise<ENautilusStepResponse | null> {
    const response: stepMethodEnautilusStepPostResponse = await stepMethodEnautilusStepPost(request)

    if (response.status != 200){
        console.log("E-NAUTILUS init failed.", response.status);
        return null;
    }

    return response.data;
}

export async function step_enautilus(
    current_state: ENautilusStepResponse,
    selected_index: number,
    problem_id: number,
    number_of_intermediate_points: number,
    iterations_left: number,
    representative_solutions_id: number
): Promise<ENautilusStepResponse | null> {
    const selected_point = current_state.intermediate_points[selected_index];
    const reachable_indices = current_state.reachable_point_indices[selected_index];

    const request: ENautilusStepRequest = {
        problem_id: problem_id,
        representative_solutions_id: representative_solutions_id,
        current_iteration: current_state.current_iteration,
        iterations_left: iterations_left,
        selected_point: selected_point,
        reachable_point_indices: reachable_indices,
        number_of_intermediate_points: number_of_intermediate_points
        // parent state
        //session id
    }

    console.log(request);

    const response: stepMethodEnautilusStepPostResponse = await stepMethodEnautilusStepPost(request);

    if (response.status != 200) {
        console.error("E-NAUTILUS step failed.", response.status);
        return null;
    }

    return response.data;
}

export async function fetch_problem_info(request: ProblemGetRequest): Promise<ProblemInfo | null> {
    const response: getProblemProblemGetPostResponse = await getProblemProblemGetPost(request);

    if (response.status != 200) {
        console.log("Could not fetch problem info.", response.status);
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