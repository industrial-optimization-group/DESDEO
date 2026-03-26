import type { PageLoad } from '../../$types';
import {
	getGroupInfoGdmGetGroupInfoPost,
	getProblemProblemProblemIdGet
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';

type LoadData = {
	refreshToken?: string;
};

type Problem = ProblemInfo;

export const load: PageLoad<LoadData> = async ({ url, data }) => {
	const groupId = url.searchParams.get('group');
	if (!groupId) throw new Error('No group ID provided');

	const group = await getGroupInfoGdmGetGroupInfoPost({ group_id: parseInt(groupId) });
	if (group.status !== 200) throw new Error('Failed to fetch group info');
	const problemId = group.data.problem_id;

	const resProblem = await getProblemProblemProblemIdGet(problemId);
	if (resProblem.status !== 200) throw new Error('Failed to fetch problem info');

	return {
		problem: resProblem.data as Problem,
		refreshToken: data?.refreshToken,
		group: group.data
	};
};
