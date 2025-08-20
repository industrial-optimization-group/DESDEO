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
                response = await handle_initialize(body, refreshToken);
                break;
            case 'iterate':
                response = await handle_iterate(body, refreshToken);
                break;
            case 'choose':
                return json({ success: true, message: 'solution chosen!' });
            case 'intermediate':
                response = await handle_intermediate(body, refreshToken);
                break;
            case 'save':
                response = await handle_save(body, refreshToken);
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

async function handle_save(body: any, refreshToken: string) {
        const {problem_id, solutions} = body;
        const session_id = null;
        const parent_state_id = null;
        const requestBody = {
            problem_id,
            session_id,
            parent_state_id,
            solutions
        }
        const response = await api.POST('/method/nimbus/save', {
            body: requestBody,
            headers: {
                'Authorization': `Bearer ${refreshToken}`
            }
        });

        // Check if the response has an error
        if (response.error) {
            console.error(`NIMBUS save API error: ${response.error} (Status: ${response.response?.status})`);
            throw new Error(`NIMBUS save API error: ${response.error} (Status: ${response.response?.status})`);
        }

        if (!response.data) {
            console.error('No data received from NIMBUS save API');
            throw new Error('No data received from NIMBUS save API');
        }

        return { success: true, data: response.data };
}

async function handle_initialize(body: any, refreshToken: string) {
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
    
    // Check if the response has an error
    if (response.error) {
        console.error(`NIMBUS initialization API error: ${response.error} (Status: ${response.response?.status})`);
        throw new Error(`NIMBUS initialize API error: ${response.error} (Status: ${response.response?.status})`);
    }

    if (!response.data) {
        console.error('No data received from NIMBUS initialize API');
        throw new Error('No data received from NIMBUS initialize API');
    }

    return { success: true, data: response.data };
}

async function handle_iterate(body: any, refreshToken: string) {
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

    // Check if the response has an error
    if (response.error) {
        console.error(`NIMBUS solve API error: ${response.error} (Status: ${response.response?.status})`);
        throw new Error(`NIMBUS solve API error: ${response.error} (Status: ${response.response?.status})`);
    }

    if (!response.data) {
        console.error('No data received from NIMBUS solve API');
        throw new Error('No data received from NIMBUS solve API');
    }

    return { success: true, data: response.data };
}

async function handle_intermediate(body: any, refreshToken: string) {
    const { problem_id, session_id, parent_state_id, reference_solution_1, reference_solution_2, num_desired } = body;

    const requestBody = {
        problem_id: Number(problem_id),
        session_id: session_id ? Number(session_id) : null,
        parent_state_id: parent_state_id ? Number(parent_state_id) : null,
        reference_solution_1,
        reference_solution_2,
        num_desired: num_desired ? Number(num_desired) : 4,
        scalarization_options: null,
        solver: null,
        solver_options: null
    };

    const response = await api.POST('/method/nimbus/intermediate', {
        body: requestBody,
        headers: {
            'Authorization': `Bearer ${refreshToken}`
        }
    });

    // Check if the response has an error
    if (response.error) {
        console.error(`NIMBUS intermediate API error: ${response.error} (Status: ${response.response?.status})`);
        throw new Error(`NIMBUS intermediate API error: ${response.error} (Status: ${response.response?.status})`);
    }

    if (!response.data) {
        console.error('No data received from NIMBUS intermediate API');
        throw new Error('No data received from NIMBUS intermediate API');
    }

    return { success: true, data: response.data };
}

async function handle_get_maps(body: any, refreshToken: string) {
    const { problem_id, solution } = body;
    
    try {
        const requestBody = {
            problem_id: Number(problem_id),
            solution: solution
        };

        const response = await api.POST('/utopia/', {
            body: requestBody,
            headers: {
                'Authorization': `Bearer ${refreshToken}`
            }
        });
        
        // Check if the response has an error
        if (response.error) {
            console.error(`utopia map API error: ${response.error} (Status: ${response.response?.status})`);
            throw new Error(`utopia map API error: ${response.error} (Status: ${response.response?.status})`);
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