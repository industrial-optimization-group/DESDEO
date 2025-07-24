import { json } from '@sveltejs/kit';
import { serverApi as api } from '$lib/api/client';
import type { RequestHandler } from './$types';


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
                response = await handleInitialize(body, refreshToken);
                break;
            case 'iterate':
                response = await handleIterate(body, refreshToken);
                break;
            case 'choose':
                return json({ success: true, message: 'solution chosen! ...not' });
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

async function handleInitialize(body: any, refreshToken: string) {
    const { problem_id, session_id, parent_state_id, solver } = body;

    const requestBody = {
        problem_id: Number(problem_id),
        session_id: session_id ? Number(session_id) : null,
        parent_state_id: parent_state_id ? Number(parent_state_id) : null,
        solver
    };

    const response = await api.POST('/method/nimbus/initialize', {
        body: requestBody,
        headers: {
            'Authorization': `Bearer ${refreshToken}`
        }
    });
    console.log('Raw initialization API response:', response);

    // Check if the response has an error
    if (response.error) {
        console.error('NIMBUS initialization API error:', response.error);
        console.error('Response status:', response.response?.status);
        console.error('Response status text:', response.response?.statusText);
        throw new Error(`NIMBUS initialize API error: ${response.error} (Status: ${response.response?.status})`);
    }

    if (!response.data) {
        console.error('No data received from NIMBUS initialize API');
        throw new Error('No data received from NIMBUS initialize API');
    }

    return { success: true, data: response.data };
}

async function handleIterate(body: any, refreshToken: string) {
    const { problem_id, session_id, parent_state_id, current_objectives, num_desired, preference } = body;

    const requestBody = {
        problem_id: Number(problem_id),
        session_id: session_id ? Number(session_id) : null,
        parent_state_id: parent_state_id ? Number(parent_state_id) : null,
        current_objectives,
        num_desired: num_desired ? Number(num_desired) : null,
        preference,
        scalarization_options: null,
        solver: null,
        solver_options: null
    };

    const response = await api.POST('/method/nimbus/solve', {
        body: requestBody,
        headers: {
            'Authorization': `Bearer ${refreshToken}`
        }
    });
    
    console.log('Raw iteration API response:', response);
    console.log('Response data type:', typeof response.data);

    // Check if the response has an error
    if (response.error) {
        console.error('NIMBUS solve API error:', response.error);
        console.error('Response status:', response.response?.status);
        console.error('Response status text:', response.response?.statusText);
        throw new Error(`NIMBUS solve API error: ${response.error} (Status: ${response.response?.status})`);
    }

    if (!response.data) {
        console.error('No data received from NIMBUS solve API');
        throw new Error('No data received from NIMBUS solve API');
    }

    return { success: true, data: response.data };
}