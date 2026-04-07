import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { getCurrentUserInfoUserInfoGet } from '$lib/gen/endpoints/DESDEOFastAPI';

export const load: PageServerLoad = async ({ cookies }) => {
    const refreshToken = cookies.get('refresh_token');
    if (!refreshToken) {
        return redirect(307, '/home');
    }

    const accessToken = cookies.get('access_token');
    const response = await getCurrentUserInfoUserInfoGet({
        headers: { Authorization: `Bearer ${accessToken}` },
    });

    if (response.status !== 200) {
        return redirect(307, '/home');
    }

    const role = response.data.role;
    if (role !== 'analyst' && role !== 'admin') {
        return redirect(307, '/dashboard');
    }

    return {};
};
