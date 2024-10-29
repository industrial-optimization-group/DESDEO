<script lang="ts">
	import LoginForm from '$lib/components/LoginForm.svelte';
	import { goto } from '$app/navigation';

	let { login_ok = $bindable(false) }: { login_ok: boolean } = $props();

	$effect(() => {
		if (login_ok) {
			goto('/');
		}
	});
</script>

<LoginForm bind:login_ok></LoginForm>
