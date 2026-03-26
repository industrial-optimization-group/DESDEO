import type { PageLoad } from './$types';
import { getProblemsProblemAllGet } from '$lib/gen/endpoints/DESDEOFastAPI';
import type { ProblemInfoSmall } from '$lib/gen/models';

export const load: PageLoad = async ({url}) => {
	const res = await getProblemsProblemAllGet();
	if (res.status !== 200) throw new Error('Failed to fetch problems');

	// Check if we have a group ID parameter, for selecting a method for GDM
    const groupId = url.searchParams.get('group');
    if (groupId) {
        return {
            problems: res.data,
            groupId: groupId,
        };
    }

    // Regular single-user mode
	return { problems: res.data satisfies ProblemInfoSmall[] };
};
