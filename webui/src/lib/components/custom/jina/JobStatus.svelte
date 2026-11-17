<script lang="ts">
	/**
	 * Polls a JINA state until its background job has finished.
	 *
	 * Calls `onDone` with the state once it is ready, also when it failed; a failure stays shown
	 * with its error until dismissed. A 401, 403 or 404 response stops polling and is shown; network
	 * errors and other error responses are retried with backoff.
	 */
	import { onDestroy } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import {
		getStatusMethodJinaStatusStateIdGet,
		type JinaStateResponse
	} from '$lib/gen/endpoints/DESDEOFastAPI';
	import { errorDetail } from './labels';

	let {
		stateId,
		label,
		interval = 1500,
		maxInterval = 30000,
		onDone,
		onDismiss
	}: {
		stateId: number;
		label: string;
		interval?: number;
		maxInterval?: number;
		onDone: (state: JinaStateResponse) => void;
		onDismiss?: () => void;
	} = $props();

	let error = $state<string | null>(null);
	let retrying = $state(false);
	let timer: ReturnType<typeof setTimeout> | undefined;
	let stopped = false;

	async function poll(id: number, failures: number) {
		let failed = false;
		try {
			const response = await getStatusMethodJinaStatusStateIdGet(id);
			if (stopped || id !== stateId) return;
			const status = response.status as number;
			if (status === 200) {
				const state = response.data as JinaStateResponse;
				if (state.is_ready) {
					error = state.error ?? null;
					onDone(state);
					return;
				}
			} else if (status === 401 || status === 403 || status === 404) {
				error = errorDetail(status, response.data);
				return;
			} else {
				failed = true;
			}
		} catch {
			if (stopped || id !== stateId) return;
			failed = true;
		}
		failures = failed ? failures + 1 : 0;
		retrying = failed;
		const next = failed ? Math.min(interval * 2 ** failures, maxInterval) : interval;
		timer = setTimeout(() => void poll(id, failures), next);
	}

	$effect(() => {
		error = null;
		retrying = false;
		clearTimeout(timer);
		void poll(stateId, 0);
	});

	onDestroy(() => {
		stopped = true;
		clearTimeout(timer);
	});
</script>

{#if error}
	<div
		class="flex items-start gap-2 rounded border border-red-300 bg-red-50 p-2 text-sm text-red-800"
		role="alert"
	>
		<span class="flex-1"><span class="font-semibold">{label} failed:</span> {error}</span>
		{#if onDismiss}
			<Button variant="ghost" size="sm" class="h-6 px-2" onclick={onDismiss}>Dismiss</Button>
		{/if}
	</div>
{:else}
	<div class="flex items-center gap-2 text-sm text-gray-600" role="status">
		<span class="size-3 animate-spin rounded-full border-2 border-gray-300 border-t-gray-700"
		></span>
		{label}…
		{#if retrying}<span class="text-xs text-amber-700">(connection problem, retrying)</span>{/if}
	</div>
{/if}
