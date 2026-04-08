import type { RequestHandler } from './$types';

const API_BASE_URL = process.env.API_BASE_URL ?? 'http://localhost:8000';

const handler: RequestHandler = async ({ request, params, fetch }) => {
	const path = params.path;
	const search = new URL(request.url).search;
	const upstreamUrl = `${API_BASE_URL}/${path}${search}`;

	const headers = new Headers(request.headers);
	headers.delete('host');

	const upstreamRequest = new Request(upstreamUrl, {
		method: request.method,
		headers,
		body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
		// @ts-expect-error — duplex is required for streaming bodies in Node 18+
		duplex: 'half',
	});

	// Use event.fetch (not global fetch) so handleFetch intercepts for 401/refresh
	const response = await fetch(upstreamRequest);

	// Forward response headers so getBody can detect content-type correctly
	const responseHeaders = new Headers(response.headers);
	responseHeaders.delete('set-cookie'); // SvelteKit manages cookies separately

	return new Response(response.body, {
		status: response.status,
		headers: responseHeaders,
	});
};

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
