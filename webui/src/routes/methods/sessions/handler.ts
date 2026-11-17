import type {
	CreateSessionRequest,
	InteractiveSessionBase
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type {
	createNewSessionSessionNewPostResponse,
	deleteSessionSessionSessionIdDeleteResponse,
	getAllSessionsSessionGetAllGetResponse
} from '$lib/gen/endpoints/DESDEOFastAPI';

import {
	activateSessionSessionActivatePost,
	createNewSessionSessionNewPost,
	deleteSessionSessionSessionIdDelete,
	getAllSessionsSessionGetAllGet
} from '$lib/gen/endpoints/DESDEOFastAPI';

export async function fetch_sessions(): Promise<InteractiveSessionBase[] | null> {
	const response: getAllSessionsSessionGetAllGetResponse = await getAllSessionsSessionGetAllGet();

	if (response.status !== 200) {
		console.error('fetch_sessions failed.', response.status);
		return null;
	}

	return response.data;
}

export async function create_session(
	info: string | null,
	targetUserId?: number | null
): Promise<InteractiveSessionBase | null> {
	const payload: CreateSessionRequest = { info: info ?? null };
	const response: createNewSessionSessionNewPostResponse = await createNewSessionSessionNewPost(
		payload,
		targetUserId != null ? { target_user_id: targetUserId } : undefined
	);

	if (response.status !== 200) {
		console.error('create_session failed.', response.status);
		return null;
	}

	return response.data;
}

/** Makes one of the user's own sessions the active one in the backend, or clears it with null. */
export async function activate_session(session_id: number | null): Promise<boolean> {
	const response = await activateSessionSessionActivatePost({ session_id });

	if (response.status !== 200) {
		console.error('activate_session failed.', response.status);
		return false;
	}
	return true;
}

export async function delete_session(session_id: number): Promise<boolean> {
	const response = await deleteSessionSessionSessionIdDelete(session_id);

	if (response.status < 200 || response.status >= 300) {
		console.error('delete_session failed.', response.status);
		return false;
	}
	return true;
}
