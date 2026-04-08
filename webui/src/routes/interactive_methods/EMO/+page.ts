import type { PageLoad } from './$types';
import { getProblemsInfoProblemAllInfoGet } from '$lib/gen/endpoints/DESDEOFastAPI';
import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';

type ProblemList = ProblemInfo[];

export const load: PageLoad = async () => {
	const res = await getProblemsInfoProblemAllInfoGet();
	if (res.status !== 200) throw new Error('Failed to fetch problems');
	return { problems: res.data satisfies ProblemList };
};
