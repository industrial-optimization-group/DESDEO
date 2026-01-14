import type { PageLoad } from './$types';
import { api } from '$lib/api/client';
import type { FetchReturnType } from 'openapi-typescript-fetch';
import type { paths } from '$lib/api/client-types';

type ProblemList = FetchReturnType<paths['/problem/all']['get']>;

export const load: PageLoad = async ({url, data}) => {
	const res = await api.GET('/problem/all');
	if (!res.data) throw new Error('Failed to fetch problems');
	
	// Check if we have a group ID parameter, for selecting a method for GDM
    const groupId = url.searchParams.get('group');
    if (groupId) {
        return {
            problems: res.data,
            groupId: groupId,
        };
    }

    // Regular single-user mode
	return { problems: res.data satisfies ProblemList };
};