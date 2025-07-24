import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { api } from '$lib/api/client';

export const POST: RequestHandler = async ({ request, cookies }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    const {
      problemId,
      solutions,
      name = 'Saved Solutions'
    } = await request.json();

    const saveRequest = {
      problem_id: problemId,
      solutions,
      name
    };

    const response = await api.POST('/method/emo/save', {
      body: saveRequest
    });

    if (!response.data) {
      return json(
        { error: 'Failed to save solutions' }, 
        { status: response.response?.status || 500 }
      );
    }

    return json({
      success: true,
      data: response.data,
      message: 'Solutions saved successfully'
    });

  } catch (error) {
    console.error('Save error:', error);
    return json({ error: 'Server error' }, { status: 500 });
  }
};