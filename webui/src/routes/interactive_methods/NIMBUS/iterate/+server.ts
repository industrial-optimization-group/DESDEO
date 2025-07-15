import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { api } from '$lib/api/client';

export const POST: RequestHandler = async ({ request, cookies }) => {
    try {
        const body = await request.json();
        
        const problemId = Number(body.problem_id);
        const sessionId = body.session_id ? Number(body.session_id) : null;
        const parentStateId = body.parent_state_id ? Number(body.parent_state_id) : null;
        const currentObjectives = body.current_objectives;
        const numDesired = body.num_desired ? Number(body.num_desired) : null;
        const preference = body.preference;
        
        // Get authentication token from cookies
        const refreshToken = cookies.get('refresh_token');
        if (!refreshToken) {
            return json({ success: false, error: 'No authentication token found' }, { status: 401 });
        }
        
        const requestBody = {
            problem_id: problemId,
            session_id: sessionId,
            parent_state_id: parentStateId,
            current_objectives: currentObjectives,
            num_desired: numDesired,
            preference: preference,
            scalarization_options: null,
            solver: null,
            solver_options: null
        };

        // Pass the authentication token to the API client
        const response = await api.POST('/method/nimbus/solve', {
            body: requestBody,
            headers: {
                'Authorization': `Bearer ${refreshToken}`
            }
        });

        console.log('Raw API response:', response);
        console.log('Response data type:', typeof response.data);

        if (!response.data) {
            throw new Error('No data received from NIMBUS solve API');
        }

        return json({
            success: true,
            data: response.data
        });

    } catch (error) {
        console.error('NIMBUS solve request failed:', error);
        return json({ 
            success: false, 
            error: error instanceof Error ? error.message : 'Unknown error occurred' 
        }, { status: 500 });
    }
};