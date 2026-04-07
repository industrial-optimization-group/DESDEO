import type { ENautilusRepresentativeSolutionsResponse, ENautilusSessionTreeResponse, ENautilusSimulateResponse, ENautilusStateResponse, ENautilusStepRequest, ENautilusStepResponse, ProblemInfo, VariableFixing, RPMState } from "$lib/gen/models";
import type { getRepresentativeMethodEnautilusGetRepresentativeStateIdGetResponse, getSessionTreeMethodEnautilusSessionTreeSessionIdGetResponse, getStateMethodEnautilusGetStateStateIdGetResponse, simulateMethodEnautilusSimulatePostResponse, stepMethodEnautilusStepPostResponse } from "$lib/gen/endpoints/DESDEOFastAPI";
import { stepMethodEnautilusStepPost, getProblemProblemProblemIdGet, getStateMethodEnautilusGetStateStateIdGet, getRepresentativeMethodEnautilusGetRepresentativeStateIdGet, getSessionTreeMethodEnautilusSessionTreeSessionIdGet, simulateMethodEnautilusSimulatePost, createConstrainedVariantProblemProblemIdConstrainedVariantPost, solveSolutionsMethodRpmSolvePost, deleteProblemProblemProblemIdDelete } from "$lib/gen/endpoints/DESDEOFastAPI";
import type { getProblemProblemProblemIdGetResponse } from "$lib/gen/endpoints/DESDEOFastAPI";
import { fetch_sessions, create_session } from '../../methods/sessions/handler';
export { fetch_sessions, create_session };

export type ENautilusStepBundle = {
    request: ENautilusStepRequest;
    response: ENautilusStepResponse;
}

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
    representative_solutions_id: number,
    session_id: number | null
): Promise<ENautilusStepBundle | null> {
    const selected_point = current_state.intermediate_points[selected_index];
    const reachable_indices = current_state.reachable_point_indices[selected_index];

    const request: ENautilusStepRequest = {
        problem_id: problem_id,
        representative_solutions_id: representative_solutions_id,
        current_iteration: current_state.current_iteration,
        iterations_left: iterations_left,
        selected_point: selected_point,
        reachable_point_indices: reachable_indices,
        number_of_intermediate_points: number_of_intermediate_points,
        parent_state_id: current_state.state_id ?? undefined,
        session_id: session_id,
    }

    console.log(request);
    if (current_state.state_id == null) {
	    console.warn('step_enautilus: current_state.state_id is null; parent_state_id will be omitted');
    }


    const response: stepMethodEnautilusStepPostResponse = await stepMethodEnautilusStepPost(request);

    if (response.status != 200) {
        console.error("E-NAUTILUS step failed.", response.status);
        return null;
    }

    return {request: request, response: response.data};
}

export async function fetch_problem_info(problem_id: number): Promise<ProblemInfo | null> {
    const response: getProblemProblemProblemIdGetResponse = await getProblemProblemProblemIdGet(problem_id);

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

export async function fetch_enautilus_state(state_id: number): Promise<ENautilusStateResponse | null> {
    const response: getStateMethodEnautilusGetStateStateIdGetResponse = await getStateMethodEnautilusGetStateStateIdGet(state_id);

    if (response.status !== 200) {
        console.error("Failed to fetch E-NAUTILUS state:", response.status);
        return null;
    }

    return response.data;
}

export async function fetch_representative_solutions(
    state_id: number
): Promise<ENautilusRepresentativeSolutionsResponse | null> {
    const response: getRepresentativeMethodEnautilusGetRepresentativeStateIdGetResponse = await getRepresentativeMethodEnautilusGetRepresentativeStateIdGet(state_id);

    if (response.status !== 200) {
        console.error("Failed to fetch representative solutions:", response.status);
        return null;
    }

    return response.data;
}

export async function fetch_session_tree(
    session_id: number
): Promise<ENautilusSessionTreeResponse | null> {
    const response: getSessionTreeMethodEnautilusSessionTreeSessionIdGetResponse = await getSessionTreeMethodEnautilusSessionTreeSessionIdGet(session_id);

    if (response.status !== 200) {
        console.error("Failed to fetch session tree:", response.status);
        return null;
    }

    return response.data;
}

export async function simulate_enautilus(
    state_id: number,
    preferred_objective: string,
    number_of_intermediate_points?: number,
): Promise<ENautilusSimulateResponse | null> {
    const response: simulateMethodEnautilusSimulatePostResponse = await simulateMethodEnautilusSimulatePost({
        state_id,
        preferred_objective,
        ...(number_of_intermediate_points != null ? { number_of_intermediate_points } : {}),
    });

    if (response.status !== 200) {
        console.error("E-NAUTILUS simulation failed:", response.status);
        return null;
    }

    return response.data;
}

export async function resolveWithSiteConstraints(
    problem_id: number,
    fixings: VariableFixing[],
    reference_point: Record<string, number>,
    solver?: string,
): Promise<{ constrained_problem_id: number; rpm_result: RPMState } | null> {
    // Step 1: Create constrained variant
    const variantResp = await createConstrainedVariantProblemProblemIdConstrainedVariantPost(
        problem_id,
        { variable_fixings: fixings }
    );

    if (variantResp.status !== 200) {
        console.error("Failed to create constrained variant:", variantResp.status);
        return null;
    }

    const constrained_problem_id = variantResp.data.problem_id;

    // Step 2: Solve with RPM using E-NAUTILUS final objectives as reference point
    try {
        const rpmResp = await solveSolutionsMethodRpmSolvePost({
            problem_id: constrained_problem_id,
            preference: {
                preference_type: "reference_point",
                aspiration_levels: reference_point,
            },
            solver: solver ?? undefined,
        });

        if (rpmResp.status !== 200) {
            console.error("RPM solve failed:", rpmResp.status);
            // Cleanup on failure
            await cleanupConstrainedVariant(constrained_problem_id);
            return null;
        }

        return {
            constrained_problem_id,
            rpm_result: rpmResp.data,
        };
    } catch (e) {
        // Cleanup on error
        await cleanupConstrainedVariant(constrained_problem_id);
        throw e;
    }
}

/**
 * Unroll tensor variables in a SolverResults object.
 * RPM returns tensor variables as e.g. {"sv": [[v1], [v2], ...]} for shape [N, 1].
 * The map and other components expect unrolled names: {"sv_1": v1, "sv_2": v2, ...}.
 * Scalar values and already-unrolled variables are passed through unchanged.
 */
export function unrollTensorVariables(
    variables: Record<string, unknown>
): Record<string, unknown> {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(variables)) {
        if (Array.isArray(value) && value.length > 0 && Array.isArray(value[0])) {
            // Nested list (tensor variable) — flatten with 1-based indexing
            let flatIdx = 1;
            const flatten = (arr: unknown[]): void => {
                for (const el of arr) {
                    if (Array.isArray(el)) {
                        flatten(el);
                    } else {
                        result[`${key}_${flatIdx}`] = el;
                        flatIdx++;
                    }
                }
            };
            flatten(value);
        } else {
            result[key] = value;
        }
    }
    return result;
}

export async function cleanupConstrainedVariant(constrained_problem_id: number): Promise<void> {
    try {
        await deleteProblemProblemProblemIdDelete(constrained_problem_id);
    } catch (e) {
        console.warn("Failed to clean up constrained variant:", e);
    }
}

export type { VariableFixing };
