/**
 * Handlers for the JINA (interactive combined multi-scenario) method.
 *
 * Thin wrappers over the generated client that turn a non-200 into a message a decision maker can
 * act on, mirroring the multi-scenario method's handlers. This method has only two calls: fetch
 * the (objective, scenario) grid, and solve one ASF against a full set of aspiration levels.
 */

import {
	analysisMethodDistrictHeatingCombinedAnalysisPost,
	getOrInitializeMethodDistrictHeatingCombinedGetOrInitializeGet,
	initializeMethodDistrictHeatingCombinedInitializePost,
	iterateMethodDistrictHeatingCombinedIteratePost,
	sessionTreeMethodDistrictHeatingCombinedSessionTreeGet,
	wishlistAddMethodDistrictHeatingCombinedWishlistAddPost,
	wishlistRemoveMethodDistrictHeatingCombinedWishlistRemovePost
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type {
	DistrictHeatingCombinedAnalysisRequest,
	DistrictHeatingCombinedIterateRequest,
	DistrictHeatingCombinedWishlistUpdateRequest
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type {
	CombinedAnalysisResult,
	CombinedGrid,
	CombinedResult,
	CombinedSessionTreeEntry,
	CombinedWishlistResult
} from './types';

/**
 * Turn a non-200 response into something a DM can act on. Same shapes as the multi-scenario
 * method's: FastAPI's plain-string `detail`, its list-of-objects validation errors, and the
 * SvelteKit `/api` proxy's own `message` when the backend never answered at all.
 */
function errorMessage(res: { status?: number; data?: unknown }, fallback: string): string {
	const withStatus = (text: string) => (res.status ? `${text} (HTTP ${res.status})` : text);
	const data = res.data;

	if (typeof data === 'string' && data.trim().length > 0) {
		return withStatus(`${fallback} ${data.trim().slice(0, 300)}`);
	}

	if (typeof data === 'object' && data !== null) {
		const detail = (data as { detail?: unknown }).detail;
		if (typeof detail === 'string' && detail.length > 0) return detail;

		if (Array.isArray(detail) && detail.length > 0) {
			const parts = detail.map((d) => {
				const item = d as { loc?: unknown; msg?: unknown };
				const loc = Array.isArray(item.loc) ? item.loc.join('.') : '';
				const msg = typeof item.msg === 'string' ? item.msg : JSON.stringify(d);
				return loc ? `${loc}: ${msg}` : msg;
			});
			return withStatus(`${fallback} ${parts.join('; ')}`);
		}

		const message = (data as { message?: unknown }).message;
		if (typeof message === 'string' && message.length > 0) {
			return withStatus(`${fallback} ${message}`);
		}
	}

	return withStatus(fallback);
}

export async function initializeCombined(
	problemId: number,
	sessionId: number | null
): Promise<CombinedGrid> {
	const res = await initializeMethodDistrictHeatingCombinedInitializePost({
		problem_id: problemId,
		...(sessionId != null ? { session_id: sessionId } : {})
	});
	if (res.status !== 200) {
		throw new Error(errorMessage(res, 'Failed to load the objective-scenario grid.'));
	}
	return res.data as unknown as CombinedGrid;
}

export async function runCombinedIteration(
	body: DistrictHeatingCombinedIterateRequest
): Promise<CombinedResult> {
	const res = await iterateMethodDistrictHeatingCombinedIteratePost(body);
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to run the iteration.'));
	return res.data as unknown as CombinedResult;
}

export async function getOrInitializeCombined(
	problemId: number,
	sessionId: number | null
): Promise<CombinedResult> {
	const res = await getOrInitializeMethodDistrictHeatingCombinedGetOrInitializeGet({
		problem_id: problemId,
		...(sessionId != null ? { session_id: sessionId } : {})
	});
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to fetch the current state.'));
	return res.data as unknown as CombinedResult;
}

export async function getCombinedSessionTree(
	problemId: number,
	sessionId: number | null
): Promise<CombinedSessionTreeEntry[]> {
	const res = await sessionTreeMethodDistrictHeatingCombinedSessionTreeGet({
		problem_id: problemId,
		...(sessionId != null ? { session_id: sessionId } : {})
	});
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to fetch the session history.'));
	return (res.data as unknown as { entries: CombinedSessionTreeEntry[] }).entries ?? [];
}

export async function combinedWishlistAdd(
	body: DistrictHeatingCombinedWishlistUpdateRequest
): Promise<CombinedWishlistResult> {
	const res = await wishlistAddMethodDistrictHeatingCombinedWishlistAddPost(body);
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to add to the wish list.'));
	return res.data as unknown as CombinedWishlistResult;
}

export async function combinedWishlistRemove(
	body: DistrictHeatingCombinedWishlistUpdateRequest
): Promise<CombinedWishlistResult> {
	const res = await wishlistRemoveMethodDistrictHeatingCombinedWishlistRemovePost(body);
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to remove from the wish list.'));
	return res.data as unknown as CombinedWishlistResult;
}

export async function getCombinedAnalysis(
	body: DistrictHeatingCombinedAnalysisRequest
): Promise<CombinedAnalysisResult> {
	const res = await analysisMethodDistrictHeatingCombinedAnalysisPost(body);
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to run the analysis.'));
	return res.data as unknown as CombinedAnalysisResult;
}
