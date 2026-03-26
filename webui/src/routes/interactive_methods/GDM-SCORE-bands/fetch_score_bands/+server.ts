/**
 * Server-side API endpoint for GDM SCORE Bands data fetching.
 *
 * Route: POST /interactive_methods/GDM-SCORE-bands/fetch_score_bands
 *
 * Author: Stina Palomäki
 * Created: December 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { getOrInitializeGdmScoreBandsGetOrInitializePost } from '$lib/gen/endpoints/DESDEOFastAPI';
import type { GDMScoreBandsInitializationRequest } from '$lib/gen/endpoints/DESDEOFastAPI';

export const POST: RequestHandler = async ({ request, cookies }) => {
	const refreshToken = cookies.get('refresh_token');
	if (!refreshToken) {
		return json({ error: 'Not authenticated' }, { status: 401 });
	}

	try {
		const requestData = await request.json();
		const { group_id, score_bands_config, from_iteration } = requestData;

		const scoreBandRequest: GDMScoreBandsInitializationRequest = {
			group_id,
			score_bands_config: {
				from_iteration,
				score_bands_config,
				minimum_votes: 1
			}
		};

		const options: RequestInit = {
			headers: { Authorization: `Bearer ${refreshToken}` }
		};

		const scoreResponse = await getOrInitializeGdmScoreBandsGetOrInitializePost(
			scoreBandRequest,
			options
		);

		if (scoreResponse.status !== 200) {
			console.error('get_or_initialize error:', scoreResponse.data);
			return json(
				{
					error: 'Failed to fetch score bands',
					details: (scoreResponse.data as any)?.detail || 'get_or_initialize failed',
					status: scoreResponse.status
				},
				{ status: scoreResponse.status }
			);
		}

		return json({
			success: true,
			data: scoreResponse.data
		});
	} catch (error) {
		const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
		const errorName = error instanceof Error ? error.name : 'Error';

		console.error('get_or_initialize error details:', {
			message: errorMessage,
			name: errorName
		});

		return json(
			{ error: 'Server error', details: errorMessage, type: errorName },
			{ status: 500 }
		);
	}
};
