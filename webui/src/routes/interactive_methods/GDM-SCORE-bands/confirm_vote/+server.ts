/**
 * Server-side API endpoint for GDM SCORE Bands vote confirmation.
 *
 * Route: POST /interactive_methods/GDM-SCORE-bands/confirm_vote
 *
 * Author: Stina Palomäki
 * Created: December 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { confirmVoteGdmScoreBandsConfirmPost } from '$lib/gen/endpoints/DESDEOFastAPI';

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

		const response = await confirmVoteGdmScoreBandsConfirmPost({ group_id }, options);

		if (response.status !== 200) {
			console.error('Confirm error:', { status: response.status, data: response.data });

			return json(
				{
					error: 'Failed to confirm',
					details: (response.data as any)?.detail || 'No data returned from API',
					status: response.status
				},
				{ status: response.status }
			);
		}

		console.log('confirm response:', response.data);

		return json({
			success: true,
			data: response.data,
			message: 'confirm completed successfully'
		});
	} catch (error) {
		const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
		const errorName = error instanceof Error ? error.name : 'Error';

		console.error('voting error details:', { message: errorMessage, name: errorName });

		return json(
			{ error: 'Server error', details: errorMessage, type: errorName },
			{ status: 500 }
		);
	}
};
