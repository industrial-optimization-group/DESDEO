// src/routes/api/emo/solve/+server.ts
import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import createClient from 'openapi-fetch';
import type { paths } from '$lib/api/client-types';
import type { components } from '$lib/api/client-types';

// CREATE THE SERVER-SIDE API CLIENT HERE (Option 1)
const serverApi = createClient<paths>({
  baseUrl: process.env.API_URL || 'http://localhost:8000' // Use regular env var, not VITE_
});

type EMOSolveRequest = components['schemas']['EMOSolveRequest'];
type EMOState = components['schemas']['EMOState'];

export const POST: RequestHandler = async ({ request, cookies }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    const solveRequest: EMOSolveRequest = await request.json();
    
    console.log('Received solve request:', JSON.stringify(solveRequest, null, 2));
    console.log('Making API call to /method/emo/solve');

    // USE THE SERVER API CLIENT INSTEAD OF THE REGULAR API CLIENT
    // Make the request with the refresh token
    const response = await serverApi.POST('/method/emo/solve', {
      body: solveRequest,
      headers: {
        'Authorization': `Bearer ${refreshToken}`, // Use refresh token directly
        'Content-Type': 'application/json'
      }
    });

    console.log('API response status:', response.response?.status);
    console.log('API response data:', response.data);
    console.log('API response error:', response.error);

    if (!response.data) {
      console.error('No data in response:', {
        status: response.response?.status,
        statusText: response.response?.statusText,
        error: response.error
      });
      
      return json(
        { 
          error: 'Failed to solve problem',
          details: response.error || 'No data returned from API',
          status: response.response?.status
        }, 
        { status: response.response?.status || 500 }
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
    const errorStack = error instanceof Error ? error.stack : undefined;
    
    console.error('EMO solve error details:', {
        message: errorMessage,
        stack: errorStack,
        name: errorName
    });
    
    return json({ 
        error: 'Server error',
        details: errorMessage,
        type: errorName
    }, { status: 500 });
  }
};