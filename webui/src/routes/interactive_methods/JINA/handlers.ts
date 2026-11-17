/**
 * JINA API client-side handlers.
 *
 * Handlers return the response data, or null after putting the error in `errorMessage`.
 */

import {
	getScenarioModelsMethodJinaScenarioModelsGet,
	getOrInitializeMethodJinaGetOrInitializePost,
	setupMethodJinaSetupPost,
	iterateMethodJinaIteratePost,
	importDesignsMethodJinaImportPost,
	evaluateMethodJinaEvaluatePost,
	selectDesignsMethodJinaSelectPost,
	antifragilityAnalysisMethodJinaAntifragilityPost,
	getDesignsMethodJinaDesignsGet
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type {
	JinaSetupRequest,
	JinaIterateRequest,
	JinaImportRequest,
	JinaEvaluateRequest,
	JinaSelectRequest,
	JinaAntifragilityRequest,
	JinaAntifragilityResponse,
	JinaDesignInfo,
	JinaGetOrInitializeResponse,
	JinaScenarioModelInfo,
	JinaStateResponse
} from '$lib/gen/endpoints/DESDEOFastAPI';
import { errorDetail } from '$lib/components/custom/jina/labels';
import { errorMessage, isLoading } from '../../../stores/uiState';

/** Send a request; return its data, or the error message of a failed request. */
async function send<T>(
	request: () => Promise<{ status: number; data: unknown }>
): Promise<{ data: T | null; error: string | null }> {
	try {
		const response = await request();
		if (response.status !== 200) {
			return { data: null, error: errorDetail(response.status, response.data) };
		}
		return { data: response.data as T, error: null };
	} catch (error) {
		return { data: null, error: error instanceof Error ? error.message : 'Unknown error' };
	}
}

/** A user-started call clears the previous error and shows loading; a background call does neither. */
async function call<T>(
	request: () => Promise<{ status: number; data: unknown }>,
	background = false
): Promise<T | null> {
	if (!background) {
		isLoading.set(true);
		errorMessage.set(null);
	}
	const { data, error } = await send<T>(request);
	if (!background) isLoading.set(false);
	if (error) errorMessage.set(error);
	return data;
}

/** Load the scenario models and the latest setup together, under one loading indicator. */
export async function loadSession(problem_id: number) {
	isLoading.set(true);
	errorMessage.set(null);
	const [models, restored] = await Promise.all([
		call<JinaScenarioModelInfo[]>(
			() => getScenarioModelsMethodJinaScenarioModelsGet({ problem_id }),
			true
		),
		call<JinaGetOrInitializeResponse>(
			() => getOrInitializeMethodJinaGetOrInitializePost({ problem_id }),
			true
		)
	]);
	isLoading.set(false);
	return { models, restored };
}

/** Start a setup; the error is returned rather than shown, for the setup dialog to show it. */
export const startSetup = (request: JinaSetupRequest) =>
	send<JinaStateResponse>(() => setupMethodJinaSetupPost(request));

export const iterate = (request: JinaIterateRequest) =>
	call<JinaStateResponse>(() => iterateMethodJinaIteratePost(request));

export const importDesigns = (request: JinaImportRequest) =>
	call<JinaStateResponse>(() => importDesignsMethodJinaImportPost(request));

export const evaluate = (request: JinaEvaluateRequest) =>
	call<JinaStateResponse>(() => evaluateMethodJinaEvaluatePost(request));

export const select = (request: JinaSelectRequest) =>
	call<JinaStateResponse>(() => selectDesignsMethodJinaSelectPost(request));

export const analyseAntifragility = (request: JinaAntifragilityRequest) =>
	call<JinaAntifragilityResponse>(() => antifragilityAnalysisMethodJinaAntifragilityPost(request));

export const fetchDesigns = (problem_id: number, setup_state_id: number) =>
	call<JinaDesignInfo[]>(
		() => getDesignsMethodJinaDesignsGet({ problem_id, setup_state_id }),
		true
	);
