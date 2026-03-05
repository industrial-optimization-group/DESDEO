import type { PageLoad } from './$types';
import { api } from '$lib/api/client';

export const load: PageLoad = async () => {
	const res = await api.GET('/problem/all_info');

	if (!res.data) {
		throw new Error('Failed to fetch problems');
	}

	return {
		problemList: res.data
	};
};