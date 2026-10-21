/**
 * Handlers for the JINA (interactive two-stage robustness) method.
 *
 * Return values are typed via the local `IterateState`/`WishlistState` interfaces in `./types`
 * rather than the generated response types directly — see the comment at the top of `./types.ts`.
 * The generated client *functions* are still used for the actual network calls.
 */

import {
	analysisMethodDistrictHeatingRobustAnalysisPost,
	combinedScenarioAnalysisMethodDistrictHeatingRobustCombinedScenarioAnalysisPost,
	getOrInitializeMethodDistrictHeatingRobustGetOrInitializeGet,
	iterateMethodDistrictHeatingRobustIteratePost,
	sessionTreeMethodDistrictHeatingRobustSessionTreeGet,
	strategicDesignsMethodDistrictHeatingRobustStrategicDesignsGet,
	wishlistAddMethodDistrictHeatingRobustWishlistAddPost,
	wishlistRemoveMethodDistrictHeatingRobustWishlistRemovePost
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type {
	DistrictHeatingRobustAnalysisRequest,
	DistrictHeatingRobustCombinedScenarioRequest,
	DistrictHeatingRobustIterateRequest,
	DistrictHeatingRobustWishlistUpdateRequest
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type {
	AnalysisResult,
	CombinedScenarioResult,
	IterateState,
	SessionTreeEntry,
	StrategicDesignsResult,
	WishlistState
} from './types';

// FastAPI's HTTPException (raised e.g. when a problem has no attached scenario model — see
// `JinaScenarioError` in the backend) returns `{ detail: "<specific reason>" }`. Surfacing that
// instead of a generic message is the difference between a DM knowing *why* a problem doesn't
// work with this method and just seeing "failed to load".
/** Turn a non-200 response into something a DM can act on.
 *
 * Only FastAPI's plain-string `HTTPException.detail` used to be understood, so three common
 * failures all collapsed into the bare fallback text and hid their own cause: request-validation
 * errors (where `detail` is a list of objects, not a string), failures raised by the SvelteKit
 * `/api` proxy itself rather than by the backend (upstream timeout, connection refused — those
 * use `message`, not `detail`), and non-JSON error bodies. The HTTP status is appended whenever
 * the body carried no usable text, so "it failed" at least becomes "it failed with a 504".
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

		// FastAPI request-validation errors: a list of { loc, msg, type }.
		if (Array.isArray(detail) && detail.length > 0) {
			const parts = detail.map((d) => {
				const item = d as { loc?: unknown; msg?: unknown };
				const loc = Array.isArray(item.loc) ? item.loc.join('.') : '';
				const msg = typeof item.msg === 'string' ? item.msg : JSON.stringify(d);
				return loc ? `${loc}: ${msg}` : msg;
			});
			return withStatus(`${fallback} ${parts.join('; ')}`);
		}

		// SvelteKit's error shape, i.e. the proxy failed before the backend ever answered.
		const message = (data as { message?: unknown }).message;
		if (typeof message === 'string' && message.length > 0) {
			return withStatus(`${fallback} ${message}`);
		}
	}

	return withStatus(fallback);
}

export async function getOrInitialize(problemId: number, sessionId: number | null): Promise<IterateState> {
	const res = await getOrInitializeMethodDistrictHeatingRobustGetOrInitializeGet({
		problem_id: problemId,
		...(sessionId != null ? { session_id: sessionId } : {})
	});
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to fetch the current state.'));
	return res.data as IterateState;
}

export async function runIteration(body: DistrictHeatingRobustIterateRequest): Promise<IterateState> {
	const res = await iterateMethodDistrictHeatingRobustIteratePost(body);
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to run the iteration.'));
	return res.data as IterateState;
}

export async function wishlistAdd(
	body: DistrictHeatingRobustWishlistUpdateRequest
): Promise<WishlistState> {
	const res = await wishlistAddMethodDistrictHeatingRobustWishlistAddPost(body);
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to add to the wish list.'));
	return res.data as WishlistState;
}

export async function wishlistRemove(
	body: DistrictHeatingRobustWishlistUpdateRequest
): Promise<WishlistState> {
	const res = await wishlistRemoveMethodDistrictHeatingRobustWishlistRemovePost(body);
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to remove from the wish list.'));
	return res.data as WishlistState;
}

export async function getAnalysis(body: DistrictHeatingRobustAnalysisRequest): Promise<AnalysisResult> {
	const res = await analysisMethodDistrictHeatingRobustAnalysisPost(body);
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to fetch the analysis.'));
	return res.data as unknown as AnalysisResult;
}

export async function getSessionTree(problemId: number, sessionId: number | null): Promise<SessionTreeEntry[]> {
	const res = await sessionTreeMethodDistrictHeatingRobustSessionTreeGet({
		problem_id: problemId,
		...(sessionId != null ? { session_id: sessionId } : {})
	});
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to fetch the session history.'));
	return res.data as unknown as SessionTreeEntry[];
}

export async function getStrategicDesigns(problemId: number, sessionId: number | null): Promise<StrategicDesignsResult> {
	const res = await strategicDesignsMethodDistrictHeatingRobustStrategicDesignsGet({
		problem_id: problemId,
		...(sessionId != null ? { session_id: sessionId } : {})
	});
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to fetch the strategic designs.'));
	return res.data as unknown as StrategicDesignsResult;
}

export async function getCombinedScenarioAnalysis(
	body: DistrictHeatingRobustCombinedScenarioRequest
): Promise<CombinedScenarioResult> {
	const res = await combinedScenarioAnalysisMethodDistrictHeatingRobustCombinedScenarioAnalysisPost(body);
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to run the compound-disruption analysis.'));
	return res.data as unknown as CombinedScenarioResult;
}
