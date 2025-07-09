import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { api } from '$lib/api/client';

export const GET: RequestHandler = async ({ cookies, url }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    // Optional: get problem_id from query params
    const problemId = url.searchParams.get('problem_id');
    
    const response = await api.GET('/method/emo/saved-solutions', {
      params: problemId ? { query: { problem_id: problemId } } : undefined
    });

    if (!response.data) {
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