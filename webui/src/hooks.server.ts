import type { HandleFetch } from '@sveltejs/kit';

const API = process.env.API_BASE_URL ?? '/';

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
  // TODO: check that the request originates from our app, instead of being a third party
  const res = await fetch(request);

  // No auth errors, assuming either ok or other errors, pass the response back.
  if (res.status !== 401) return res;

  // 401, try refreshing the access token ONCE and then try again with the original request.
  return res;
};