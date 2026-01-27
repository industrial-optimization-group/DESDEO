<script lang="ts">
	import { onMount } from 'svelte';
	import { isLoading, errorMessage } from '../../../stores/uiState';
	import type { InteractiveSessionBase } from '$lib/gen/models';

	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';

	import { create_session, delete_session, fetch_sessions } from './handler';

	let sessions = $state<InteractiveSessionBase[]>([]);
	let newInfo = $state<string>('');
	let deletingId = $state<number | null>(null);

	async function refresh() {
		try {
			isLoading.set(true);
			errorMessage.set(null);

			const data = await fetch_sessions();
			sessions = data ?? [];
		} catch (err) {
			console.error('Failed to fetch sessions', err);
			errorMessage.set('Failed to fetch sessions.');
		} finally {
			isLoading.set(false);
		}
	}

	async function handleCreate() {
		try {
			isLoading.set(true);
			errorMessage.set(null);

			const trimmed = newInfo.trim();
			const created = await create_session(trimmed.length > 0 ? trimmed : null);

			if (!created) {
				errorMessage.set('Failed to create session.');
				return;
			}

			newInfo = '';
			await refresh();
		} catch (err) {
			console.error('Failed to create session', err);
			errorMessage.set('Failed to create session.');
		} finally {
			isLoading.set(false);
		}
	}

	async function handleDelete(sessionId: number | null) {
		try {
            if (sessionId === null) return;
			deletingId = sessionId;
			isLoading.set(true);
			errorMessage.set(null);

			const ok = await delete_session(sessionId);
			if (!ok) {
				errorMessage.set('Failed to delete session.');
				return;
			}

			await refresh();
		} catch (err) {
			console.error('Failed to delete session', err);
			errorMessage.set('Failed to delete session.');
		} finally {
			deletingId = null;
			isLoading.set(false);
		}
	}

	onMount(() => {
		refresh();
	});
</script>

<div class="container mx-auto px-4 py-8">
	<div class="mb-8 space-y-4">
		<div class="flex items-center justify-between">
			<div class="space-y-1">
				<h1 class="text-3xl font-bold tracking-tight">Interactive Sessions</h1>
				<p class="text-muted-foreground text-sm">
					Sessions group interactive method states into a single decision process.
				</p>
			</div>
			<Button variant="outline" size="sm" onclick={refresh}>
				<RefreshCw class="mr-2 size-4" />
				Refresh
			</Button>
		</div>
	</div>

	<Card.Root class="mb-8">
		<Card.Header>
			<Card.Title>Create a new session</Card.Title>
			<Card.Description>
				Optional info/label.
			</Card.Description>
		</Card.Header>
		<Card.Content>
			<form class="flex flex-col gap-3 sm:flex-row sm:items-center" onsubmit={handleCreate}>
				<input
					class="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2"
					placeholder="Session info (optional)"
					bind:value={newInfo}
				/>
				<Button type="submit">Create session</Button>
			</form>
		</Card.Content>
	</Card.Root>

	<Card.Root>
		<Card.Header>
			<Card.Title>Existing sessions</Card.Title>
			<Card.Description>
				These are your current interactive sessions. Deleting a session deletes the session and its related states.
			</Card.Description>
		</Card.Header>
		<Card.Content>
			{#if sessions.length === 0}
				<div class="text-muted-foreground text-sm">No sessions found. Create one above.</div>
			{:else}
				<Table.Root>
					<Table.Header>
						<Table.Row>
							<Table.Head class="w-[120px]">ID</Table.Head>
							<Table.Head>Info</Table.Head>
							<Table.Head class="w-[140px] text-right">Actions</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#each sessions as s (s.id)}
							<Table.Row>
								<Table.Cell class="font-mono text-sm">{s.id}</Table.Cell>
								<Table.Cell class="max-w-[720px] truncate">{s.info ?? '—'}</Table.Cell>
								<Table.Cell class="text-right">
									<Button
										variant="ghost"
										size="icon"
										disabled={deletingId === s.id}
										onclick={() => handleDelete(s.id)}
										title="Delete session"
									>
										<Trash2 class="size-4" />
									</Button>
								</Table.Cell>
							</Table.Row>
						{/each}
					</Table.Body>
				</Table.Root>
			{/if}
		</Card.Content>
	</Card.Root>
</div>
