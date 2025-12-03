/**
 * Server-side API endpoint for EMO fetch score bands.
 * This endpoint acts as a proxy between the frontend and the backend DESDEO API.
 * 
 * Route: POST /interactive_methods/GDM-SCORE-bands/fetch_score_bands
 * 
 * Purpose:
 * - Calls fetch_score endpoint to get score bands data from a completed EMO iteration
 * - Returns the score bands results to the frontend
 * 
 * Author: AI Assistant
 * Created: November 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { api } from '$lib/api/client';

/**
 * POST handler for EMO fetch score requests
 * 
 * Expected request body: Contains problem_id, parent_state_id and other EMO parameters
 * 
 * Returns: JSON response with score bands data from EMO fetch_score endpoint
 */
export const POST: RequestHandler = async ({ request, cookies }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    // Parse the incoming request from the frontend
    const requestData = await request.json();
    
    console.log('Starting EMO fetch score');

    // Call fetch_score endpoint using the authenticated API client
    const scoreRequest = {
      problem_id: requestData.problem_id || 1,
      session_id: requestData.session_id || null,
      parent_state_id: requestData.parent_state_id || null, // This should come from iterate response
      config: requestData.config || null,
      solution_ids: requestData.solution_ids || [] // Default empty array
    };

    console.log('Calling EMO fetch_score endpoint:', scoreRequest);

    const scoreResponse = await api.POST('/method/emo/fetch_score', {
        body: scoreRequest,
        headers: {
            'Authorization': `Bearer ${refreshToken}`, // Authenticate with refresh token
            'Content-Type': 'application/json'
        }
    });

    if (!scoreResponse.data) {
      console.error('EMO fetch_score error:', scoreResponse.error);
      return json(
        { 
          error: 'Failed to fetch score bands',
          details: scoreResponse.error?.detail || 'EMO fetch_score failed',
          status: scoreResponse.response?.status || 500
        }, 
        { status: scoreResponse.response?.status || 500 }
      );
    }

    const scoreData = scoreResponse.data;
    console.log('EMO fetch_score response:', scoreData);

    return json({
      success: true,
      data: scoreData,
      message: 'EMO fetch score completed successfully'
    });

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    const errorName = error instanceof Error ? error.name : 'Error';
    const errorStack = error instanceof Error ? error.stack : undefined;
    
    console.error('EMO fetch score error details:', {
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

/**
 * Flow Summary:
 * 1. Frontend sends POST request to /interactive_methods/GDM-SCORE-bands/fetch_score_bands
 * 2. Server calls EMO fetch_score endpoint to get score bands data from completed iteration
 * 3. Server returns score bands response to frontend
 */