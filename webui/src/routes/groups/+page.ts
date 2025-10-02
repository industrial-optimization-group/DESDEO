import type { PageLoad } from './$types';
import { api } from '$lib/api/client';

export const load: PageLoad = async () => {
	const user = await api.GET('/user_info');
	if (!user.data) {
		throw new Error('Failed to fetch user info');
	}

	const groupIds = user.data.group_ids;
	if (!groupIds || groupIds.length === 0) {
		return {problemList: [], groupList: []};
	}

	let groupList = [];
	for (const id of groupIds) {
		const info = await api.POST('/gdm/get_group_info', {body:{group_id: id}});
		if (!info.data) {
			throw new Error(`Failed to fetch group info for group ID ${id}`);
		}
		groupList.push(info.data);
	}

	let problemList = [];
	// for each group, get problem info by POST problem/get, giving problem_id as body
	for (const group of groupList) {
		const problem = await api.POST('/problem/get', {body:{problem_id: group.problem_id}});
		if (!problem.data) {
			throw new Error(`Failed to fetch problem info for problem ID ${group.problem_id}`);
		}
		problemList.push(problem.data);
	}


	return {
		problemList,
		groupList
	};
};