<script lang="ts">
	import { Modal } from '@skeletonlabs/skeleton-svelte';
	// The application's global stylesheet
	// import '../app.postcss';
	import '../app.css';

	let { children } = $props();
	let drawerState = $state(false);

	function drawerClose() {
		drawerState = false;
	}
</script>

<div class="preset-tonal-primary">
	{@render children?.()}
</div>
