import type { PageLoad } from './$types';
import { getProblemsInfoProblemAllInfoGet } from '$lib/gen/endpoints/DESDEOFastAPI';

export const load: PageLoad = async () => {
	const res = await getProblemsInfoProblemAllInfoGet();

	if (res.status !== 200) {
		throw new Error('Failed to fetch problems');
	}

	return {
		problemList: res.data
	};
};
