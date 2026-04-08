// TODO: Replace with orval-generated endpoint once /method/emo/saved-solutions is added to the OpenAPI spec and orval is re-run
import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { customFetch } from '$lib/api/new-client';

const BASE_URL = import.meta.env.VITE_API_URL as string;

export const GET: RequestHandler = async ({ cookies }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    const response = await customFetch<{ status: number; data: any }>(`${BASE_URL}/method/emo/saved-solutions`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${refreshToken}`
      }
    });

    if (response.status !== 200) {
      return json(
        { error: 'Failed to get saved solutions' },
        { status: response.status || 500 }
      );
    }

    return json({
      success: true,
      data: response.data,
      message: 'Saved solutions retrieved successfully'
    });

  } catch (error) {
    console.error('Get saved solutions error:', error);
    return json({ error: 'Server error' }, { status: 500 });
  }
};
