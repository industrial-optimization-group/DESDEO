import type { PageLoad } from './$types';
import { api } from '$lib/api/client';

export const load: PageLoad = async ({ url, data }) => {
	// Fetch user's problems
	const problemsRes = await api.GET('/problem/all_info');

	if (!problemsRes.data || problemsRes.data.length === 0) {
		return {
			solutions: null,
			error: 'No problems found for the current user'
		};
	}

	// Get the first problem from the list
	const firstProblem = problemsRes.data[0];
	const problemId = firstProblem.id;

	try {
		const res = await api.GET('/method/generic/final-solutions/{problem_id}', {
			params: {
				path: {
					problem_id: problemId
				}
			}
		});

		if (!res.data) {
			return {
				solutions: null,
				error: 'Failed to fetch solutions'
			};
		}

		return {
			solutions: res.data,
			problemInfo: firstProblem
		};
	} catch (error) {
		return {
			solutions: null,
			error: `Error fetching solutions: ${error}`
		};
	}
};
