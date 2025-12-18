/**
 * Server-side API endpoint for GDM SCORE Bands data fetching.
 * This endpoint acts as a proxy between the frontend and the backend DESDEO API.
 *
 * Route: POST /interactive_methods/GDM-SCORE-bands/fetch_score_bands
 *
 * Purpose:
 * - Calls fetch-score-bands endpoint to get current SCORE bands data and history
 * - Returns the complete SCORE bands results including visualization data
 * - Handles both consensus reaching and decision phase data
 *
 * Author: Stina Palomäki
 * Created: December 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import type { components } from '$lib/api/client-types';

/**
 * POST handler for GDM SCORE Bands fetch requests
 *
 * Expected request body: { group_id: number, score_bands_config: SCOREBandsConfig, from_iteration?: number }
 *
 * Returns: JSON response with SCORE bands data, history, and current phase information
 */
export const POST: RequestHandler = async ({ request, cookies }) => {
	const refreshToken = cookies.get('refresh_token');
	if (!refreshToken) {
		return json({ error: 'Not authenticated' }, { status: 401 });
	}

	try {
		// Parse the incoming request from the frontend
		const requestData = await request.json();

		// Call fetch_score endpoint using the authenticated API client
		const { group_id, score_bands_config, from_iteration } = requestData;
		const scoreBandRequest: components['schemas']['GDMScoreBandsInitializationRequest'] = {
			group_id,
			score_bands_config: {
				from_iteration,
				score_bands_config,
				minimum_votes: 1
			}
		};

		const scoreResponse = await api.POST('/gdm-score-bands/get-or-initialize', {
			body: scoreBandRequest,
			headers: {
				Authorization: `Bearer ${refreshToken}`, // Authenticate with refresh token
				'Content-Type': 'application/json'
			}
		});

		if (!scoreResponse.data) {
			console.error('get_or_initialize error:', scoreResponse.error);
			return json(
				{
					error: 'Failed to fetch score bands',
					details: scoreResponse.error?.detail || 'get_or_initialize failed',
					status: scoreResponse.response?.status || 500
				},
				{ status: scoreResponse.response?.status || 500 }
			);
		}

		const scoreData = scoreResponse.data;

		return json({
			success: true,
			data: scoreData
		});
	} catch (error) {
		const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
		const errorName = error instanceof Error ? error.name : 'Error';
		const errorStack = error instanceof Error ? error.stack : undefined;

		console.error('get_or_initialize error details:', {
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
 * 1. Frontend sends POST request to /interactive_methods/GDM-SCORE-bands/fetch_score_bands
 * 2. Server calls get_or_initialize endpoint to get score bands data from completed iteration
 * 3. Server returns score bands response to frontend
 */
