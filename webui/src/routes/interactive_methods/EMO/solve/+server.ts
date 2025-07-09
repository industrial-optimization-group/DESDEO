// src/routes/api/emo/solve/+server.ts
import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import type { components } from '$lib/api/client-types';

type EMOSolveRequest = components['schemas']['EMOSolveRequest'];
type EMOState = components['schemas']['EMOState'];

export const POST: RequestHandler = async ({ request, cookies }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    const solveRequest: EMOSolveRequest = await request.json();

    const response = await api.POST('/method/emo/solve', {
      body: solveRequest
    });

    if (!response.data) {
      return json(
        { error: 'Failed to solve problem' }, 
        { status: response.response?.status || 500 }
      );
    }

    return json({
      success: true,
      data: response.data as EMOState,
      message: 'Problem solved successfully'
    });

  } catch (error) {
    console.error('EMO solve error:', error);
    return json({ error: 'Server error' }, { status: 500 });
  }
};