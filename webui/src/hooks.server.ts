import type { HandleFetch } from '@sveltejs/kit';
import { refreshAccessTokenRefreshPost } from '$lib/gen/endpoints/DESDEOFastAPI';

// const API = process.env.API_BASE_URL ?? '/';

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
  // TODO: check that the request originates from our app, instead of being a third party
  const originalRequest = request.clone();
  let res = await fetch(request);

  // No auth errors, assuming either ok or other errors, pass the response back.
  if (res.status !== 401) return res;

  // 401, try refreshing the access token ONCE and then try again with the original request.

  const refreshToken = event.cookies.get("refresh_token");

  if (!refreshToken) return res;

  const response_with_new_cookies = await refreshAccessTokenRefreshPost({
    fetchImpl: fetch,
    headers: {
      cookie: `refresh_token=${refreshToken}`,
    },
  } as RequestInit);

  if (response_with_new_cookies.status != 200 || !response_with_new_cookies.data?.access_token) return res;

  // access ok!
  event.cookies.set("access_token", response_with_new_cookies.data.access_token, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
  });

  const cookieHeader = event.cookies
    .getAll()
    .map(({ name, value }) => `${name}=${value}`)
    .join("; ");

  // try again with new access cookie
  const retryRequest = new Request(originalRequest, {
    headers: new Headers({
      ...Object.fromEntries(request.headers.entries()),
      cookie: cookieHeader,
    }),
  });
  res = await fetch(retryRequest);

  return res;
};
