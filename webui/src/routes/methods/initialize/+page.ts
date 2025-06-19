import type { PageLoad } from './$types';
import { api } from '$lib/api/client';
import type { FetchReturnType } from 'openapi-typescript-fetch';
import type { paths } from '$lib/api/client-types';

type ProblemList = FetchReturnType<paths['/problem/all']['get']>;

export const load: PageLoad = async () => {
	const res = await api.GET('/problem/all');
	if (!res.data) throw new Error('Failed to fetch problems');
	return { problems: res.data satisfies ProblemList };
};