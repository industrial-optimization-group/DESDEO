<script lang="ts">
	import { api } from '$lib/api/client';
	import { goto } from '$app/navigation';
	import { auth } from '../../stores/auth';
	import { tick } from 'svelte';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import GalleryVerticalEndIcon from '@lucide/svelte/icons/orbit';
	import main_image from '$lib/assets/main.jpg';
	import { setTime } from 'effect/TestClock';

	let username = ''; // from login form
	let password = '';
	let loginError: string | null = null; // whether login is successful or not

	async function handleLogin() {
		const res = await api.POST('/login', {
			// @ts-ignore
			body: new URLSearchParams({
				// type not really matched, but it is what it is here (not worth fixing right now)
				username,
				password,
				scope: ''
			}),
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded'
			},
			credentials: 'include'
		});

		const token = res.data?.access_token;
		// check if login ok
		if (!token) {
			loginError = 'Invalid username or password';
			return;
		}

		// need to set token to be available, even if user not known yet
		auth.setAuth(token, null);

		const userRes = await api.GET('/user_info');

		// check is user data can be fetched
		if (!userRes.data) {
			loginError = 'Could not fetch user info';
			auth.clearAuth();
			return;
		}

		// user info available, update that as well
		auth.setAuth(token, userRes.data);

		goto('/dashboard');
	}
</script>

<div class="grid min-h-svh lg:grid-cols-2">
	<div class="left-inner-shadow flex flex-col gap-4 p-6 md:p-10">
		<div class="flex justify-center gap-2 md:justify-start">
			<a href="##" class="flex items-center gap-2 font-medium">
				<div
					class="bg-primary text-primary-foreground flex size-6 items-center justify-center rounded-md"
				>
					<GalleryVerticalEndIcon class="size-4" />
				</div>
				DESDEO
			</a>
		</div>
		<div class="flex flex-1 items-center justify-center">
			<div class="w-full max-w-xs">
				<form class="flex flex-col gap-6" on:submit|preventDefault={handleLogin}>
					<div class="flex flex-col items-center gap-2 text-center">
						<h1 class="text-2xl font-bold">Login to your account</h1>
						<p class="text-muted-foreground text-sm text-balance">
							Enter your username below to login to your account
						</p>
					</div>
					<div class="grid gap-6">
						<div class="grid gap-3">
							<Label for="username">Username</Label>
							<Input id="username" bind:value={username} required />
						</div>
						<div class="grid gap-3">
							<div class="flex items-center">
								<Label for="password">Password</Label>
								<a href="##" class="ml-auto text-sm underline-offset-4 hover:underline">
									Forgot your password?
								</a>
							</div>
							<Input id="password" type="password" bind:value={password} required />
						</div>
						<Button type="submit" class="w-full">Login</Button>
						{#if loginError}
							<p class="text-center text-sm text-red-500">{loginError}</p>
						{/if}
					</div>
					<div class="text-center text-sm">
						Don&apos;t have an account?
						<a href="##" class="underline underline-offset-4"> Sign up </a>
						or
						<a href="/dashboard" class="underline underline-offset-4">
							explore DESDEO as a guest.
						</a>
					</div>
				</form>
			</div>
		</div>
	</div>
	<div class="bg-muted relative hidden lg:block">
		<img
			src={main_image}
			alt="placeholder"
			class="absolute inset-0 h-full w-full object-cover dark:brightness-[0.2] dark:grayscale"
		/>
		<div class="bg-primary-600 pointer-events-none absolute inset-0 opacity-20"></div>
	</div>
</div>
