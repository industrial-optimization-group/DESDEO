<script lang="ts">
	import Topbar from '$lib/components/ui/topbar/topbar.svelte';
	import Dialogs from '$lib/components/custom/dialogs/Dialogs.svelte';
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
		'/problems': 'Problems',
		'/problems/define': 'Define New'
	};

	$: currentPage = breadcrumbMap[page.url.pathname] ?? 'Select Method';
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
			
					{#if currentPage !== 'Problems'}
						<BreadcrumbItem>
							<BreadcrumbLink href="/problems" class="hover:text-primary-foreground">Problems</BreadcrumbLink>
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

<Dialogs />
