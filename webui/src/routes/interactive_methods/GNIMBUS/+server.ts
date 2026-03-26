/**
 * +server.ts - GNIMBUS API Server Endpoint
 *
 * @author Stina Palomäki <palomakistina@gmail.com>
 * @created September 2025
 * @updated November 2025
 *
 * @description
 * This server endpoint handles all Group NIMBUS method API requests, acting as a proxy
 * between the frontend and the backend API.
 *
 * @authentication
 * All endpoints require authentication via refresh_token cookie.
 */
import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import {
	gnimbusInitializeGnimbusInitializePost,
	getLatestResultsGnimbusGetLatestResultsPost,
	fullIterationGnimbusAllIterationsPost,
	switchPhaseGnimbusTogglePhasePost,
	revertIterationGnimbusRevertIterationPost,
	getPhaseGnimbusGetPhasePost,
	getUtopiaDataUtopiaPost
} from '$lib/gen/endpoints/DESDEOFastAPI';

type ApiResult = { success: true; data: any } | { success: false; error: string; status?: number };

async function callApi(
	fn: () => Promise<{ status: number; data: any }>,
	label: string
): Promise<ApiResult> {
	try {
		const response = await fn();
		if (response.status !== 200) {
			const detail = (response.data as any)?.detail || 'Failed to process request';
			console.error(`API error on ${label}: ${response.status} ${detail}`);
			return { success: false, error: detail, status: response.status };
		}
		return { success: true, data: response.data };
	} catch (error) {
		const errorMessage =
			error instanceof Error ? error.message : `Unknown error on ${label}`;
		console.error(`Caught exception on ${label}:`, errorMessage);
		return { success: false, error: errorMessage, status: 500 };
	}
}

type HandlerFunction = (body: any, options: RequestInit) => Promise<ApiResult>;

const handlers: Record<string, HandlerFunction> = {
	initialize: (body, options) => {
		const { group_id } = body;
		return callApi(
			() => gnimbusInitializeGnimbusInitializePost({ group_id: Number(group_id) }, options),
			'gnimbus/initialize'
		);
	},

	get_latest_results: (body, options) => {
		const { group_id } = body;
		if (!group_id) {
			return Promise.resolve({ success: false, error: 'group_id is required' });
		}
		return callApi(
			() => getLatestResultsGnimbusGetLatestResultsPost({ group_id: Number(group_id) }, options),
			'gnimbus/get_latest_results'
		);
	},

	get_all_iterations: async (body, options) => {
		const { group_id } = body;
		const response = await callApi(
			() => fullIterationGnimbusAllIterationsPost({ group_id: Number(group_id) }, options),
			'gnimbus/all_iterations'
		);

		// Special case for not initialized error
		if (
			!response.success &&
			response.error &&
			response.error.includes('Problem has not been initialized!')
		) {
			return { success: false, error: 'not_initialized' };
		}

		return response;
	},

	switch_phase: async (body, options) => {
		const { group_id, new_phase } = body;
		const response = await callApi(
			() =>
				switchPhaseGnimbusTogglePhasePost(
					{ group_id: Number(group_id), new_phase },
					options
				),
			'gnimbus/toggle_phase'
		);

		// Special case for wrong step error
		if (!response.success && response.error && response.error.includes('400')) {
			return { success: false, error: 'wrong_step' };
		}

		return response;
	},

	revert_iteration: (body, options) => {
		const { group_id, state_id } = body;
		if (!group_id) {
			return Promise.resolve({ success: false, error: 'group_id is required' });
		}
		if (!state_id) {
			return Promise.resolve({ success: false, error: 'state_id is required' });
		}
		return callApi(
			() =>
				revertIterationGnimbusRevertIterationPost(
					{ group_id: Number(group_id), state_id: Number(state_id) },
					options
				),
			'gnimbus/revert_iteration'
		);
	},

	get_phase: (body, options) => {
		const { group_id } = body;
		return callApi(
			() => getPhaseGnimbusGetPhasePost({ group_id: Number(group_id) }, options),
			'gnimbus/get_phase'
		);
	},

	get_maps: (body, options) => {
		const { problem_id, solution } = body;
		return callApi(
			() =>
				getUtopiaDataUtopiaPost(
					{ problem_id: Number(problem_id), solution },
					undefined,
					options
				),
			'utopia'
		);
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
			const options: RequestInit = {
				headers: { Authorization: `Bearer ${refreshToken}` }
			};
			const response = await handler(body, options);
			const httpStatus = response.success ? 200 : ('status' in response ? response.status || 500 : 500);
			return json(response, { status: httpStatus });
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
