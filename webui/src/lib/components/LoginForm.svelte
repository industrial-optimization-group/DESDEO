<script lang="ts">
	type AuthorizationTokens = {
		access: string;
		refresh: string;
	};

	export const tokens = $state({ access: '', refresh: '' });

	let username = $state('');
	let password = $state('');

	function fauxLogin(username: string, password: string): AuthorizationTokens {
		// Implement login
		return { access: 'token_access', refresh: 'token_refresh' };
	}

	function handleLogin() {
		// use real login when implemented
		const new_tokens = fauxLogin(username, password);
		tokens.access = new_tokens.access;
		tokens.refresh = new_tokens.refresh;
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
			class="btn preset-filled-primary-500 mt-2 uppercase"
			disabled={!(() => {
				return username.length > 0 && password.length > 0;
			})()}
			onclick={handleLogin}>Log in</button
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
