<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { auth } from '../../stores/auth';
	import { goto } from '$app/navigation';

	/* 	onMount(() => {
		const { accessToken, user } = get(auth);
		if (!accessToken || !user) {
			goto('/home');
		}
	}); */
</script>

<slot />
