import type { PageLoad } from './$types';
import {
	getCurrentUserInfoUserInfoGet,
	getGroupInfoGdmGetGroupInfoPost,
	getProblemProblemProblemIdGet
} from '$lib/gen/endpoints/DESDEOFastAPI';

export const load: PageLoad = async () => {
	const user = await getCurrentUserInfoUserInfoGet();
	if (user.status !== 200) {
		throw new Error('Failed to fetch user info');
	}

	const groupIds = user.data.group_ids;
	if (!groupIds || groupIds.length === 0) {
		return { problemList: [], groupList: [] };
	}

	let groupList = [];
	for (const id of groupIds) {
		const info = await getGroupInfoGdmGetGroupInfoPost({ group_id: id });
		if (info.status !== 200) {
			throw new Error(`Failed to fetch group info for group ID ${id}`);
		}
		groupList.push(info.data);
	}

	let problemList = [];
	for (const group of groupList) {
		const problem = await getProblemProblemProblemIdGet(group.problem_id);
		if (problem.status !== 200) {
			throw new Error(`Failed to fetch problem info for problem ID ${group.problem_id}`);
		}
		problemList.push(problem.data);
	}

	return {
		problemList,
		groupList
	};
};
