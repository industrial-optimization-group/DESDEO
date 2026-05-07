<script lang="ts">
	import Topbar from '$lib/components/ui/topbar/topbar.svelte';
	import TopbarBreadcrumbs from '$lib/components/ui/topbar-breadcrumbs/topbar-breadcrumbs.svelte';
</script>

<div class="flex min-h-screen flex-col">
	<Topbar>
		<div slot="breadcrumbs">
			<TopbarBreadcrumbs/>
		</div>
	</Topbar>

	<slot />
</div>
