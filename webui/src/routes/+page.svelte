<script lang="ts">
	import { getContext } from 'svelte';
	import type { UserData } from '$lib/utils/utils';

	let user_data: UserData = $derived(getContext('user_data'));
</script>

{#if user_data.user_info}<h1>User info set!</h1>
	{JSON.stringify(user_data, null, 2)}{:else}<h1>User info NOT set</h1>
	<p>Please <a href="/login"> LOGIN</a></p>{/if}
