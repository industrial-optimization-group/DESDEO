<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import '../../../app.css';
	let { children } = $props();
</script>

<main class="flex min-h-[calc(100vh-3rem)]">
	<!-- 3rem = 12 * 0.25rem (h-12) -->
	<Sidebar.Provider
		class="flex min-h-[calc(100vh-3rem)]"
		style="--sidebar-width: 25rem; --sidebar-width-mobile: 20rem;"
	>
		<Sidebar.Inset class="bg-gray-200">
			{@render children()}
		</Sidebar.Inset>
	</Sidebar.Provider>
</main>
