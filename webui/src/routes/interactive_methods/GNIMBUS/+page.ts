import type { PageLoad } from '../../$types';
import { api } from '$lib/api/client';
import type { components } from '$lib/api/client-types';

type LoadData = {
	refreshToken?: string;
};

type Problem = components['schemas']['ProblemInfo'];

export const load: PageLoad<LoadData> = async ({ url, data }) => {
	const groupId = url.searchParams.get('group');
	if (!groupId) throw new Error('No group ID provided');

	const group = await api.POST('/gdm/get_group_info', { body: { group_id: parseInt(groupId) } });
	if (!group.data) throw new Error('Failed to fetch group info');
	const problemId = group.data.problem_id;
	const resProblem = await api.POST(`/problem/get`, {
		body: { problem_id: problemId },
		headers: {
			Authorization: `Bearer ${data.refreshToken}`
		}
	});
	return {
		problem: resProblem.data as Problem,
		refreshToken: data.refreshToken,
		group: group.data
	};
};
