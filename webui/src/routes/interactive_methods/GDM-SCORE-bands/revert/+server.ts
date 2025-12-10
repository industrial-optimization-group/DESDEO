/**
 * Server-side API endpoint for GDM Score Bands revert functionality.
 * This endpoint acts as a proxy between the frontend and the backend DESDEO API.
 * 
 * Route: POST /interactive_methods/GDM-SCORE-bands/revert
 * 
 * Purpose:
 * - Calls the revert endpoint to revert to a previous iteration
 * - Only group owners can revert iterations
 * - Returns confirmation of the revert action
 * 
 * Author: AI Assistant
 * Created: December 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import type { components } from '$lib/api/client-types';

/**
 * POST handler for revert iteration requests
 * 
 * Expected request body: { group_id: number, iteration_number: number }
 * 
 * Returns: JSON response with revert confirmation from backend API
 */
export const POST: RequestHandler = async ({ request, cookies }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    // Parse the incoming request from the frontend
    const requestData = await request.json();
    
    // Extract group_id and iteration_number from the request
    const { group_id, iteration_number } = requestData;
    
    // Validate required parameters
    if (typeof group_id !== 'number' || typeof iteration_number !== 'number') {
      return json(
        { 
          error: 'Invalid request',
          details: 'group_id and iteration_number must be numbers'
        }, 
        { status: 400 }
      );
    }

    // Create the revert request object matching GDMSCOREBandsRevertRequest schema
    const revertRequest: components["schemas"]["GDMSCOREBandsRevertRequest"] = {
        group_id,
        iteration_number
    };

    // Call revert endpoint using the authenticated API client
    const revertResponse = await api.POST('/gdm-score-bands/revert', {
        body: revertRequest,
        headers: {
            'Authorization': `Bearer ${refreshToken}`, // Authenticate with refresh token
            'Content-Type': 'application/json'
        }
    });

    if (!revertResponse.data && revertResponse.error) {
      console.error('Revert error:', revertResponse.error);
      return json(
        { 
          error: 'Failed to revert iteration',
          details: revertResponse.error?.detail || 'Revert failed',
          status: revertResponse.response?.status || 500
        }, 
        { status: revertResponse.response?.status || 500 }
      );
    }

    // Return successful response
    return json({
      success: true,
      data: {
        message: 'Successfully reverted to previous iteration'
      }
    });

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    const errorName = error instanceof Error ? error.name : 'Error';
    const errorStack = error instanceof Error ? error.stack : undefined;
    
    console.error('Revert error details:', {
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
 * 1. Frontend sends POST request to /interactive_methods/GDM-SCORE-bands/revert
 * 2. Server calls /gdm-score-bands/revert endpoint to revert to specified iteration
 * 3. Server returns confirmation response to frontend
 * 4. Note: Only group owners can perform revert operations (enforced by backend)
 */