// NOTE: Supports cases where `content-type` is other than `json`
const getBody = async <T>(c: Response | Request): Promise<T> => {
  // If it's a Response and there is explicitly no content, don't parse anything
  if (c instanceof Response && (c.status === 204 || c.status === 205)) {
    return null as T;
  }

  const contentType = c.headers.get('content-type');

  if (contentType && contentType.includes('application/json')) {
    // Avoid JSON.parse errors on empty bodies
    const text = await (c as Response).text?.() ?? '';
    if (!text) return null as T;
    return JSON.parse(text) as T;
  }

  if (contentType && contentType.includes('application/pdf')) {
    return (c as Response).blob() as Promise<T>;
  }

  return (c as Response).text() as Promise<T>;
};

const getUrl = (contextUrl: string): string => {
  const url = new URL(contextUrl);
  const pathname = url.pathname;
  const search = url.search;

  const base =
    typeof process !== 'undefined' && process.env?.API_BASE_URL
      ? process.env.API_BASE_URL
      : (import.meta.env.VITE_API_URL ?? 'http://localhost:8000');

  // base may be a relative path (e.g. '/api' in local dev via Vite proxy)
  // in that case, fall back to localhost as the origin
  const absoluteBase = base.startsWith('http') ? base : `http://localhost:8000`;

  return new URL(`${absoluteBase}${pathname}${search}`).toString();
};

const getHeaders = (headers?: HeadersInit): HeadersInit => {
  return {
    ...headers,
    // add headers if needed
  }
};

export const customFetch = async <T>(
  url: string,
  options: (RequestInit & {fetchImpl?: typeof fetch }),
): Promise<T> => {
  const f = options.fetchImpl ?? fetch;

  const requestUrl = getUrl(url);
  const requestHeaders = getHeaders(options.headers);

  const requestInit: RequestInit = {
    ...options,
    headers: requestHeaders,
    credentials: "include",
  };

  const request = new Request(requestUrl, requestInit);
  const retryRequest = request.clone();

  let response = await f(request);

  if (response.status === 401) {
    const refreshUrl = new URL("/refresh", requestUrl).toString();
    const refreshResponse = await f(refreshUrl, {
      method: "POST",
      credentials: "include",
    });

    if (refreshResponse.ok) {
      response = await f(retryRequest);
    }
  }

  const data = await getBody<T>(response);

  return { status: response.status, data, headers: response.headers } as T;
};
