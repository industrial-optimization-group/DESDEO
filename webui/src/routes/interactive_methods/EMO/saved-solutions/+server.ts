import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { api } from '$lib/api/client';

export const GET: RequestHandler = async ({ cookies }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    const response = await api.GET('/method/emo/saved-solutions');

    if (!response.data) {
      // Just use a generic error message
      return json(
        { error: 'Failed to get saved solutions' }, 
        { status: response.response?.status || 500 }
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