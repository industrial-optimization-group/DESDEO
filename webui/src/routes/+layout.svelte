<script lang="ts">
	// import { Modal } from '@skeletonlabs/skeleton-svelte';
	// The application's global stylesheet
	// import '../app.postcss';
	import '../app.css';

	import { setContext } from 'svelte';
	import type { UserData } from '$lib/utils/utils';

	let { children } = $props();

	// Set top-level context
	let user_data: UserData = $state({});
	setContext('user_data', user_data);

	$inspect(user_data);
</script>

<div class="preset-tonal-primary">
	{@render children?.()}
</div>
