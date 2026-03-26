/**
 * Server-side API endpoint for GDM SCORE Bands iteration reversion.
 *
 * Route: POST /interactive_methods/GDM-SCORE-bands/revert
 *
 * Author: Stina Palomäki
 * Created: December 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { revertGdmScoreBandsRevertPost } from '$lib/gen/endpoints/DESDEOFastAPI';
import type { GDMSCOREBandsRevertRequest } from '$lib/gen/models';

export const POST: RequestHandler = async ({ request, cookies }) => {
	const refreshToken = cookies.get('refresh_token');
	if (!refreshToken) {
		return json({ error: 'Not authenticated' }, { status: 401 });
	}

	try {
		const requestData = await request.json();
		const { group_id, iteration_number } = requestData;

		if (typeof group_id !== 'number' || typeof iteration_number !== 'number') {
			return json(
				{ error: 'Invalid request', details: 'group_id and iteration_number must be numbers' },
				{ status: 400 }
			);
		}

		const revertRequest: GDMSCOREBandsRevertRequest = { group_id, iteration_number };

		const options: RequestInit = {
			headers: { Authorization: `Bearer ${refreshToken}` }
		};

		const revertResponse = await revertGdmScoreBandsRevertPost(revertRequest, options);

		if (revertResponse.status !== 200) {
			console.error('Revert error:', revertResponse.data);
			return json(
				{
					error: 'Failed to revert iteration',
					details: (revertResponse.data as any)?.detail || 'Revert failed',
					status: revertResponse.status
				},
				{ status: revertResponse.status }
			);
		}

		return json({
			success: true,
			data: { message: 'Successfully reverted to previous iteration' }
		});
	} catch (error) {
		const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
		const errorName = error instanceof Error ? error.name : 'Error';

		console.error('Revert error details:', { message: errorMessage, name: errorName });

		return json(
			{ error: 'Server error', details: errorMessage, type: errorName },
			{ status: 500 }
		);
	}
};
