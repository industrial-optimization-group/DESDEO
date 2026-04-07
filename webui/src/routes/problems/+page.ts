import type { PageLoad } from './$types';
import { getDmUsersUsersDmsGet, getProblemsInfoProblemAllInfoGet } from '$lib/gen/endpoints/DESDEOFastAPI';
import type { UserPublic } from '$lib/gen/endpoints/DESDEOFastAPI';

export const load: PageLoad = async () => {
	const [problemsRes, dmsRes] = await Promise.all([
		getProblemsInfoProblemAllInfoGet(),
		getDmUsersUsersDmsGet().catch(() => null)
	]);

	if (problemsRes.status !== 200) {
		throw new Error('Failed to fetch problems');
	}

	const dmUsers: UserPublic[] = dmsRes?.status === 200 ? (dmsRes.data as UserPublic[]) : [];

	return {
		problemList: problemsRes.data,
		dmUsers
	};
};
