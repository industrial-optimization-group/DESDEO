<script lang="ts">
	import { Label } from '$lib/components/ui/label/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import LoadingSpinner from '$lib/components/custom/notifications/loading-spinner.svelte';
	import { auth } from '../../stores/auth';
	import { addDm, addAnalyst } from './handler';
	import type { UserCreateResult } from './handler';

	const isAnalystOrAdmin = $derived(
		$auth.user?.role === 'analyst' || $auth.user?.role === 'admin'
	);

	let dmUsername = $state('');
	let dmPassword = $state('');
	let dmLoading = $state(false);
	let dmResult = $state<UserCreateResult | null>(null);

	let analystUsername = $state('');
	let analystPassword = $state('');
	let analystLoading = $state(false);
	let analystResult = $state<UserCreateResult | null>(null);

	async function handleAddDm(e: Event) {
		e.preventDefault();
		dmLoading = true;
		dmResult = null;
		dmResult = await addDm(dmUsername, dmPassword);
		if (dmResult.success) {
			dmUsername = '';
			dmPassword = '';
		}
		dmLoading = false;
	}

	async function handleAddAnalyst(e: Event) {
		e.preventDefault();
		analystLoading = true;
		analystResult = null;
		analystResult = await addAnalyst(analystUsername, analystPassword);
		if (analystResult.success) {
			analystUsername = '';
			analystPassword = '';
		}
		analystLoading = false;
	}
</script>

<svelte:head>
	<title>Manage Users | DESDEO</title>
</svelte:head>

<main class="container mx-auto px-4 py-8">
	<h1 class="mb-1 text-2xl font-bold">Manage Users</h1>
	<p class="text-muted-foreground mb-8 text-sm">Create new user accounts.</p>

	<div class="grid grid-cols-1 gap-6 md:grid-cols-2">
		<!-- Add Decision Maker -->
		<Card.Root>
			<Card.Header>
				<Card.Title>Add Decision Maker</Card.Title>
				<Card.Description>Create a new decision maker account.</Card.Description>
			</Card.Header>
			<Card.Content>
				<form onsubmit={handleAddDm} class="flex flex-col gap-4">
					<div class="grid gap-2">
						<Label for="dm-username">Username<span class="text-red-500">*</span></Label>
						<Input
							id="dm-username"
							name="username"
							placeholder="Enter username"
							bind:value={dmUsername}
							required
						/>
					</div>
					<div class="grid gap-2">
						<Label for="dm-password">Password<span class="text-red-500">*</span></Label>
						<Input
							id="dm-password"
							name="password"
							type="password"
							placeholder="Enter password"
							bind:value={dmPassword}
							required
						/>
					</div>
					<Button type="submit" disabled={dmLoading}>
						{#if dmLoading}
							<LoadingSpinner />
							Creating...
						{:else}
							Create decision maker
						{/if}
					</Button>
					{#if dmResult}
						<p class={dmResult.success ? 'text-sm text-green-600' : 'text-sm text-red-500'}>
							{dmResult.message}
						</p>
					{/if}
				</form>
			</Card.Content>
		</Card.Root>

		<!-- Add Analyst (analyst and admin only) -->
		{#if isAnalystOrAdmin}
			<Card.Root>
				<Card.Header>
					<Card.Title>Add Analyst</Card.Title>
					<Card.Description>Create a new analyst account.</Card.Description>
				</Card.Header>
				<Card.Content>
					<form onsubmit={handleAddAnalyst} class="flex flex-col gap-4">
						<div class="grid gap-2">
							<Label for="analyst-username"
								>Username<span class="text-red-500">*</span></Label
							>
							<Input
								id="analyst-username"
								name="username"
								placeholder="Enter username"
								bind:value={analystUsername}
								required
							/>
						</div>
						<div class="grid gap-2">
							<Label for="analyst-password"
								>Password<span class="text-red-500">*</span></Label
							>
							<Input
								id="analyst-password"
								name="password"
								type="password"
								placeholder="Enter password"
								bind:value={analystPassword}
								required
							/>
						</div>
						<Button type="submit" disabled={analystLoading}>
							{#if analystLoading}
								<LoadingSpinner />
								Creating...
							{:else}
								Create analyst
							{/if}
						</Button>
						{#if analystResult}
							<p
								class={analystResult.success ? 'text-sm text-green-600' : 'text-sm text-red-500'}
							>
								{analystResult.message}
							</p>
						{/if}
					</form>
				</Card.Content>
			</Card.Root>
		{/if}
	</div>
</main>
