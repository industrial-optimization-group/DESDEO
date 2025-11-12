/**
 * +server.ts - NIMBUS API Server Endpoint
 *
 * @author Stina Palomäki <palomakistina@gmail.com>
 * @created August 2025
 *
 * @description
 * This server endpoint handles all NIMBUS method API requests, acting as a proxy between
 * the frontend and the backend API. It supports operations like initializing NIMBUS,
 * iterating to find new solutions, generating intermediate solutions, saving solutions,
 * and fetching map data for UTOPIA visualization.
 *
 * @endpoints
 * - initialize: Initializes a new NIMBUS session with the backend
 * - iterate: Performs a NIMBUS iteration based on user preferences
 * - intermediate: Generates intermediate solutions between two reference solutions
 * - choose: Selects a final solution (TODO: currently not implemented)
 * - save: Saves a solution with a name
 * - remove_saved: Removes a saved solution (TODO: currently not implemented)
 * - get_maps: Retrieves map data for UTOPIA visualization
 *
 * @authentication
 * All endpoints require authentication via refresh_token cookie.
 *
 * @error_handling
 * Returns standardized JSON responses with success/error fields and appropriate HTTP status codes.
 */
import { json } from '@sveltejs/kit';
import { serverApi as api } from '$lib/api/client';
import type { RequestHandler } from '@sveltejs/kit';

async function makeApiRequest(endpoint: string, body: any, refreshToken: string) {
    try {
        const response = await api.POST(endpoint as any, {
            body,
            headers: {
                Authorization: `Bearer ${refreshToken}`
            }
        });

        // Handle API errors
        if (response.error || !response.data) {
            const status = response.response?.status || 'N/A';
            const detail = 
                response.error.detail || response.error.toString() || 'Failed to process request';
            console.error(`API error on endpoint ${endpoint}: ${status} ${detail}`);
            return {
                success: false,
                error: detail,
                status: status,
            };
        }

        return {
            success: true,
            data: response.data
        };
    } catch (error) {
        const errorMessage =
            error instanceof Error ? error.message : `Unknown error on endpoint ${endpoint}`;
        console.error(`Caught exception on endpoint ${endpoint}:`, errorMessage);
        return {
            success: false,
            error: errorMessage,
            status: 500
        };
    }
}

type HandlerFunction = (body: any, refreshToken: string) => Promise<any>;

const handlers: Record<string, HandlerFunction> = {
    initialize: (body, refreshToken) => {
        const { group_id } = body;
        const requestBody = {
            group_id: Number(group_id)
        };
        return makeApiRequest('/gnimbus/initialize', requestBody, refreshToken);
    },

    get_latest_results: (body, refreshToken) => {
        const { group_id } = body;
        if (!group_id) {
            return Promise.resolve({
                success: false,
                error: 'group_id is required'
            });
        }
        const requestBody = {
            group_id: Number(group_id)
        };
        return makeApiRequest('/gnimbus/get_latest_results', requestBody, refreshToken);
    },

    get_all_iterations: async (body, refreshToken) => {
        const { group_id } = body;
        const requestBody = {
            group_id: Number(group_id)
        };
        
        const response = await makeApiRequest('/gnimbus/all_iterations', requestBody, refreshToken);
        
        // Special case for not initialized error
        if (!response.success && response.error && response.error.includes('Problem has not been initialized!')) {
            return {
                success: false,
                error: 'not_initialized'
            };
        }
        
        return response;
    },

    switch_phase: async (body, refreshToken) => {
        const { group_id, new_phase } = body;
        const requestBody = {
            group_id: Number(group_id),
            new_phase
        };
        
        const response = await makeApiRequest('/gnimbus/toggle_phase', requestBody, refreshToken);
        
        // Special case for wrong step error
        if (!response.success && response.error && response.error.includes('400')) {
            return {
                success: false,
                error: 'wrong_step'
            };
        }
        
        return response;
    },
        revert_iteration: (body, refreshToken) => {
        const { group_id , state_id} = body;
        if (!group_id) {
            return Promise.resolve({
                success: false,
                error: 'group_id is required'
            });
        }        
        if (!state_id) {
            return Promise.resolve({
                success: false,
                error: 'state_id is required'
            });
        }
        const requestBody = {
            group_id: Number(group_id),
            state_id: Number(state_id)
        };
        return makeApiRequest('/gnimbus/revert_iteration', requestBody, refreshToken);
    },

    get_phase: async (body, refreshToken) => {
        const { group_id } = body;
        const requestBody = {
            group_id: Number(group_id)
        };
        
        return makeApiRequest('/gnimbus/get_phase', requestBody, refreshToken);
    },

    get_maps: (body, refreshToken) => {
        const { problem_id, solution } = body;
        const requestBody = {
            problem_id: Number(problem_id),
            solution
        };
        return makeApiRequest('/utopia/', requestBody, refreshToken);
    }
};

export const POST: RequestHandler = async ({ url, request, cookies }) => {
    try {
        const body = await request.json();
        const type = url.searchParams.get('type');
        const refreshToken = cookies.get('refresh_token');
        
        if (!refreshToken) {
            return json({ success: false, error: 'No authentication token found' }, { status: 401 });
        }

        if (!type) {
            return json({ success: false, error: 'Invalid request type' }, { status: 400 });
        }

        const handler = handlers[type];
        if (handler) {
            const response = await handler(body, refreshToken);
            return json(response, {
                status: response.status || 200 // Use the API status if available, otherwise 200
            });
        } else {
            return json({ success: false, error: 'Invalid operation type' }, { status: 400 });
        }
    } catch (error) {
        console.error('Request failed:', error);
        return json(
            {
                success: false,
                error: error instanceof Error ? error.message : 'Unknown error occurred'
            },
            { status: 500 }
        );
    }
};
