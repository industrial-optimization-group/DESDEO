/**
 * Server-side API endpoint for EMO iterate.
 * This endpoint acts as a proxy between the frontend and the backend DESDEO API.
 * 
 * Route: POST /interactive_methods/GDM-SCORE-bands/iterate
 * 
 * Purpose:
 * - Calls EMO iterate endpoint to start evolutionary algorithm
 * - Returns the iterate response with state_id for subsequent calls
 * 
 * Author: AI Assistant
 * Created: November 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import type { components } from '$lib/api/client-types';


/**
 * POST handler for EMO iterate requests
 * 
 * Expected request body: Contains problem_id and other EMO parameters
 * 
 * Returns: JSON response with iterate data including state_id
 */
export const POST: RequestHandler = async ({ request, cookies }) => {
  // Authentication check: Verify that the user has a valid refresh token
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    // Parse the incoming request from the frontend
    const {group_id, vote} = await request.json();
    const requestData = {
      group_id,
      vote
    }

    /**
     * Forward the request to the backend DESDEO API
     */
    const response = await api.POST('/gdm-score-bands/vote', {
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
          error: 'Failed to vote',
          details: response.error || 'No data returned from API',
          status: response.response?.status
        }, 
        { status: response.response?.status || 500 }
      );
    }

    console.log('vote response:', response.data);

    return json({
      success: true,
      data: response.data,
      message: 'vote completed successfully'
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
