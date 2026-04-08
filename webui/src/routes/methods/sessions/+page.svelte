<script lang="ts">
	import { onMount } from 'svelte';
	import { isLoading, errorMessage } from '../../../stores/uiState';
	import type { InteractiveSessionBase, UserPublic } from '$lib/gen/endpoints/DESDEOFastAPI';
	import { getDmUsersUsersDmsGet } from '$lib/gen/endpoints/DESDEOFastAPI';

	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';

	import { goto } from '$app/navigation';
	import { methodSelection } from '../../../stores/methodSelection';
	import { auth } from '../../../stores/auth';
	import Check from '@lucide/svelte/icons/check';

	import { create_session, delete_session, fetch_sessions } from './handler';

	let sessions = $state<InteractiveSessionBase[]>([]);
	let newInfo = $state<string>('');
	let deletingId = $state<number | null>(null);
	let dms = $state<UserPublic[]>([]);

	const isAnalystOrAdmin = $derived(
		$auth.user?.role === 'analyst' || $auth.user?.role === 'admin'
	);
	const ownerMap = $derived(Object.fromEntries(dms.map((u: UserPublic) => [u.id, u.username])));

	function getOwnerLabel(userId: number | null | undefined): string {
		if (userId == null) return '—';
		if (userId === $auth.user?.id) return $auth.user?.username ?? String(userId);
		return ownerMap[userId] ?? `User #${userId}`;
	}

	// 'me' | 'all' | '<user-id>'
	let selectedFilter = $state('me');

	const filteredSessions = $derived(
		selectedFilter === 'all'
			? sessions
			: selectedFilter === 'me'
				? sessions.filter((s) => s.user_id === $auth.user?.id)
				: sessions.filter((s) => s.user_id === Number(selectedFilter))
	);

	const usersWithSessions = $derived(
		isAnalystOrAdmin
			? [...new Map(sessions.map((s) => [s.user_id, s.user_id])).keys()].map((id) => ({
					id,
					label: getOwnerLabel(id)
				}))
			: []
	);

	// "Create for" selector: '' = myself, '<id>' = specific DM
	let selectedTargetDmId = $state<string>('');
	const targetUserId = $derived(selectedTargetDmId ? Number(selectedTargetDmId) : null);

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
			const created = await create_session(trimmed.length > 0 ? trimmed : null, targetUserId);

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

			if ($methodSelection.selectedSessionId === sessionId) {
				methodSelection.clearSession();
			}

			sessions = sessions.filter((s) => s.id !== sessionId);

			await refresh();
		} catch (err) {
			console.error('Failed to delete session', err);
			errorMessage.set('Failed to delete session.');
		} finally {
			deletingId = null;
			isLoading.set(false);
		}
	}

	onMount(async () => {
		await refresh();
		if (isAnalystOrAdmin) {
			const res = await getDmUsersUsersDmsGet().catch(() => null);
			if (res?.status === 200) dms = res.data as UserPublic[];
		}
	});
</script>

<svelte:head>
	<title>Sessions | DESDEO</title>
	<meta name="description" content="Page for managing existing sessions and creating new ones" />
</svelte:head>

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
			<Button
				variant="outline"
				size="sm"
				onclick={() => {
					methodSelection.clearSession();
					goto('/methods/initialize');
				}}
			>
				None
			</Button>
		</div>
	</div>

	<Card.Root class="mb-8">
		<Card.Header>
			<Card.Title>Create a new session</Card.Title>
			<Card.Description>Optional info/label.</Card.Description>
		</Card.Header>
		<Card.Content>
			{#if isAnalystOrAdmin && dms.length > 0}
				<div class="mb-3 flex items-center gap-3">
					<Label for="create-for" class="shrink-0 text-sm font-medium">Create for</Label>
					<Select.Root
						type="single"
						value={selectedTargetDmId}
						onValueChange={(v) => (selectedTargetDmId = v)}
					>
						<Select.Trigger id="create-for" class="w-48">
							{selectedTargetDmId ? getOwnerLabel(Number(selectedTargetDmId)) : ($auth.user?.username ?? 'Myself')}
						</Select.Trigger>
						<Select.Content>
							<Select.Item value="">{$auth.user?.username ?? 'Myself'}</Select.Item>
							{#each dms as dm}
								<Select.Item value={String(dm.id)}>{dm.username}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				</div>
			{/if}
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
				{isAnalystOrAdmin
					? 'All interactive sessions. Deleting a session removes it and its related states.'
					: 'Your interactive sessions. Deleting a session removes it and its related states.'}
			</Card.Description>
		</Card.Header>
		<Card.Content>
			{#if isAnalystOrAdmin && usersWithSessions.length > 1}
				<div class="mb-4 flex items-center gap-3">
					<Label for="session-filter" class="shrink-0 text-sm font-medium">Show sessions for</Label>
					<Select.Root
						type="single"
						value={selectedFilter}
						onValueChange={(v) => (selectedFilter = v || 'me')}
					>
						<Select.Trigger id="session-filter" class="w-48">
							{selectedFilter === 'me'
								? ($auth.user?.username ?? 'Myself')
								: selectedFilter === 'all'
									? 'All users'
									: getOwnerLabel(Number(selectedFilter))}
						</Select.Trigger>
						<Select.Content>
							<Select.Item value="me">{$auth.user?.username ?? 'Myself'}</Select.Item>
							<Select.Item value="all">All users</Select.Item>
							{#each usersWithSessions.filter((u) => u.id !== $auth.user?.id) as u}
								<Select.Item value={String(u.id)}>{u.label}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				</div>
			{/if}
			{#if filteredSessions.length === 0}
				<div class="text-muted-foreground text-sm">No sessions found. Create one above.</div>
			{:else}
				<Table.Root>
					<Table.Header>
						<Table.Row>
							<Table.Head class="w-[120px]">ID</Table.Head>
							<Table.Head>Info</Table.Head>
							{#if isAnalystOrAdmin}
								<Table.Head>Owner</Table.Head>
							{/if}
							<Table.Head class="w-[140px] text-right">Actions</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#each filteredSessions as s (s.id)}
							<Table.Row>
								<Table.Cell class="font-mono text-sm">{s.id}</Table.Cell>
								<Table.Cell class="max-w-[480px] truncate">{s.info ?? '—'}</Table.Cell>
								{#if isAnalystOrAdmin}
									<Table.Cell>{getOwnerLabel(s.user_id)}</Table.Cell>
								{/if}

								<Table.Cell class="text-right">
									<div class="flex justify-end gap-1">
										<Button
											variant="ghost"
											size="icon"
											onclick={() => {
												methodSelection.setSession(s.id, s.info ?? null);
												goto('/methods/initialize');
											}}
											title="Select session"
										>
											<Check class="size-4" />
										</Button>

										<Button
											variant="ghost"
											size="icon"
											disabled={deletingId === s.id}
											onclick={() => handleDelete(s.id)}
											title="Delete session"
										>
											<Trash2 class="size-4" />
										</Button>
									</div>
								</Table.Cell>
							</Table.Row>
						{/each}
					</Table.Body>
				</Table.Root>
			{/if}
		</Card.Content>
	</Card.Root>
</div>
