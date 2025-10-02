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


export const POST: RequestHandler = async ({ url, request, cookies }) => {
    try {
        const body = await request.json();
        const type = url.searchParams.get('type');
        // Get authentication token from cookies
        const refreshToken = cookies.get('refresh_token');
        if (!refreshToken) {
            return json({ success: false, error: 'No authentication token found' }, { status: 401 });
        }

        let response;
        switch (type) {
            case 'initialize':
                response = await handle_init(body, refreshToken);
                break;
            case 'get_latest_results':
                response = await get_results(body, refreshToken);
                break;
            case 'get_all_iterations':
                response = await get_all_iterations(body, refreshToken);
                break;
            case 'switch_phase':
                response = await switch_phase(body, refreshToken);
                break;
            case 'get_maps':
                response = await handle_get_maps(body, refreshToken);
                break;
            default:
                return json({ success: false, error: 'Invalid operation type' }, { status: 400 });
        }

        return json(response);

    } catch (error) {
        console.error('Request failed:', error);
        return json({ 
            success: false, 
            error: error instanceof Error ? error.message : 'Unknown error occurred' 
        }, { status: 500 });
    }
};

interface APIError {
    detail: string;
    [key: string]: any;
}
async function handle_init(body: any, refreshToken: string) {
    const { group_id } = body;
    const requestBody = {
        group_id: Number(group_id)
    };

    const response = await api.POST('/gnimbus/initialize', {
        body: requestBody,
        headers: {
            'Authorization': `Bearer ${refreshToken}`
        }
    });

    // Check if the response has an error
    if (response.error) {
        console.error(`GNIMBUS initialize API error: ${response.error.detail} (Status: ${response.response?.status})`);
        throw new Error(`GNIMBUS initialize API error: ${response.error.detail} (Status: ${response.response?.status})`);
    }

    if (!response.data) {
        console.error('No data received from GNIMBUS initialize API');
        throw new Error('No data received from GNIMBUS initialize API');
    }

    return { success: true, data: response.data };
}

async function get_results(body: any, refreshToken: string) {
    const { group_id } = body;
    if (!group_id) {
        throw new Error('group_id is required');
    }

    const requestBody = {
        group_id: Number(group_id)
    };

    const response = await api.POST('/gnimbus/get_latest_results', {
        body: requestBody,
        headers: {
            'Authorization': `Bearer ${refreshToken}`
        }
    });

    // For any other error, throw it
    if (response.error) {
        throw new Error(response.error as string);
    }

    // Return the successful response
    return { success: true, data: response.data };
}

async function get_all_iterations(body: any, refreshToken: string) {
    const { group_id } = body;
    const requestBody = {
        group_id: Number(group_id)
    };

    const response = await api.POST('/gnimbus/all_iterations', {
        body: requestBody,
        headers: {
            'Authorization': `Bearer ${refreshToken}`
        }
    });

    // If we get an error because of problem is not initialized, return a special response
    const error = response.error as unknown as APIError;
    if (error && response.response?.status === 400 && error.detail === "Problem has not been initialized!") {
        return {
            success: false,
            error: 'not_initialized'
        };
    }

    // Check if the response has an error
    if (response.error) {
        console.error(`GNIMBUS full_response API error: ${response.error.detail} (Status: ${response.response?.status})`);
        throw new Error(`GNIMBUS full_response API error: ${response.error.detail} (Status: ${response.response?.status})`);
    }

    if (!response.data) {
        console.error('No data received from GNIMBUS full_response API');
        throw new Error('No data received from GNIMBUS full_response API');
    }

    return { success: true, data: response.data };

}


async function switch_phase(body: any, refreshToken: string) {
        const {group_id, new_phase} = body;
        const requestBody = {
            group_id: Number(group_id),
            new_phase
        }
        const response = await api.POST('/gnimbus/toggle_phase', {
            body: requestBody,
            headers: {
                'Authorization': `Bearer ${refreshToken}`
            }
        });

        // If we get an error that the step is wrong for phase change, return a special response
        const error = response.error as unknown as APIError;
        if (error && response.response?.status === 400) {
            return {
                success: false,
                error: 'wrong_step'
            };
        }

        // Check if the response has an error
        if (response.error) {
            console.error(`GNIMBUS toggle_phase API error: ${response.error.detail} (Status: ${response.response?.status})`);
            throw new Error(`GNIMBUS toggle_phase API error: ${response.error.detail} (Status: ${response.response?.status})`);
        }

        if (!response.data) {
            console.error('No data received from GNIMBUS toggle_phase API');
            throw new Error('No data received from GNIMBUS toggle_phase API');
        }

        return { success: true, data: response.data };
}

async function handle_get_maps(body: any, refreshToken: string) {
    const { problem_id, solution } = body;
    
    try {
        // Ensure solution matches SolutionInfo model: state_id, solution_index, name
        const requestBody = {
            problem_id: Number(problem_id),
            solution
        }

        const response = await api.POST('/utopia/', {
            body: requestBody,
            headers: {
                'Authorization': `Bearer ${refreshToken}`
            }
        });

        // Check if the response has an error
        if (response.error) {
            console.error('utopia map API error:', response.error, response.response);
            throw new Error(`utopia map API error: ${JSON.stringify(response.error)} (Status: ${response.response?.status})`);
        }

        if (!response.data) {
            console.error('No data received from map API');
            throw new Error('No data received from map API');
        }
        const mapData = response.data;

        return { 
            success: true, 
            data: mapData 
        };
    } catch (error) {
        console.error('Failed to get maps:', error);
        return { 
            success: false, 
            error: error instanceof Error ? error.message : 'Failed to get maps' 
        };
    }
}