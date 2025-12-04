import type { PageLoad } from './$types';
import { api } from '$lib/api/client';
import type { FetchReturnType } from 'openapi-typescript-fetch';
import type { paths, components } from '$lib/api/client-types';

type ProblemList = FetchReturnType<paths['/problem/all']['get']>;
type Group = components['schemas']['GroupPublic'];
type Problem = components['schemas']['ProblemInfo'];

export const load: PageLoad = async ({ url, data }) => {
	// Get all problems for the dropdown
	const res = await api.GET('/problem/all_info');
	if (!res.data) throw new Error('Failed to fetch problems');

	// Check if we have a group ID parameter (for GDM sessions)
	const groupId = url.searchParams.get('group');
	
	if (groupId) {
		// Load group-specific data for collaborative sessions
		const group = await api.POST('/gdm/get_group_info', { 
			body: { group_id: parseInt(groupId) } 
		});
		
		if (!group.data) throw new Error('Failed to fetch group info');
		
		const problemId = group.data.problem_id;
		const resProblem = await api.POST(`/problem/get`, {
			body: { problem_id: problemId },
			headers: {
				Authorization: `Bearer ${data.refreshToken}`
			}
		});
		
		return {
			problems: res.data,
			refreshToken: data.refreshToken,
			group: group.data,
			problem: resProblem.data as Problem
		};
	}

	// Regular single-user mode
	return { 
		problems: res.data,
		refreshToken: data.refreshToken
	};
};