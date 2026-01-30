import { beforeEach, describe, expect, it, vi } from 'vitest';
import { handleFetch } from './hooks.server';
import { refreshAccessTokenRefreshPost } from '$lib/gen/endpoints/DESDEOFastAPI';

vi.mock('$lib/gen/endpoints/DESDEOFastAPI', () => ({
  refreshAccessTokenRefreshPost: vi.fn()
}));

const createCookieStore = (initial: Record<string, string>) => {
  const store = new Map(Object.entries(initial));

  return {
    get: (name: string) => store.get(name),
    getAll: () => Array.from(store.entries()).map(([name, value]) => ({ name, value })),
    set: (name: string, value: string) => {
      store.set(name, value);
    }
  };
};

describe('handleFetch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('refreshes the access token and retries with updated cookies', async () => {
    const cookies = createCookieStore({ refresh_token: 'refresh-123' });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { 'content-type': 'application/json' }
        })
      );

    vi.mocked(refreshAccessTokenRefreshPost).mockResolvedValue({
      status: 200,
      data: { access_token: 'new-access-token' },
      headers: new Headers()
    });

    const request = new Request('http://example.test/api/resource');
    const response = await handleFetch({
      event: { cookies } as Parameters<typeof handleFetch>[0]['event'],
      request,
      fetch: fetchMock
    } as Parameters<typeof handleFetch>[0]);

    expect(response.status).toBe(200);
    expect(refreshAccessTokenRefreshPost).toHaveBeenCalledWith(
      expect.objectContaining({
        headers: { cookie: 'refresh_token=refresh-123' }
      })
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);

    const retryRequest = fetchMock.mock.calls[1][0] as Request;
    const retryCookieHeader = retryRequest.headers.get('cookie');
    expect(retryCookieHeader).toContain('refresh_token=refresh-123');
    expect(retryCookieHeader).toContain('access_token=new-access-token');
  });

  it('returns the original response when refresh token is missing', async () => {
    const cookies = createCookieStore({});
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(null, { status: 401 }));

    const request = new Request('http://example.test/api/resource');
    const response = await handleFetch({
      event: { cookies } as Parameters<typeof handleFetch>[0]['event'],
      request,
      fetch: fetchMock
    } as Parameters<typeof handleFetch>[0]);

    expect(response.status).toBe(401);
    expect(refreshAccessTokenRefreshPost).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
