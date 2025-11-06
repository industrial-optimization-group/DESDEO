<script lang="ts">
	import Topbar from '$lib/components/ui/topbar/topbar.svelte';
</script>

<div class="flex min-h-screen flex-col">
	<Topbar />
	<slot />
</div>
