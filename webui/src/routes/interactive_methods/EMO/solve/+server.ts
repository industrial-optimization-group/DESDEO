// TODO: Replace with orval-generated endpoint once /method/emo/solve is added to the OpenAPI spec and orval is re-run
import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { customFetch } from '$lib/api/new-client';

const BASE_URL = (process.env.API_URL || 'http://localhost:8000').replace(/\/+$/, '');

type EMOState = Record<string, unknown>;

export const POST: RequestHandler = async ({ request, cookies }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    const solveRequest = await request.json();

    console.log('Received solve request:', JSON.stringify(solveRequest, null, 2));
    console.log('Making API call to /method/emo/solve');

    const response = await customFetch<{ status: number; data: any; headers: Headers }>(`${BASE_URL}/method/emo/solve`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${refreshToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(solveRequest)
    });

    console.log('API response status:', response.status);

    if (response.status !== 200) {
      console.error('API error:', { status: response.status, data: response.data });

      return json(
        {
          error: 'Failed to solve problem',
          details: response.data || 'No data returned from API',
          status: response.status
        },
        { status: response.status || 500 }
      );
    }

    console.log('Returning successful response');
    return json({
      success: true,
      data: response.data as EMOState,
      message: 'Problem solved successfully'
    });

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    const errorName = error instanceof Error ? error.name : 'Error';

    console.error('EMO solve error details:', { message: errorMessage, name: errorName });

    return json({
      error: 'Server error',
      details: errorMessage,
      type: errorName
    }, { status: 500 });
  }
};
