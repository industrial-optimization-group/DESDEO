import type { HandleFetch } from '@sveltejs/kit';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
  // For SSR requests, ensure cookies are forwarded
  // The fetch function in hooks automatically includes cookies, but we need to handle 401 refresh
  
  let res = await fetch(request);

  // If the request succeeds or it's not a 401, return immediately
  if (res.status !== 401) {
    return res;
  }

  // 401 Unauthorized - try to refresh the token
  const refreshToken = event.cookies.get('refresh_token');
  
  if (!refreshToken) {
    // No refresh token available, return the original 401
    return res;
  }

  // Try to refresh with the refresh token cookie
  const refreshRes = await fetch(`${API_BASE_URL}/refresh`, {
    method: 'POST',
    headers: {
      'Cookie': `refresh_token=${refreshToken}`
    }
  });

  if (!refreshRes.ok) {
    return res;
  }

  const { access_token } = await refreshRes.json();
  event.cookies.set("access_token", access_token, { 
    httpOnly: true, 
    secure: true, 
    sameSite: "lax", 
    path: '/' 
  });

  // Retry the original request with the new token
  const retryRequest = request.clone();
  retryRequest.headers.set('Authorization', `Bearer ${access_token}`);
  res = await fetch(retryRequest);

  return res;
};
