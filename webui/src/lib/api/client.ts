import { PUBLIC_API_URL } from "$env/static/public";
import createClient from 'openapi-fetch';
import type { paths } from './client-types';
import { auth } from '../../stores/auth';
import { get } from 'svelte/store';

const BASE_URL = PUBLIC_API_URL

export const api = createClient<paths>({baseUrl: BASE_URL});

api.use({
  async onRequest({ request }) {
    const token = get(auth).accessToken

    if (token) request.headers.set('Authorization', `Bearer ${token}`)

    return request
  },

  async onResponse({ response }) {
    if (response.status === 401) {
      const refreshRes = await fetch(`${BASE_URL}/refresh`, {
        method: 'POST',
        credentials: 'include'
      })

      if (refreshRes.ok) {
        const { access_token } = await refreshRes.json()
        auth.setAuth(access_token, get(auth).user)

        // Retry original request with new token
        const retryReq = new Request(response.url, {
          method: response.url.method,
          headers: {
            ...Object.fromEntries(response.request.headers),
            Authorization: `Bearer ${access_token}`
          },
          body: await response.clone().text()
        })

        return fetch(retryReq)

      } else {
        auth.clearAuth()
      }
    }

    return response
  }
})
