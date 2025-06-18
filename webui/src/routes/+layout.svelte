<script lang="ts">
	import '../app.css';

	import { setContext } from 'svelte';

	let { children } = $props();
</script>

<div class="preset-tonal-primary">
	{@render children?.()}
</div>
