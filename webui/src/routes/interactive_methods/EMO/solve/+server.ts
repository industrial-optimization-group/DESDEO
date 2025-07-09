// src/routes/api/emo/solve/+server.ts
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
      method = 'NSGA3',
      maxEvaluations = 1000,
      numberOfVectors = 30,
      useArchive = true,
      preference = { aspiration_levels: {} }
    } = await request.json();

    const solveRequest = {
      problem_id: problemId,
      method,
      preference,
      max_evaluations: maxEvaluations,
      number_of_vectors: numberOfVectors,
      use_archive: useArchive
    };

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
      data: response.data,
      message: 'Problem solved successfully'
    });

  } catch {
    return json({ error: 'Server error' }, { status: 500 });
  }
};