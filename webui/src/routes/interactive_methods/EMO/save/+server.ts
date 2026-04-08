// TODO: Replace with orval-generated endpoint once /method/emo/save is added to the OpenAPI spec and orval is re-run
import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { customFetch } from '$lib/api/new-client';

const BASE_URL = import.meta.env.VITE_API_URL as string;

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

    const response = await customFetch<{ status: number; data: any }>(`${BASE_URL}/method/emo/save`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${refreshToken}`
      },
      body: JSON.stringify(saveRequest)
    });

    if (response.status !== 200) {
      return json(
        { error: 'Failed to save solutions' },
        { status: response.status || 500 }
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
