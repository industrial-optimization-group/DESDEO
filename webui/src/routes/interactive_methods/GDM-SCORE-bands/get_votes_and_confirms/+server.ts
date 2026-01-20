/**
 * Server-side API endpoint for GDM-SCORE-bands get votes and confirmations.
 * This endpoint acts as a proxy between the frontend and the backend DESDEO API.
 *
 * Route: POST /interactive_methods/GDM-SCORE-bands/get_votes_and_confirms
 *
 * Purpose:
 * - Calls get-votes-and-confirms endpoint to get current voting status and confirmations
 * - Returns the current state of votes and confirmations for the group iteration
 *
 * Author: Stina Palomäki
 * Created: December 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import type { components } from '$lib/api/client-types';

/**
 * POST handler for GDM-SCORE-bands get votes and confirmations requests
 *
 * Expected request body: Contains group_id to identify which group's voting status to fetch
 *
 * Returns: JSON response with current votes and confirmations from the group iteration
 */
export const POST: RequestHandler = async ({ request, cookies }) => {
	const refreshToken = cookies.get('refresh_token');
	if (!refreshToken) {
		return json({ error: 'Not authenticated' }, { status: 401 });
	}

	try {
		// Parse the incoming request from the frontend
		const requestData = await request.json();

		// Call get-votes-and-confirms endpoint using the authenticated API client
		const { group_id } = requestData;
		const getVotesRequest = { group_id };

		const votesResponse = await api.POST('/gdm-score-bands/get-votes-and-confirms', {
			body: getVotesRequest,
			headers: {
				Authorization: `Bearer ${refreshToken}`, // Authenticate with refresh token
				'Content-Type': 'application/json'
			}
		});

		if (!votesResponse.data) {
			console.error('get-votes-and-confirms error:', votesResponse.error);
			return json(
				{
					error: 'Failed to fetch votes and confirmations',
					details: votesResponse.error?.detail || 'get-votes-and-confirms failed',
					status: votesResponse.response?.status || 500
				},
				{ status: votesResponse.response?.status || 500 }
			);
		}

		const votesData = votesResponse.data;

		return json({
			success: true,
			data: votesData
		});
	} catch (error) {
		const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
		const errorName = error instanceof Error ? error.name : 'Error';
		const errorStack = error instanceof Error ? error.stack : undefined;

		console.error('get-votes-and-confirms error details:', {
			message: errorMessage,
			stack: errorStack,
			name: errorName
		});

		return json(
			{
				error: 'Server error',
				details: errorMessage,
				type: errorName
			},
			{ status: 500 }
		);
	}
};

/**
 * Flow Summary:
 * 1. Frontend sends POST request to /interactive_methods/GDM-SCORE-bands/get_votes_and_confirms
 * 2. Server calls get-votes-and-confirms endpoint to get current voting status and confirmations
 * 3. Server returns votes and confirmations response to frontend
 *
 * Response format:
 * {
 *   "votes": { "user_id": vote_index, ... },
 *   "confirms": [user_id, user_id, ...]
 * }
 */
