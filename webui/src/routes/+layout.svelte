<script lang="ts">
	import '../app.css';

	import { setContext } from 'svelte';
	import type { UserData } from '$lib/core/user_and_login';

	let { children } = $props();

	// Set top-level context
	let user_data: UserData = $state({ user_info: null });
	setContext('user_data', user_data);

	$inspect(user_data);
</script>

<div class="preset-tonal-primary">
	{@render children?.()}
</div>
