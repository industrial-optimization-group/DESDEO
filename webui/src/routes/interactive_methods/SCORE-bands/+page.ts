import type { PageLoad } from './$types';
import { api } from '$lib/api/client';
import type { components } from '$lib/api/client-types';

type ProblemList = components['schemas']['ProblemInfo'][];

export const load: PageLoad = async () => {
	const res = await api.GET('/problem/all_info');
	if (!res.data) throw new Error('Failed to fetch problems');
	return { problems: res.data satisfies ProblemList };
};
