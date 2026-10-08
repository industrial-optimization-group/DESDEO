<script lang="ts">
	import Dialogs from '$lib/components/custom/dialogs/Dialogs.svelte';
	import '../../../app.css';
	let { children } = $props();
</script>

<main class="flex min-h-[calc(100vh-3rem)]">
	<!-- 3rem = 12 * 0.25rem (h-12) -->
	<div class="w-full bg-gray-200">
		{@render children()}
	</div>
</main>
<Dialogs />
