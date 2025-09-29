/**
 * Server-side API endpoint for calculating SCORE bands parameters.
 * This endpoint acts as a proxy between the frontend and the backend DESDEO API.
 * 
 * Route: POST /interactive_methods/GDM-SCORE-bands/calculate
 * 
 * Purpose:
 * - Receives score bands calculation requests from the frontend
 * - Forwards the request to the backend DESDEO API
 * - Returns the calculated parameters to the frontend
 * 
 * Author: AI Assistant
 * Created: July 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';

// Type definitions for the score bands request
type ScoreBandsRequest = {
  data: number[][];
  objs: string[];
  dist_parameter?: number;
  use_absolute_corr?: boolean;
  distance_formula?: number;
  flip_axes?: boolean;
  clustering_algorithm?: string;
  clustering_score?: string;
};

/**
 * POST handler for score bands calculation requests
 * 
 * Expected request body: ScoreBandsRequest containing:
 * - data: Matrix of objective values (number[][])
 * - objs: Array of objective names (string[])
 * - Optional parameters for customization
 * 
 * Returns: JSON response with ScoreBandsResponse containing calculated parameters
 */
export const POST: RequestHandler = async ({ request }) => {
  try {
    // Parse the incoming score bands request from the frontend
    const calculateRequest: ScoreBandsRequest = await request.json();
    
    // Debug logging: Log the received request for troubleshooting
    console.log('Received score bands request:', JSON.stringify(calculateRequest, null, 2));
    console.log('Making API call to /method/generic/score-bands');

    // Get the backend API URL
    const apiUrl = process.env.API_URL || 'http://localhost:8000';
    
    /**
     * Forward the request to the backend DESDEO API using native fetch
     * 
     * Process:
     * - Uses native fetch for direct API communication
     * - Sends the calculation request as JSON payload
     * - No authentication required for this endpoint
     */
    const response = await fetch(`${apiUrl}/method/generic/score-bands`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(calculateRequest)
    });

    // Debug logging: Log the API response details
    console.log('API response status:', response.status);
    console.log('API response ok:', response.ok);

    /**
     * Handle API response errors
     * If the backend API didn't return a successful response, handle the error
     */
    if (!response.ok) {
      const errorText = await response.text();
      console.error('API error response:', {
        status: response.status,
        statusText: response.statusText,
        body: errorText
      });
      
      // Return error response to frontend with details from backend
      return json(
        { 
          error: 'Failed to calculate score bands parameters',
          details: errorText || `HTTP ${response.status}: ${response.statusText}`,
          status: response.status
        }, 
        { status: response.status }
      );
    }

    // Parse the successful response
    const data = await response.json();
    
    console.log('API response data:', data);

    /**
     * Success case: Return the calculated parameters to the frontend
     * 
     * The response contains:
     * - groups: Cluster assignments for each data point
     * - axis_dist: Normalized axis positions 
     * - axis_signs: Axis direction signs (1 or -1), or null
     * - obj_order: Optimal order of objectives
     */
    return json({
      success: true,
      data: data,
      message: 'Score bands parameters calculated successfully'
    });

  } catch (error) {
    /**
     * Handle unexpected errors during request processing
     * This catches:
     * - JSON parsing errors from request body
     * - Network errors from API calls
     * - Type conversion errors
     * - Any other unexpected runtime errors
     */
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    const errorName = error instanceof Error ? error.name : 'Error';
    const errorStack = error instanceof Error ? error.stack : undefined;
    
    // Detailed error logging for server-side debugging
    console.error('Score bands calculation error details:', {
        message: errorMessage,
        stack: errorStack,
        name: errorName
    });
    
    // Return generic server error to frontend (don't expose internal details)
    return json({ 
        error: 'Server error',
        details: errorMessage,
        type: errorName
    }, { status: 500 });
  }
};

/**
 * Flow Summary:
 * 1. Frontend sends POST request to /interactive_methods/GDM-SCORE-bands/calculate
 * 2. Server parses ScoreBandsRequest from request body
 * 3. Server forwards request to DESDEO backend API
 * 4. Server receives ScoreBandsResponse from backend
 * 5. Server returns processed response to frontend
 */