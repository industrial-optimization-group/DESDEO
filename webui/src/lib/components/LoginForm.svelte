<script lang="ts">
	import { login, refreshAccessToken } from '../../api/utils';

	export const tokens = $state({ access: '', refresh: '' });

	let username = $state('');
	let password = $state('');

	async function handleLogin() {
		// use real login when implemented
		const login_response = await login(username, password);

		console.log(login_response);
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
