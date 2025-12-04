import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ cookies }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    throw redirect(307, '/home');
  }
  return { refreshToken };
};