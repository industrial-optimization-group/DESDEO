import type { HandleFetch } from '@sveltejs/kit';
import { refreshAccessTokenRefreshPost } from '$lib/gen/endpoints/DESDEOFastAPI';
import { dev } from '$app/environment';

// const API = process.env.API_BASE_URL ?? '/';

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
	try {
		// Forward access_token cookie to all API requests
		const accessToken = event.cookies.get('access_token');
		if (accessToken) {
			request = new Request(request, {
				headers: new Headers({
					...Object.fromEntries(request.headers.entries()),
					cookie: `access_token=${accessToken}`
				}),
				// @ts-expect-error — duplex is required for streaming bodies in Node 18+
				duplex: 'half'
			});
		}

		const originalRequest = request.clone();
		let res = await fetch(request);

		// No auth errors, assuming either ok or other errors, pass the response back.
		if (res.status !== 401) return res;

		// 401, try refreshing the access token ONCE and then try again with the original request.

		const refreshToken = event.cookies.get('refresh_token');

		if (!refreshToken) return res;

		console.log('[handleFetch] got 401, attempting refresh');

		const response_with_new_cookies = await refreshAccessTokenRefreshPost({
			fetchImpl: fetch,
			headers: {
				cookie: `refresh_token=${refreshToken}`
			}
		} as RequestInit);

		console.log('[handleFetch] refresh status:', response_with_new_cookies.status);

		if (response_with_new_cookies.status != 200 || !response_with_new_cookies.data?.access_token)
			return res;

		// access ok!
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

		// try again with new access cookie
		const retryRequest = new Request(originalRequest, {
			headers: new Headers({
				...Object.fromEntries(request.headers.entries()),
				cookie: cookieHeader
			}),
			// @ts-expect-error — duplex is required for streaming bodies in Node 18+
			duplex: 'half'
		});
		res = await fetch(retryRequest);

		return res;
	} catch (err) {
		console.error('[handleFetch] UNCAUGHT ERROR:', err);
		console.error('[handleFetch] cause:', (err as any)?.cause);
		console.error('[handleFetch] stack:', (err as Error)?.stack);
		throw err; // re-throw so behavior is unchanged (still 500), but now we have logs
	}
};
