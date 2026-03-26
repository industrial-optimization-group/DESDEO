/**
 * Server-side API endpoint for GDM SCORE Bands configuration.
 *
 * Route: POST /interactive_methods/GDM-SCORE-bands/configure
 *
 * Author: Stina Palomäki
 * Created: December 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { configureGdmGdmScoreBandsConfigurePost } from '$lib/gen/endpoints/DESDEOFastAPI';

export const POST: RequestHandler = async ({ request, cookies }) => {
	const refreshToken = cookies.get('refresh_token');
	if (!refreshToken) {
		return json({ error: 'Not authenticated' }, { status: 401 });
	}

	try {
		const requestData = await request.json();
		const { group_id, config } = requestData;

		if (typeof group_id !== 'number') {
			return json(
				{ error: 'Invalid request', details: 'group_id must be a number' },
				{ status: 400 }
			);
		}

		if (!config) {
			return json(
				{ error: 'Invalid request', details: 'config is required' },
				{ status: 400 }
			);
		}

		const options: RequestInit = {
			headers: { Authorization: `Bearer ${refreshToken}` }
		};

		const configureResponse = await configureGdmGdmScoreBandsConfigurePost(
			config,
			{ group_id },
			options
		);

		if (configureResponse.status !== 200) {
			console.error('Configure error:', configureResponse.data);
			return json(
				{
					error: 'Failed to configure SCORE bands',
					details: (configureResponse.data as any)?.detail || 'Configuration failed',
					status: configureResponse.status
				},
				{ status: configureResponse.status }
			);
		}

		return json({
			success: true,
			data: { message: 'Successfully configured SCORE bands settings' }
		});
	} catch (error) {
		const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
		const errorName = error instanceof Error ? error.name : 'Error';

		console.error('Configure error details:', { message: errorMessage, name: errorName });

		return json(
			{ error: 'Server error', details: errorMessage, type: errorName },
			{ status: 500 }
		);
	}
};
