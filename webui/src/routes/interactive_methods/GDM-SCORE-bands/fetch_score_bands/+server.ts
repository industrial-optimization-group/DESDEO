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
import type { components } from '$lib/api/client-types';

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
    

    // Call fetch_score endpoint using the authenticated API client
    const {group_id, score_bands_config} = requestData;
    const scoreBandRequest: components["schemas"]["GDMScoreBandsInitializationRequest"] = {
        group_id,
        score_bands_config: {
          num_interations: 5,  
          score_bands_config,
          voting_method: 'majority'
        }
    };

    const scoreResponse = await api.POST('/gdm-score-bands/get-or-initialize', {
        body: scoreBandRequest,
        headers: {
            'Authorization': `Bearer ${refreshToken}`, // Authenticate with refresh token
            'Content-Type': 'application/json'
        }
    });

    if (!scoreResponse.data) {
      console.error('get_or_initialize error:', scoreResponse.error);
      return json(
        { 
          error: 'Failed to fetch score bands',
          details: scoreResponse.error?.detail || 'get_or_initialize failed',
          status: scoreResponse.response?.status || 500
        }, 
        { status: scoreResponse.response?.status || 500 }
      );
    }

    const scoreData = scoreResponse.data;

    return json({
      success: true,
      data: scoreData
    });

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    const errorName = error instanceof Error ? error.name : 'Error';
    const errorStack = error instanceof Error ? error.stack : undefined;
    
    console.error('get_or_initialize error details:', {
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
 * 2. Server calls get_or_initialize endpoint to get score bands data from completed iteration
 * 3. Server returns score bands response to frontend
 */