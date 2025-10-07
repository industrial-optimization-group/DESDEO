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
import type { RequestHandler } from './$types';

async function makeApiRequest(endpoint: string, body: any, refreshToken: string) {
	try {
		const response = await api.POST(endpoint as any, {
			body,
			headers: {
				Authorization: `Bearer ${refreshToken}`
			}
		});

		if (response.error || !response.data) {
			const status = response.response?.status || 'N/A';
			// The error object from the client seems to have a 'detail' property for FastAPI errors
			const detail =
				response.error.detail || response.error.toString() || 'Failed to process request';
			const errorMessage = `${status} ${detail}`;
			console.error(`API error on endpoint ${endpoint}:`, errorMessage);
			return {
				success: false,
				error: errorMessage
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
			error: errorMessage
		};
	}
}

type HandlerFunction = (body: any, refreshToken: string) => Promise<any>;

const handlers: Record<string, HandlerFunction> = {
	initialize: (body, refreshToken) => {
		const { problem_id, session_id, parent_state_id, solver } = body;
		const requestBody = {
			problem_id: Number(problem_id),
			session_id: session_id ? Number(session_id) : null,
			parent_state_id: parent_state_id ? Number(parent_state_id) : null,
			solver
		};
		return makeApiRequest('/method/nimbus/get-or-initialize', requestBody, refreshToken);
	},
	iterate: (body, refreshToken) => {
		const { problem_id, session_id, parent_state_id, current_objectives, num_desired, preference } =
			body;
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
		return makeApiRequest('/method/nimbus/solve', requestBody, refreshToken);
	},
	intermediate: (body, refreshToken) => {
		const {
			problem_id,
			session_id,
			parent_state_id,
			reference_solution_1,
			reference_solution_2,
			num_desired
		} = body;
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
		return makeApiRequest('/method/nimbus/intermediate', requestBody, refreshToken);
	},
	save: (body, refreshToken) => {
		const { problem_id, solution_info } = body;
		const requestBody = {
			problem_id,
			session_id: null,
			parent_state_id: null,
			solution_info
		};
		return makeApiRequest('/method/nimbus/save', requestBody, refreshToken);
	},
	get_maps: (body, refreshToken) => {
		const { problem_id, solution } = body;
		const requestBody = {
			problem_id: Number(problem_id),
			solution: solution
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

		if (type === 'choose') {
			return json({ success: true, message: 'solution chosen!' });
		}
		if (type === 'remove_saved') {
			return json({ success: false, error: 'solution remove not implemented!' });
		}

		const handler = handlers[type];
		if (handler) {
			const response = await handler(body, refreshToken);
			return json(response);
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
