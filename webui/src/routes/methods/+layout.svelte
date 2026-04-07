<script lang="ts">
	import Topbar from '$lib/components/ui/topbar/topbar.svelte';
	import {
		Breadcrumb,
		BreadcrumbList,
		BreadcrumbItem,
		BreadcrumbLink,
		BreadcrumbPage,
		BreadcrumbSeparator
	} from '$lib/components/ui/breadcrumb';
	import { page } from '$app/state';

	// finding path for breadcrumb
	const breadcrumbMap: Record<string, string> = {
		'/methods' : 'Methods',
		'/methods/initialize': 'Select Method',
		'/methods/sessions': 'Sessions'
	};

	$: currentPage = breadcrumbMap[page.url.pathname];
</script>

<div class="flex min-h-screen flex-col">
	<Topbar>
		<div slot="breadcrumbs">
			<Breadcrumb>
				<BreadcrumbList class="text-primary-foreground/80">
					<BreadcrumbItem>
						<BreadcrumbLink href="/dashboard" class="hover:text-primary-foreground">Dashboard</BreadcrumbLink>
					</BreadcrumbItem>
			
					<BreadcrumbSeparator />
			
					{#if currentPage !== 'Methods'}
						<BreadcrumbItem>
							<BreadcrumbLink href="/methods" class="hover:text-primary-foreground">Methods</BreadcrumbLink>
						</BreadcrumbItem>
				
						<BreadcrumbSeparator />				
					{/if}
			

					<BreadcrumbItem>
						<BreadcrumbPage class="text-primary-foreground">{currentPage}</BreadcrumbPage>
					</BreadcrumbItem>
				</BreadcrumbList>
			</Breadcrumb>
		</div>
	</Topbar>

	<slot />
</div>
