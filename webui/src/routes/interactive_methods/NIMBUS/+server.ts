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
                return json({ success: true, message: 'solution chosen! ...not' });
            case 'intermediate':
                return json({ success: true, message: 'intermediate solutions blah blah' });
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
        // TODO: request is right but only for the future endpoint. Enable the commented request when the new endpoint is implemented.
        // matching the current endpoint is not even possible right now, because it wants the extra unneccessary information that does not exist in frontend anymore
        const {problem_id, solutions} = body;
        const session_id = null;
        const parent_state_id = null;
        const requestBody = {
            problem_id,
            session_id,
            parent_state_id,
            solutions
        }
        // const response = await api.POST('/method/nimbus/save', {
        //     body: requestBody,
        //     headers: {
        //         'Authorization': `Bearer ${refreshToken}`
        //     }
        // });
        console.log("Solution is " + JSON.stringify(requestBody));

        return { success: true, body: 1 };

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
    console.log('Raw initialization API response:', response);
    //  data: {
    //     method: 'nimbus',
    //     phase: 'solve_candidates',
    //     scalarization_options: null,
    //     solver: null,
    //     solver_options: null,
    //     current_objectives: {
    //       f_1: 309250.3028396401,
    //       f_2: 3432.270495150779,
    //       f_3: 72436.3955323759,
    //       f_4: 24685.73413615731
    //     },
    //     num_desired: 4,
    //     previous_preference: { preference_type: 'reference_point', aspiration_levels: [Object] },
    //     solver_results: [ [Object], [Object], [Object], [Object] ]
    //   },
    
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
    // MOCK the future version of http response:

    // Transform the current response format to match the future format
    const originalData = response.data;
    const mockStateId = Math.floor(Math.random() * 10000); // Generate a mock state ID
    
    // Convert solver_results to the new format
    const solutionsList = Array.isArray(originalData.solver_results) 
        ? originalData.solver_results.map((result, index) => {
            // Extract objective values from the result
            return {
                objective_values: result.optimal_objectives || {},
                state_id: mockStateId,
                result_index: index,
                optimal_variables: result.optimal_variables || {},
            };
          })
        : [];
    
    // Create the transformed response in the new format
    const transformedData = {
        state_id: mockStateId,
        previous_reference_point: 'previous_preference' in originalData && originalData.previous_preference ? 
            originalData.previous_preference : 
            null,
        current_solutions: solutionsList,
        saved_solutions: [],
        all_solutions: solutionsList,   // Using same solutions for both lists for now
    };

    return { success: true, data: transformedData };
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
    
    console.log('Raw iteration API response:', response);
    //   data: {
    //     method: 'nimbus',
    //     phase: 'solve_candidates',
    //     scalarization_options: null,
    //     solver: null,
    //     solver_options: null,
    //     current_objectives: {
    //       f_1: 309250.3028396401,
    //       f_2: 3432.270495150779,
    //       f_3: 72436.3955323759,
    //       f_4: 24685.734136157123
    //     },
    //     num_desired: 4,
    //     previous_preference: { preference_type: 'reference_point', aspiration_levels: [Object] },
    //     solver_results: [ [Object], [Object], [Object], [Object] ]
    //   }
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

    // MOCK the future version of http response:

    // Transform the current response format to match the future format
    const originalData = response.data;
    const mockStateId = Math.floor(Math.random() * 10000); // Generate a mock state ID
    
    // Convert solver_results to the new format
    const solutionsList = Array.isArray(originalData.solver_results) 
        ? originalData.solver_results.map((result, index) => {
            // Extract objective values from the result
            return {
                objective_values: result.optimal_objectives || {},
                state_id: mockStateId,
                result_index: index,
                optimal_variables: result.optimal_variables || {},
            };
          })
        : [];
    
    // Create the transformed response in the new format
    const transformedData = {
        state_id: mockStateId,
        previous_reference_point: originalData.previous_preference,
        current_solutions: solutionsList,
        saved_solutions: solutionsList, // Using same solutions for all three lists for now
        all_solutions: solutionsList,   // Using same solutions for all three lists for now
    };

    return { success: true, data: transformedData };
}

async function handle_get_maps(body: any, refreshToken: string) {
    const { problem_id, solution } = body;
    
    try {
        // Use the solution object directly as decision_variables
        // It should already contain the required keys like X_1, P_1, etc.
        const requestBody = {
            problem_id: Number(problem_id),
            decision_variables: solution
        };

        const response = await api.POST('/utopia/', {
            body: requestBody,
            headers: {
                'Authorization': `Bearer ${refreshToken}`
            }
        });
        
        // Check if the response has an error
        if (response.error) {
            console.error('utopia map API error:', response.error);
            console.error('Response status:', response.response?.status);
            console.error('Response status text:', response.response?.statusText);
            throw new Error(`utopia map API error: ${response.error} (Status: ${response.response?.status})`);
        }

        if (!response.data) {
            console.error('No data received from map API');
            throw new Error('No data received from map API');
        }
        const mapData = response.data;
        // Add tooltip formatter here in the server code instead of client
        // if (mapData.options && mapData.years) {
        //     for (let year of mapData.years) {
        //         if (mapData.options[year] && mapData.options[year].tooltip) {
        //             // Note: we can't add functions via JSON, so we'll handle this on the client side
        //             mapData.options[year].tooltip.formatterEnabled = true;
        //         }
        //     }
        // }

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