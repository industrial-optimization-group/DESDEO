import type { ProblemInfo, Solution } from '$lib/types';
import type { Response } from './types';
import { callNimbusAPI } from './helper-functions';
import { errorMessage, isLoading } from '../../../stores/error-store';

// Handler for intermediate solutions generation
export async function handle_intermediate(
    problem: ProblemInfo | null,
    selected_solutions: Solution[],
    num_desired: number
): Promise<Response | null> {
    if (!problem) {
        console.error('No problem selected');
        return null;
    }
    // Check if we have exactly 2 solutions selected
    if (selected_solutions.length !== 2) {
        console.error('Exactly 2 solutions must be selected for intermediate solutions');
        return null;
    }

    const result = await callNimbusAPI<Response>('intermediate', {
        problem_id: problem.id,
        session_id: null, // Using active session
        parent_state_id: null, // No specific parent
        reference_solution_1: selected_solutions[0],
        reference_solution_2: selected_solutions[1],
        num_desired: num_desired
    });

    if (result.success && result.data) {
        return result.data;
    } else {
        console.error('Failed to solve intermediate solutions:', result.error);
        return null;
    }
}

// Handler for iteration
export async function handle_iterate(
    problem: ProblemInfo,
    current_preference: number[],
    selected_iteration_objectives: Record<string, number>,
    current_num_iteration_solutions: number
): Promise<Response | null> {
    try {
        isLoading.set(true);
        errorMessage.set(null);

        const preference = {
            preference_type: 'reference_point',
            aspiration_levels: problem.objectives.reduce(
                (acc, obj, idx) => {
                    acc[obj.symbol] = current_preference[idx];
                    return acc;
                },
                {} as Record<string, number>
            )
        };

        const result = await callNimbusAPI<Response>('iterate', {
            problem_id: problem.id,
            session_id: null,
            parent_state_id: null,
            current_objectives: selected_iteration_objectives,
            num_desired: current_num_iteration_solutions,
            preference: preference
        });

        if (!result.success) {
            // Ensure error is always a string
            const errorMsg = result.error ?? 'Failed to iterate';
            errorMessage.set(errorMsg);
            return null;
        }

        return result.data || null;
    } catch (error) {
        const msg = error instanceof Error ? error.message : 'Unknown error';
        errorMessage.set(msg);
        return null;
    } finally {
        isLoading.set(false);
    }
}

// Handler for saving a solution
export async function handle_save(
    problem: ProblemInfo | null,
    solution: Solution,
    name: string | undefined
): Promise<boolean> {
    if (!problem) {
        console.error('No problem selected');
        return false;
    }

    // Create a copy of the solution with the name
    const solutionToSave = {
        ...solution,
        name: name ?? null
    };

    interface SaveResponse {
        success: boolean;
    }

    const result = await callNimbusAPI<SaveResponse>('save', {
        problem_id: problem.id,
        solution_info: [solutionToSave]
    });

    if (result.success) {
        return true;
    } else {
        console.error('Failed to save solution:', result.error);
        return false;
    }
}

// Handler for removing a saved solution
export async function handle_remove_saved(
    problem: ProblemInfo | null,
    solution: Solution
): Promise<boolean> {
    if (!problem) {
        console.error('No problem selected');
        return false;
    }

    interface RemoveResponse {
        success: boolean;
    }

    const result = await callNimbusAPI<RemoveResponse>('remove_saved', {
        problem_id: problem.id,
        solutions: [solution]
    });

    if (result.success) {
        return true;
    } else {
        console.error('Failed to remove saved solution:', result.error);
        return false;
    }
}

// Handler for finishing with a solution
export async function handle_finish(
    problem: ProblemInfo | null,
    solution: Solution
): Promise<boolean> {
    if (!problem) {
        console.error('No problem selected');
        return false;
    }

    interface FinishResponse {
        success: boolean;
    }

    const result = await callNimbusAPI<FinishResponse>('choose', {
        problem_id: problem.id,
        solution: solution
    });

    if (result.success) {
        return true;
    } else {
        console.error('Failed to save final choice:', result.error);
        return false;
    }
}

// Handler for getting maps data
export async function get_maps(
    problem: ProblemInfo,
    solution: Solution
): Promise<{
    years: string[];
    options: Record<string, any>;
    map_json: object;
    map_name: string;
    description: string;
    compensation: number;
} | null> {
    interface MapsResponse {
        years: string[];
        options: Record<string, any>;
        map_json: object;
        map_name: string;
        description: string;
        compensation: number;
    }

    const result = await callNimbusAPI<MapsResponse>('get_maps', {
        problem_id: problem.id,
        solution: solution
    });

    if (result.success && result.data) {
        // Apply the formatter function client-side
        for (const year of result.data.years) {
            if (result.data.options[year].tooltip.formatterEnabled) {
                result.data.options[year].tooltip.formatter = function (params: any) {
                    return `${params.name}`;
                };
            }
        }

        return result.data;
    } else {
        console.error('Failed to get maps:', result.error);
        return null;
    }
}

// Handler for initializing NIMBUS state
export async function initialize_nimbus_state(problem_id: number): Promise<Response | null> {
    const result = await callNimbusAPI<Response>('initialize', {
        problem_id: problem_id,
        session_id: null, // Use active session
        parent_state_id: null, // No parent for initialization
        solver: null // Use default solver
    });

    if (result.success && result.data) {
        return result.data;
    } else {
        console.error('NIMBUS initialization failed:', result.error);
        return null;
    }
}
