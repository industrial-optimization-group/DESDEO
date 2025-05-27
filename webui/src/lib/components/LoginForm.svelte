<script lang="ts">
	import { getContext } from 'svelte';
	import { login, getUserDetails, refreshAccessToken } from '$lib/utils/utils';
	import type { UserData, UserInfo } from '$lib/utils/utils';

	// import context
	let user_data: UserData = getContext('user_data');

	let { login_ok = $bindable() }: { login_ok: boolean } = $props();

	let username = $state('');
	let password = $state('');
	let access_token = $state('');

	async function handleLogin() {
		// Login and fetch user info and then set user info.
		const login_response = await login(username, password);

		access_token = login_response.access_token;

		let tmp: UserInfo = await getUserDetails(access_token);
		tmp.access_token = access_token;

		user_data.user_info = tmp;

		login_ok = true;
	}

	async function _refresh() {
		const new_access_token = await refreshAccessToken();

		console.log(new_access_token);
	}
</script>

<div class="flex flex-col items-center gap-10">
	<div class="mb-6 text-3xl">Login to your account</div>
	<form class="mx-24 flex w-72 flex-col gap-4">
		<label class="label">
			<span class="label-text">Username</span>
			<input class="input" type="text" placeholder="Username" bind:value={username} />
		</label>

		<label class="label">
			<span class="label-text">Password</span>
			<input class="input" type="text" placeholder="Password" bind:value={password} />
		</label>

		<button
			type="button"
			class="btn mt-2 uppercase preset-filled-primary-500"
			disabled={!(() => {
				return username.length > 0 && password.length > 0;
			})()}
			onclick={handleLogin}>Log in</button
		>
		<button
			type="button"
			class="btn mt-2 uppercase preset-filled-primary-500"
			disabled={!(() => {
				return username.length > 0 && password.length > 0;
			})()}
			onclick={_refresh}>Refresh Access Token</button
		>
		<a href="/">go back</a>
	</form>

	<div class="flex flex-col items-center">
		<span class="whitespace-nowrap"
			>Don't have an account? <a href="/" class="anchor">Create a free account</a></span
		>
		<span class="whitespace-nowrap"
			>or <button class="anchor" onclick={handleLogin}>explore DESDEO as a guest</button></span
		>
	</div>
</div>
