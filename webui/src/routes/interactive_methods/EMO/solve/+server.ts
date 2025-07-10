/**
 * Server-side API endpoint for solving optimization problems using an EMO (Evolutionary Multi-objective Optimization) method.
 * This endpoint acts as a proxy between the frontend and the backend DESDEO API.
 * 
 * Route: POST /interactive_methods/EMO/solve
 * 
 * Purpose:
 * - Receives EMO solve requests from the frontend
 * - Authenticates the request using refresh tokens
 * - Forwards the request to the backend DESDEO API
 * - Returns the optimization results to the frontend
 * 
 * Author: Giomara Larraga (glarragw@jyu.fi)
 * Created: July 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import createClient from 'openapi-fetch';
import type { paths } from '$lib/api/client-types';
import type { components } from '$lib/api/client-types';

/**
 * Create a server-side API client for communicating with the DESDEO backend.
 * This is separate from the frontend API client because:
 * - Server-side code doesn't have access to VITE_ environment variables
 * - Uses regular NODE_ENV variables (API_URL instead of VITE_API_URL)
 * - Runs in Node.js context, not browser context
 */
const serverApi = createClient<paths>({
  baseUrl: process.env.API_URL || 'http://localhost:8000' // Default to localhost if API_URL not set
});

// Type definitions from the OpenAPI schema
type EMOSolveRequest = components['schemas']['EMOSolveRequest'];
type EMOState = components['schemas']['EMOState'];

/**
 * POST handler for EMO solve requests
 * 
 * Expected request body: EMOSolveRequest containing:
 * - problem_id: ID of the optimization problem to solve
 * - method: EMO algorithm to use (e.g., "NSGA3", "RVEA")
 * - preference: User preferences (reference points, preferred ranges, etc.)
 * - max_evaluations: Maximum number of function evaluations
 * - number_of_vectors: Number of solution vectors to generate
 * - use_archive: Whether to use solution archive
 * - session_id: Optional session identifier
 * - parent_state_id: Optional parent state for iterative solving
 * 
 * Returns: JSON response with EMOState containing optimization results
 */
export const POST: RequestHandler = async ({ request, cookies }) => {
  // Authentication check: Verify that the user has a valid refresh token
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    // Parse the incoming EMO solve request from the frontend
    const solveRequest: EMOSolveRequest = await request.json();
    
    // Debug logging: Log the received request for troubleshooting
    console.log('Received solve request:', JSON.stringify(solveRequest, null, 2));
    console.log('Making API call to /method/emo/solve');

    /**
     * Forward the request to the backend DESDEO API
     * - Uses the server-side API client (serverApi)
     * - Includes authentication via Bearer token (refresh token)
     * - Sends the solve request as JSON payload
     */
    const response = await serverApi.POST('/method/emo/solve', {
      body: solveRequest,
      headers: {
        'Authorization': `Bearer ${refreshToken}`, // Authenticate with refresh token
        'Content-Type': 'application/json'
      }
    });

    // Debug logging: Log the API response details
    console.log('API response status:', response.response?.status);
    console.log('API response data:', response.data);
    console.log('API response error:', response.error);

    /**
     * Handle API response errors
     * If the backend API didn't return data, it indicates an error occurred
     */
    if (!response.data) {
      console.error('No data in response:', {
        status: response.response?.status,
        statusText: response.response?.statusText,
        error: response.error
      });
      
      // Return error response to frontend with details from backend
      return json(
        { 
          error: 'Failed to solve problem',
          details: response.error || 'No data returned from API',
          status: response.response?.status
        }, 
        { status: response.response?.status || 500 }
      );
    }

    /**
     * Success case: Return the optimization results to the frontend
     * The response.data contains an EMOState object with:
     * - solutions: Array of solution vectors
     * - outputs: Array of objective values for each solution
     * - method: The EMO algorithm used
     * - number_of_vectors: Number of solutions generated
     * - Other metadata about the optimization run
     */
    console.log('Returning successful response');
    return json({
      success: true,
      data: response.data as EMOState,
      message: 'Problem solved successfully'
    });

  } catch (error) {
    /**
     * Error handling for unexpected errors during processing
     * This could include:
     * - JSON parsing errors
     * - Network errors when calling the backend API
     * - Type conversion errors
     * - Any other unexpected runtime errors
     */
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    const errorName = error instanceof Error ? error.name : 'Error';
    const errorStack = error instanceof Error ? error.stack : undefined;
    
    // Detailed error logging for server-side debugging
    console.error('EMO solve error details:', {
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
 * 1. Frontend sends POST request to /interactive_methods/EMO/solve
 * 2. Server checks for valid refresh token in cookies
 * 3. Server parses EMOSolveRequest from request body
 * 4. Server forwards request to DESDEO backend API with authentication
 * 5. Server receives EMOState response from backend
 * 6. Server returns processed response to frontend
 */