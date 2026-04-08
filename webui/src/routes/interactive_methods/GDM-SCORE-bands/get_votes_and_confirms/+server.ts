/**
 * Server-side API endpoint for GDM-SCORE-bands get votes and confirmations.
 *
 * Route: POST /interactive_methods/GDM-SCORE-bands/get_votes_and_confirms
 *
 * Author: Stina Palomäki
 * Created: December 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { getVotesAndConfirmsGdmScoreBandsGetVotesAndConfirmsPost } from '$lib/gen/endpoints/DESDEOFastAPI';

export const POST: RequestHandler = async ({ request, cookies }) => {
	const refreshToken = cookies.get('refresh_token');
	if (!refreshToken) {
		return json({ error: 'Not authenticated' }, { status: 401 });
	}

	try {
		const { group_id } = await request.json();

		const options: RequestInit = {
			headers: { Authorization: `Bearer ${refreshToken}` }
		};

		const votesResponse = await getVotesAndConfirmsGdmScoreBandsGetVotesAndConfirmsPost(
			{ group_id },
			options
		);

		if (votesResponse.status !== 200) {
			console.error('get-votes-and-confirms error:', votesResponse.data);
			return json(
				{
					error: 'Failed to fetch votes and confirmations',
					details: (votesResponse.data as any)?.detail || 'get-votes-and-confirms failed',
					status: votesResponse.status
				},
				{ status: votesResponse.status }
			);
		}

		return json({
			success: true,
			data: votesResponse.data
		});
	} catch (error) {
		const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
		const errorName = error instanceof Error ? error.name : 'Error';

		console.error('get-votes-and-confirms error details:', {
			message: errorMessage,
			name: errorName
		});

		return json(
			{ error: 'Server error', details: errorMessage, type: errorName },
			{ status: 500 }
		);
	}
};
