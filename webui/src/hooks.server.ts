import type { HandleFetch } from '@sveltejs/kit';
import { refreshAccessTokenRefreshPost } from '$lib/gen/endpoints/DESDEOFastAPI';
import { dev } from '$app/environment';

// const API = process.env.API_BASE_URL ?? '/';

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
	// Buffer the body upfront so we have concrete data instead of a
	// ReadableStream. This avoids Node/undici "expected non-null body source"
	// errors when reconstructing or cloning Requests with streaming bodies.
	const hasBody = !['GET', 'HEAD'].includes(request.method);
	const bodyBuffer = hasBody ? await request.arrayBuffer() : undefined;
	const originalHeaders = Object.fromEntries(request.headers.entries());

	// Build a fresh Request with the buffered body and a given cookie header.
	// ArrayBuffers are reusable (unlike ReadableStreams), so this can be
	// called multiple times for retries.
	const makeRequest = (cookieHeader: string) =>
		new Request(request.url, {
			method: request.method,
			headers: new Headers({
				...originalHeaders,
				cookie: cookieHeader
			}),
			body: bodyBuffer,
			// @ts-expect-error — duplex is required for streaming bodies in Node 18+
			duplex: 'half'
		});

	// Forward access_token cookie to all API requests
	const accessToken = event.cookies.get('access_token');
	const originalCookie = originalHeaders['cookie'] ?? '';

	let res = await fetch(makeRequest(accessToken ? `access_token=${accessToken}` : originalCookie));

	// No auth errors, pass through.
	if (res.status !== 401) return res;

	// 401 — try refreshing the access token ONCE, then retry.
	const refreshToken = event.cookies.get('refresh_token');
	if (!refreshToken) return res;

	try {
		const response_with_new_cookies = await refreshAccessTokenRefreshPost({
			fetchImpl: fetch,
			headers: {
				cookie: `refresh_token=${refreshToken}`
			}
		} as RequestInit);

		if (response_with_new_cookies.status != 200 || !response_with_new_cookies.data?.access_token)
			return res;

		// Update the access_token cookie for the browser.
		event.cookies.set('access_token', response_with_new_cookies.data.access_token, {
			httpOnly: true,
			secure: !dev,
			sameSite: 'lax',
			path: '/'
		});

		const cookieHeader = event.cookies
			.getAll()
			.map(({ name, value }) => `${name}=${value}`)
			.join('; ');

		// Retry with the new access token — reuses the buffered body.
		res = await fetch(makeRequest(cookieHeader));

		return res;
	} catch (err) {
		console.error('[handleFetch] token refresh failed:', err);
		console.error('[handleFetch] cause:', (err as any)?.cause);
		return res; // degrade to 401, not 500
	}
};
