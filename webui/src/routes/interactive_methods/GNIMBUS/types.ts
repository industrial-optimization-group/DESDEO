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
export type Solution = components['schemas']['SolutionReference'];
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
	variable_values: {
		[key: string]: number | boolean;
	} | null;
	iteration_number?: number;
}
