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
