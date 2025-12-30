import type { components } from '$lib/api/client-types';
import { errorMessage, isLoading } from '../../../stores/uiState';


type ProblemInfo = components['schemas']['ProblemInfo'];
type Solution = components['schemas']['SolutionReferenceResponse'];

// Define the Response type needed for our helper functions
type NIMBUSClassificationResponse = components['schemas']['NIMBUSClassificationResponse'];
type NIMBUSInitializationResponse = components['schemas']['NIMBUSInitializationResponse'];
type BaseResponse = NIMBUSClassificationResponse | NIMBUSInitializationResponse;
type Response = BaseResponse & {
    current_solutions: Solution[],
    saved_solutions: Solution[],
    all_solutions: Solution[],
};


/**
 * Checks if a problem has utopia metadata for map visualization
 * @param prob The problem to check
 * @returns boolean indicating if the problem has utopia metadata
 */
export function checkUtopiaMetadata(prob: ProblemInfo | null) {
    // Check if the problem and its metadata exist
    if (!prob || !prob.problem_metadata) {
        return false;
    }

    // Check if forest_metadata exists and is not empty
    return (
        prob.problem_metadata.forest_metadata !== null &&
        Array.isArray(prob.problem_metadata.forest_metadata) &&
        prob.problem_metadata.forest_metadata.length > 0
    );
}
/**
 * Maps solutions objective values to arrays suitable for visualization components
 * @param solutions Array of solutions with objective values
 * @param problem The problem containing objective definitions
 * @returns Array of arrays with objective values in the order defined by the problem
 */
export function mapSolutionsToObjectiveValues(solutions: Solution[], problem: ProblemInfo) {
    return solutions.map((result) => {
        return problem.objectives.map((obj) => {
            const value = result.objective_values && result.objective_values[obj.symbol];
            return Array.isArray(value) ? value[0] : value;
        });
    });
}
/**
 * Creates a dictionary mapping objective symbols to their names
 * @param problem The problem containing objective definitions
 * @returns Record mapping objective symbols to names
 */

export function getDictionaryObjectiveNames(problem: ProblemInfo) {
    const objectiveNames: Record<string, string> = {};
    problem.objectives.forEach((obj) => {
        objectiveNames[obj.symbol] = obj.name ?? obj.symbol;
    });
    return objectiveNames;
}

/*export function mapSolutionToMultipliers(solutions: Solution[], problem: ProblemInfo) {
    return solutions.map((result) => {
        return problem.objectives.map((obj) => {
            const value = result.lagrange_multipliers && result.lagrange_multipliers[obj.symbol];
            return Array.isArray(value) ? value[0] : value;
        });
    });
}*/


/**
 * Initialize preferences from previous state or ideal values
 * @param state The current NIMBUS response state
 * @param problem The current problem
 * @returns Array of preference values
 */
export function updatePreferencesFromState(state: Response | null, problem: ProblemInfo | null): number[] {
    if (!problem) return [];
    
    // Try to get previous preference from NIMBUS state
    if (state && 'previous_preference' in state && state.previous_preference) {
        // Extract aspiration levels from previous preference
        const previous_pref = state.previous_preference as {
            aspiration_levels?: Record<string, number>;
        };
        if (previous_pref.aspiration_levels) {
            return problem.objectives.map(
                (obj) => previous_pref.aspiration_levels![obj.symbol] ?? obj.ideal ?? 0
            );
        }
    }
    
    // Fallback to ideal values
    return problem.objectives.map((obj) => obj.ideal ?? 0);
}

/**
 * Converts objective values in object format to array format
 * Used to transform previous objectives for visualization components
 * 
 * @param objectiveObj The objective values in object format keyed by symbol
 * @param problem The problem containing objective definitions
 * @returns Array of values in the order defined by the problem objectives
 */
export function convertObjectiveToArray(
    objectiveObj: Record<string, number> | undefined | null,
    problem: ProblemInfo | null
): number[] {
    if (!problem || !objectiveObj) {
        return [];
    }
    
    return problem.objectives.map(obj => {
        const value = objectiveObj[obj.symbol];
        return (value !== undefined && value !== null) ? (Array.isArray(value) ? value[0] : value) : 0;
    });
}

/**
 * Processes previous objective values and reference solutions for visualization components
 * 
 * @param state The current NIMBUS response state
 * @param problem The problem containing objective definitions
 * @returns Array of arrays with previous objective values
 */
export function processPreviousObjectiveValues(
    state: any,
    problem: ProblemInfo | null
): number[][] {
    if (!problem || !state) {
        return [];
    }
    
    const result: number[][] = [];
    
    // Add previous_objectives if it exists
    if (state.previous_objectives) {
        result.push(convertObjectiveToArray(state.previous_objectives, problem));
    }
    
    // Add reference_solution_1 if it exists
    if (state.reference_solution_1) {
        result.push(convertObjectiveToArray(state.reference_solution_1, problem));
    }
    
    // Add reference_solution_2 if it exists
    if (state.reference_solution_2) {
        result.push(convertObjectiveToArray(state.reference_solution_2, problem));
    }
    
    return result;
}
/**
 * Validates if iteration is allowed based on preferences and objectives
 * Iteration requires at least one preference to be better and one to be worse
 * @param problem The current problem
 * @param preferenceValues Current preference values
 * @param objectiveValues Current objective values
 * @param precision Precision threshold for floating point comparisons
 * @returns Boolean indicating if iteration is allowed
 */
export function validateIterationAllowed(
    problem: ProblemInfo | null,
    preferenceValues: number[],
    objectiveValues: Record<string, number>,
    precision: number = 0.001
): boolean {
    if (!problem || preferenceValues.length === 0 || Object.keys(objectiveValues).length === 0) {
        return false;
    }

    let hasImprovement = false;
    let hasWorsening = false;

    for (let i = 0; i < problem.objectives.length; i++) {
        const objective = problem.objectives[i];
        const preferenceValue = preferenceValues[i];
        const currentValue = objectiveValues[objective.symbol];

        if (preferenceValue === undefined || currentValue === undefined) {
            continue;
        }

        // Check if values are approximately equal (within precision)
        const isEqual = Math.abs(preferenceValue - currentValue) < precision;
        
        if (isEqual) {
            // Values are approximately equal - "keep constant"
            continue;
        }

        // Determine if preference is better than current value, considering optimization direction
        const isPreferenceBetter = objective.maximize ? 
            (preferenceValue > currentValue) : 
            (preferenceValue < currentValue);

        // Update improvement or worsening flags based on comparison
        if (isPreferenceBetter) {
            hasImprovement = true;
        } else {
            hasWorsening = true;
        }
    }

    // Need both improvement and worsening for valid NIMBUS classification
    return hasImprovement && hasWorsening;
}

/**
 * Generic API call function for NIMBUS operations
 * @param type The operation type (initialize, iterate, intermediate, save, choose, get_maps)
 * @param data The data to send in the request body
 * @returns Promise with the API response
 */
/**
 * Updates solution names from saved solutions
 * 
 * @param savedSolutions - Array of saved solutions with names
 * @param targetSolutions - Array of solutions to update with names
 * @returns The updated target solutions array
 */
export function updateSolutionNames(
    savedSolutions: Solution[],
    targetSolutions: Solution[]
): Solution[] {
    if (!savedSolutions || !targetSolutions) {
        return targetSolutions;
    }

    // Create a copy of the target solutions to avoid mutating the original
    const updatedSolutions = [...targetSolutions];

    // Update names for solutions that exist in saved solutions
    for (let solution of updatedSolutions) {
        const savedIndex = savedSolutions.findIndex(
            (saved) =>
                saved.state_id === solution.state_id && saved.solution_index === solution.solution_index
        );

        if (savedIndex !== -1) {
            // Solution exists in saved_solutions, update the name
            solution.name = savedSolutions[savedIndex].name;
        }
    }

    return updatedSolutions;
}

export function computeTradeoffs(
    lagrange_multipliers: Record<string, number> | null | undefined,
    solution: Solution,
    problem: ProblemInfo,
): Record<string, Record<string, number>> {
    const objective_values = mapSolutionsToObjectiveValues([solution], problem);

    if (!lagrange_multipliers || lagrange_multipliers.length === 0) {
        return {};
    }
  
    const nObjectives = problem.objectives.length;

    const lambdas: number[] = problem.objectives.map((obj) => {
        const value = lagrange_multipliers[obj.symbol];
        return Array.isArray(value) ? value[0] : value || 0;
    });

    const partialTradeOffs: Record<string, Record<string, number>> = {}; 
    const wInv: number[] = lambdas.map((value) => 1 / value); 

    problem.objectives.forEach((obj_i, i) => {
        partialTradeOffs[obj_i.symbol] = {};
        problem.objectives.forEach((obj_j) => {
            partialTradeOffs[obj_i.symbol][obj_j.symbol] = 1; // Initialize with 1
        });
        problem.objectives.forEach((obj_j, j) => {
            if (obj_i.symbol !== obj_j.symbol) {
                const lambda_i = lambdas[i];
                const lambda_j = lambdas[j];
                const tradeoff = -lambda_j / lambda_i;
                partialTradeOffs[obj_i.symbol][obj_j.symbol] = tradeoff;
            }
        });
    });    
    return partialTradeOffs;
}

export async function callNimbusAPI<T>(
    type: string,
    data: Record<string, any>,
    timeout = 10000 // 10s default
): Promise<T | null> {
    isLoading.set(true);
    errorMessage.set(null);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(`/interactive_methods/XNIMBUS/?type=${type}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        const result = await response.json();

        if (!response.ok || !result.success) {
            const errorMsg = result.error || `HTTP error! Status: ${response.status}`;
            throw new Error(errorMsg);
        }

        return result.data as T;
    } catch (error) {
        let errorMsg: string;
        if (error instanceof Error) {
            if (error.name === 'AbortError') {
                errorMsg = 'The request timed out. Please try again.';
            } else {
                errorMsg = error.message;
            }
        } else {
            errorMsg = 'An unknown error occurred';
        }
        errorMessage.set(errorMsg);
        console.error(`Error calling NIMBUS ${type} API:`, errorMsg);
        return null;
    } finally {
        isLoading.set(false);
    }
}
/**
 * 
 * @param multipliers 
 * @returns Compute the minimum and maximium lagrange multipliers for each objective
 */
export function getRangeMultipliers(multipliers: Array<Record<string, number>> | null | undefined): Record<string, { min: number; max: number }> {
    if (!multipliers || multipliers.length === 0) {
        return {};
    }
    // For each column (objective), find min and max across all solutions (rows)
    const objectiveKeys = Object.keys(multipliers[0]);
    const minMax: Record<string, { min: number; max: number }> = {};
    
    objectiveKeys.forEach((key) => {
        let min = Infinity;
        let max = -Infinity;
        multipliers.forEach((solution) => {
            const value = solution[key];
            if (value !== undefined) {
                if (value < min) min = value;
                if (value > max) max = value;
            }
        }

    );

        minMax[key] = { min, max };
    });
    
    return minMax;
}

/*Compute the minimum and maximum tradeoffs per objective (column)*/
export function getRangeTradeoffs(tradeoffs: number[][] | null | undefined) : { min: number; max: number }[] {
    if (!tradeoffs || tradeoffs.length === 0) {
        return [{ min: 0, max: 0 }];
    }
    
    const nObjectives = tradeoffs.length;
    const minMax: { min: number; max: number }[] = [];
    for (let j = 0; j < nObjectives; j++) {
        let min = Infinity;
        let max = -Infinity;
        for (let i = 0; i < nObjectives; i++) {
            const value = tradeoffs[i][j];
            if (value < min) min = value;
            if (value > max) max = value;
        }
        minMax.push({ min, max });
    }
    return minMax;
}

export function normalizeMultipliers(
    multipliers: Array<Record<string, number>> | null | undefined
): Array<Record<string, number>> {
    if (!multipliers || multipliers.length === 0) {
        return [];
    }
    
    const objectiveKeys = Object.keys(multipliers[0]);
    const normalizedMultipliers: Array<Record<string, number>> = [];
    const minMax = getRangeMultipliers(multipliers);
    
    multipliers.forEach((solution) => {
        const normalizedSolution: Record<string, number> = {};
        objectiveKeys.forEach((key) => {
            const value = solution[key];
            const range = minMax[key].max - minMax[key].min;
            if (range === 0) {
                normalizedSolution[key] = 0; // or some default value when no variation
            }
            else {
                normalizedSolution[key] = (value - minMax[key].min) / range;
            }
        });
        normalizedMultipliers.push(normalizedSolution);
    });
    
    return normalizedMultipliers;
}

export function normalizeTradeoffs(
    tradeoffs: number[][] | null | undefined
): number[][] {
    if (!tradeoffs || tradeoffs.length === 0) {
        return [];
    }
    
    const nObjectives = tradeoffs.length;
    const normalizedTradeoffs: number[][] = [];
    const minMax = getRangeTradeoffs(tradeoffs);
    
    for (let i = 0; i < nObjectives; i++) {
        const normalizedRow: number[] = [];
        for (let j = 0; j < nObjectives; j++) {
            const value = tradeoffs[i][j];
            const range = minMax[j].max - minMax[j].min;
            if (range === 0) {
                normalizedRow.push(0); // or some default value when no variation
            }
            else {
                normalizedRow.push((value - minMax[j].min) / range);
            }
        }
        normalizedTradeoffs.push(normalizedRow);
    }
    
    return normalizedTradeoffs;
}


/*export function compute_tradeoffs(
    solution: Solution,
    problem: ProblemInfo,
){
  const objective_values = mapSolutionsToObjectiveValues([solution], problem);
  const lagrange_multipliers = solution.lagrange_multipliers || null;



  // Equivalent of np.ones((n_objectives, n_objectives))
  const partialTradeOffs: number [][] = Array.from({ length: nObjectives }, () =>
    Array(nObjectives).fill(1)
  );

  // Equivalent of w_inv = 1 / np.array(w)
  // (Note: this is currently unused, just like in your Python code.)
  const wInv: number[] = w.map((value) => 1 / value);

  for (let i = 0; i < nObjectives; i++) {
    const lambda_i = lambdas[i];
    for (let j = 0; j < nObjectives; j++) {
      if (i !== j) {
        const lambda_j = lambdas[j];
        // tradeoff = -(lambda_j) / (lambda_i)
        const tradeoff = -lambda_j / lambda_i;
        partialTradeOffs[i][j] = tradeoff;
      }
    }
  }

  return partialTradeOffs;
}*/