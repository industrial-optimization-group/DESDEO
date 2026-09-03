/**
 * Handlers for the JINA (interactive single-scenario) method.
 *
 * Return values are typed via the local `IterateState`/`WishlistState` interfaces in `./types`
 * rather than the generated `DistrictHeatingIterateResponse`/`DistrictHeatingWishlistResponse`
 * directly — see the comment at the top of `./types.ts` for why. The generated client
 * *functions* are still used for the actual network calls.
 */

import {
	analysisMethodDistrictHeatingSystemAnalysisPost,
	getOrInitializeMethodDistrictHeatingSystemGetOrInitializeGet,
	iterateMethodDistrictHeatingSystemIteratePost,
	sessionTreeMethodDistrictHeatingSystemSessionTreeGet,
	strategicDesignsMethodDistrictHeatingSystemStrategicDesignsGet,
	wishlistAddMethodDistrictHeatingSystemWishlistAddPost,
	wishlistRemoveMethodDistrictHeatingSystemWishlistRemovePost
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type {
	DistrictHeatingAnalysisRequest,
	DistrictHeatingIterateRequest,
	DistrictHeatingWishlistUpdateRequest
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type {
	AnalysisResult,
	IterateState,
	SessionTreeEntry,
	StrategicDesignsResult,
	WishlistState
} from './types';

// FastAPI's HTTPException (raised e.g. when a problem has no attached pool metadata — see
// `JinaPoolError` in the backend) returns `{ detail: "<specific reason>" }`. Surfacing that
// instead of a generic message is the difference between a DM knowing *why* a problem doesn't
// work with this method and just seeing "failed to load".
function errorMessage(res: { data?: unknown }, fallback: string): string {
	const detail = (res.data as { detail?: unknown } | undefined)?.detail;
	return typeof detail === 'string' && detail.length > 0 ? detail : fallback;
}

export async function getOrInitialize(problemId: number, sessionId: number | null): Promise<IterateState> {
	const res = await getOrInitializeMethodDistrictHeatingSystemGetOrInitializeGet({
		problem_id: problemId,
		...(sessionId != null ? { session_id: sessionId } : {})
	});
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to fetch the current state.'));
	return res.data as IterateState;
}

export async function runIteration(body: DistrictHeatingIterateRequest): Promise<IterateState> {
	const res = await iterateMethodDistrictHeatingSystemIteratePost(body);
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to run the iteration.'));
	return res.data as IterateState;
}

export async function wishlistAdd(
	body: DistrictHeatingWishlistUpdateRequest
): Promise<WishlistState> {
	const res = await wishlistAddMethodDistrictHeatingSystemWishlistAddPost(body);
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to add to the wish list.'));
	return res.data as WishlistState;
}

export async function wishlistRemove(
	body: DistrictHeatingWishlistUpdateRequest
): Promise<WishlistState> {
	const res = await wishlistRemoveMethodDistrictHeatingSystemWishlistRemovePost(body);
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to remove from the wish list.'));
	return res.data as WishlistState;
}

export async function getAnalysis(body: DistrictHeatingAnalysisRequest): Promise<AnalysisResult> {
	const res = await analysisMethodDistrictHeatingSystemAnalysisPost(body);
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to fetch the analysis.'));
	return res.data as unknown as AnalysisResult;
}

export async function getSessionTree(problemId: number, sessionId: number | null): Promise<SessionTreeEntry[]> {
	const res = await sessionTreeMethodDistrictHeatingSystemSessionTreeGet({
		problem_id: problemId,
		...(sessionId != null ? { session_id: sessionId } : {})
	});
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to fetch the session history.'));
	return res.data as unknown as SessionTreeEntry[];
}

export async function getStrategicDesigns(problemId: number): Promise<StrategicDesignsResult> {
	const res = await strategicDesignsMethodDistrictHeatingSystemStrategicDesignsGet({ problem_id: problemId });
	if (res.status !== 200) throw new Error(errorMessage(res, 'Failed to fetch the strategic designs.'));
	return res.data as unknown as StrategicDesignsResult;
}
