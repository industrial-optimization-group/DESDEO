import type { CreateSessionRequest, InteractiveSessionBase } from '$lib/gen/models';
import type {
	createNewSessionSessionNewPostResponse,
	deleteSessionSessionSessionIdDeleteResponse,
	getAllSessionsSessionGetAllGetResponse
} from '$lib/gen/endpoints/DESDEOFastAPI';

import {
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

export async function create_session(info: string | null): Promise<InteractiveSessionBase | null> {
	const payload: CreateSessionRequest = { info: info ?? null };
	const response: createNewSessionSessionNewPostResponse = await createNewSessionSessionNewPost(payload);

	if (response.status !== 200) {
		console.error('create_session failed.', response.status);
		return null;
	}

	return response.data;
}

export async function delete_session(session_id: number): Promise<boolean> {
	const response: deleteSessionSessionSessionIdDeleteResponse =
		await deleteSessionSessionSessionIdDelete(session_id);

	if (response.status !== 204) {
		console.error('delete_session failed.', response.status);
		return false;
	}

	return true;
}
