/**
 * Server-side API endpoint for GDM SCORE Bands vote confirmation.
 * This endpoint acts as a proxy between the frontend and the backend DESDEO API.
 * 
 * Route: POST /interactive_methods/GDM-SCORE-bands/confirm_vote
 * 
 * Purpose:
 * - Calls confirm-vote endpoint to confirm user's vote in group decision making
 * - Allows users to confirm their previously cast vote
 * - Returns confirmation status from the backend, but there is no response data that is used: websocket handles updates
 * 
 * Author: Stina Palomäki
 * Created: December 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import type { components } from '$lib/api/client-types';


/**
 * POST handler for GDM SCORE Bands vote confirmation requests
 * 
 * Expected request body: { group_id: number }
 * 
 * Returns: JSON response with vote confirmation status
 */
export const POST: RequestHandler = async ({ request, cookies }) => {
  // Authentication check: Verify that the user has a valid refresh token
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    // Parse the incoming request from the frontend
    const {group_id} = await request.json();
    const requestData = {
      group_id,    }

    /**
     * Forward the request to the backend DESDEO API
     */
    const response = await api.POST('/gdm-score-bands/confirm', {
      body: requestData,
      headers: {
        'Authorization': `Bearer ${refreshToken}`, // Authenticate with refresh token
        'Content-Type': 'application/json'
      }
    });

    if (!response.data) {
      console.error('No data in response:', {
        status: response.response?.status,
        statusText: response.response?.statusText,
        error: response.error
      });
      
      return json(
        { 
          error: 'Failed to confirm',
          details: response.error || 'No data returned from API',
          status: response.response?.status
        }, 
        { status: response.response?.status || 500 }
      );
    }

    console.log('confirm response:', response.data);

    return json({
      success: true,
      data: response.data,
      message: 'confirm completed successfully'
    });

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    const errorName = error instanceof Error ? error.name : 'Error';
    const errorStack = error instanceof Error ? error.stack : undefined;
    
    console.error('voting error details:', {
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
