import type { HandleFetch } from '@sveltejs/kit';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
  // TODO: check that the request originates from our app, instead of being a third party
  let res = await fetch(request);

  // No auth errors, assuming either ok or other errors, pass the response back.
  if (res.status !== 401) return res;

  // 401, try refreshing the access token ONCE and then try again with the original request.
  const refreshRes = await fetch(`${API_BASE_URL}/refresh`, {
    method: 'POST',
    credentials: 'include'  // sends cookies
  });

  if (!refreshRes.ok) {
    return res;
  }

  const { access_token } = await refreshRes.json();
  event.cookies.set("access_token", access_token, { httpOnly: true, secure: true, sameSite: "lax", path: '/' });

  // try again with new access cookie
  res = await fetch(request);

  return res;
};
