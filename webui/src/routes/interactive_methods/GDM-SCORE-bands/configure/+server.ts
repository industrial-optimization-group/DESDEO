/**
 * Server-side API endpoint for GDM Score Bands configuration.
 * This endpoint acts as a proxy between the frontend and the backend DESDEO API.
 * 
 * Route: POST /interactive_methods/GDM-SCORE-bands/configure
 * 
 * Purpose:
 * - Calls the configure endpoint to update SCORE bands settings
 * - Only group owners can configure settings
 * - Triggers re-clustering with new configuration
 * 
 * Author: AI Assistant
 * Created: December 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import type { components } from '$lib/api/client-types';

/**
 * POST handler for configure SCORE bands requests
 * 
 * Expected request body: { group_id: number, config: SCOREBandsGDMConfig }
 * 
 * Returns: JSON response with configuration confirmation from backend API
 */
export const POST: RequestHandler = async ({ request, cookies }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    // Parse the incoming request from the frontend
    const requestData = await request.json();
    
    // Extract group_id and config from the request
    const { group_id, config } = requestData;
    
    // Validate required parameters
    if (typeof group_id !== 'number') {
      return json(
        { 
          error: 'Invalid request',
          details: 'group_id must be a number'
        }, 
        { status: 400 }
      );
    }

    if (!config) {
      return json(
        { 
          error: 'Invalid request',
          details: 'config is required'
        }, 
        { status: 400 }
      );
    }

    // Call configure endpoint using the authenticated API client
    // Note: The backend expects config as the body and group_id as a query parameter
    const configureResponse = await api.POST('/gdm-score-bands/configure', {
        body: config,
        params: {
          query: {
            group_id: group_id
          }
        },
        headers: {
            'Authorization': `Bearer ${refreshToken}`, // Authenticate with refresh token
            'Content-Type': 'application/json'
        }
    });

    if (!configureResponse.data && configureResponse.error) {
      console.error('Configure error:', configureResponse.error);
      return json(
        { 
          error: 'Failed to configure SCORE bands',
          details: configureResponse.error?.detail || 'Configuration failed',
          status: configureResponse.response?.status || 500
        }, 
        { status: configureResponse.response?.status || 500 }
      );
    }

    // Return successful response
    return json({
      success: true,
      data: {
        message: 'Successfully configured SCORE bands settings'
      }
    });

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    const errorName = error instanceof Error ? error.name : 'Error';
    const errorStack = error instanceof Error ? error.stack : undefined;
    
    console.error('Configure error details:', {
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
 * 1. Frontend sends POST request to /interactive_methods/GDM-SCORE-bands/configure
 * 2. Server calls /gdm-score-bands/configure endpoint with config and group_id
 * 3. Server returns confirmation response to frontend
 * 4. Note: Only group owners can perform configuration operations (enforced by backend)
 */