/**
 * GNIMBUS Type Definitions
 *
 * This module contains type definitions for the GNIMBUS interactive method,
 * including component props, state interfaces, and API response types.
 *
 * @author Stina Palomäki <palomakistina@gmail.com>
 * @created October 2025
 */

import type { components } from '$lib/api/client-types';

export type ProblemInfo = components['schemas']['ProblemInfo'];
// export type Solution = components['schemas']['SolutionReference'];
export type Solution = {
            /**
             * Name
             * @description Optional name to help identify the solution if, e.g., saved.
             */
            name?: string | null;
            /**
             * Solution Index
             * @description The index of the referenced solution, if multiple solutions exist in the reference state.
             */
            solution_index?: number | null;
            /** @description The reference state with the solution information. */
            /** Objective Values */
            readonly objective_values: {
                [key: string]: number;
            } | null;
            /** Variable Values */
            iteration_number?: number | null;
            /** State Id */
            readonly state_id: number;
            /** Num Solutions */
            readonly num_solutions: number;
        };
export type AllIterations = components['schemas']['GNIMBUSAllIterationsResponse'];
export type Group = components['schemas']['GroupPublic'];
export type Response = components['schemas']['FullIteration'];

export type Step = 'optimization' | 'voting' | 'finish';
export type PeriodKey = 'period1' | 'period2' | 'period3';

export interface MapState {
	mapOptions: Record<PeriodKey, Record<string, any>>;
	yearlist: string[];
	selectedPeriod: PeriodKey;
	geoJSON: object | undefined;
	mapName: string | undefined;
	mapDescription: string | undefined;
}

export interface TableData {
	state_id: number;
	solution_index: number |null;
	name: null;
	objective_values: {
		[key: string]: number;
	} | null;
	iteration_number?: number;
}
