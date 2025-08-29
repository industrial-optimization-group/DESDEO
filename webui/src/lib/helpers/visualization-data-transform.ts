import type { components } from '$lib/api/client-types';

type ProblemInfo = components['schemas']['ProblemInfo'];

/**
 * Transform 2D array of objective values into visualization-ready format
 * 
 * @param solutions_objective_values - Array of objective value arrays for each solution
 * @param problem - Problem definition with objective symbols
 * @returns Array of objects with named objective properties, symbol as name
 */
export function transformObjectiveData(
    solutions_objective_values: number[][],
    problem: ProblemInfo | null
): Array<{ [key: string]: number }> {
    if (!solutions_objective_values.length || !problem?.objectives) return [];

    return solutions_objective_values.map((solution) => {
        const dataPoint: { [key: string]: number } = {};
        solution.forEach((value, objIndex) => {
            if (problem.objectives[objIndex]) {
                dataPoint[problem.objectives[objIndex].symbol] = value;
            }
        });
        return dataPoint;
    });
}

/**
 * Transform 2D array of decision values into visualization-ready format
 * 
 * @param solutions_decision_values - Array of decision variable arrays for each solution
 * @param problem - Problem definition with variable symbols
 * @returns Array of objects with named variable properties, symbol as name
 */
export function transformDecisionData(
    solutions_decision_values: number[][],
    problem: ProblemInfo | null
): Array<{ [key: string]: number }> {
    if (!solutions_decision_values.length || !problem?.variables) return [];

    return solutions_decision_values.map((solution) => {
        const dataPoint: { [key: string]: number } = {};
        solution.forEach((value, varIndex) => {
            if (problem.variables && problem.variables[varIndex]) {
                dataPoint[problem.variables[varIndex].symbol] = value;
            } else {
                dataPoint[`var_${varIndex}`] = value;
            }
        });
        return dataPoint;
    });
}

/**
 * Create dimensions array for visualization components from problem objectives
 * 
 * @param problem - Problem definition with objectives
 * @returns Array of dimension definitions with bounds and direction
 */
export function createObjectiveDimensions(problem: ProblemInfo | null) {
    if (!problem?.objectives) return [];

    return problem.objectives.map((obj) => ({
        symbol: obj.symbol,
        min: typeof obj.nadir === 'number' ? obj.nadir : undefined,
        max: typeof obj.ideal === 'number' ? obj.ideal : undefined,
        direction: obj.maximize ? ('max' as const) : ('min' as const)
    }));
}

/**
 * Create dimensions array for decision variables
 * 
 * @param problem - Problem definition with variables
 * @returns Array of dimension definitions with bounds
 */
export function createDecisionDimensions(problem: ProblemInfo | null) {
    if (!problem?.variables) return [];

    return problem.variables.map((variable) => ({
        symbol: variable.symbol,
        min: typeof variable.lowerbound === 'number' ? variable.lowerbound : undefined,
        max: typeof variable.upperbound === 'number' ? variable.upperbound : undefined
    }));
}