import createClient from 'openapi-fetch';
import type { paths } from './client-types';
import { auth } from '../../stores/auth';
import { get } from 'svelte/store';
import { browser } from '$app/environment';


const BASE_URL = import.meta.env.VITE_API_URL;

export const api = createClient<paths>({baseUrl: BASE_URL});

export const serverApi = createClient<paths>({
    baseUrl: browser ? BASE_URL : (process.env.API_BASE_URL || 'http://localhost:8000')  
});

api.use({
	async onRequest({ request }) {
        // appends the access token to requests
		const token = get(auth).accessToken;
		if (token) {
			request.headers.set('Authorization', `Bearer ${token}`);
		}

        // even if no token, just send the request and handle the response
		return request;
	},

	async onResponse({ request, response }) {
		if (response.status === 401) {
            // if unauthorized, try to get a new access token
			const refreshRes = await fetch(`${BASE_URL}/refresh`, {
				method: 'POST',
				credentials: 'include'  // makes sure the cookie is sent
			});

			if (refreshRes.ok) {
				const { access_token } = await refreshRes.json();
				auth.setAuth(access_token, get(auth).user);

				// Clone original request with new token
				const retryReq = new Request(request.url, {
					method: request.method,
					headers: new Headers(request.headers),
					body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.clone().text() : undefined
				});
				retryReq.headers.set('Authorization', `Bearer ${access_token}`);

				return fetch(retryReq);
			} else {
				auth.clearAuth();
			}
		}

        // otherwise just return the response
		return response;
	}
});