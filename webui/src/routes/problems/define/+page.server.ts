import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { api } from '$lib/api/client';

export const load: PageServerLoad = async ({ cookies }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    throw redirect(307, '/home');
  }
  return {};
};


export const actions = {
  create: async ({ request, cookies }) => {
    const formData = await request.formData();
    const name = formData.get('name') as string;
    const description = formData.get('description') as string;

    // 1. Get refresh token from cookies
    const refreshToken = cookies.get('refresh_token');
    if (!refreshToken) {
      return { error: 'Not authenticated' };
    }

    // 2. Get a new access token from backend
    const refreshRes = await fetch(`${import.meta.env.VITE_API_URL}/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        cookie: `refresh_token=${refreshToken}`
      }
    });

    if (!refreshRes.ok) {
      return { error: 'Failed to refresh token' };
    }

    const { access_token } = await refreshRes.json();

    // 3. Use the access token in the Authorization header for the API call
    try {
      const res = await api.POST('/problem/add', {
        body: {
          name,
          description,
          variables: [],
          objectives: [],
          constraints: [],
        },
        headers: {
          Authorization: `Bearer ${access_token}`,
          'Content-Type': 'application/json'
        }
      });
      return { result: res.data };
    } catch (e) {
      return { error: 'Failed to add problem' };
    }
  }
};
