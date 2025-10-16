// NOTE: Supports cases where `content-type` is other than `json`
const getBody = <T>(c: Response | Request): Promise<T> => {
  const contentType = c.headers.get('content-type');

  if (contentType && contentType.includes('application/json')) {
    return c.json();
  }

  if (contentType && contentType.includes('application/pdf')) {
    return c.blob() as Promise<T>;
  }

  return c.text() as Promise<T>;
};

// NOTE: Update just base url
const getUrl = (contextUrl: string): string => {
  const url = new URL(contextUrl);
  const origin = url.origin;
  const pathname = url.pathname;
  const search = url.search;

  const requestUrl = new URL(`${origin}${pathname}${search}`);

  return requestUrl.toString();
};

// NOTE: Add headers
const getHeaders = (headers?: HeadersInit): HeadersInit => {
  // TODO: check that access token has not expired, refresh it if needed
  // remember to include credentials!

  const base =
    headers instanceof Headers
        ? Object.fromEntries(headers.entries())
        : Array.isArray(headers)
            ? Object.fromEntries(headers)
            : { ...(headers ?? {}) };

  // If Authorization already present, keep it; otherwise use token

  return base;
};

export const customFetch = async <T>(
  url: string,
  options: RequestInit,
): Promise<T> => {
  console.log(options);
  const requestUrl = getUrl(url);
  const requestHeaders = getHeaders(options.headers);

  const requestInit: RequestInit = {
    ...options,
    headers: requestHeaders,
  };

  const response = await fetch(requestUrl, requestInit);
  const data = await getBody<T>(response);

  return { status: response.status, data, headers: response.headers } as T;
};
