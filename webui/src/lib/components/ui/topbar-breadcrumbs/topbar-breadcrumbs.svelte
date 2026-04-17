<script lang="ts">
	import {
		Breadcrumb,
		BreadcrumbList,
		BreadcrumbItem,
		BreadcrumbLink,
		BreadcrumbPage,
		BreadcrumbSeparator,
        BreadcrumbEllipsis
	} from '$lib/components/ui/breadcrumb';
	import { page } from '$app/state';

	// Map of paths and relevant labels
    // EACH PATH THAT CONTAINS BREADCRUMBS MUST HAVE ASSIGNED LABEL HERE!
	const breadcrumbMap: Record<string, string> = {
        '/groups': 'Groups',
        '/interactive_methods' : 'Methods',
		'/interactive_methods/E-NAUTILUS': 'E-NAUTILUS',
		'/interactive_methods/EMO': 'EMO',
		'/interactive_methods/GDM-SCORE-bands': 'GDM Score Bands',
		'/interactive_methods/GNIMBUS': 'GNIMBUS',
		'/interactive_methods/NIMBUS': 'NIMBUS',
		'/interactive_methods/SCORE-bands': 'Score Bands',
		'/interactive_methods/XNIMBUS': 'XNIMBUS',
        '/manage-users': 'Manage Users',
        '/methods' : 'Methods',
		'/methods/initialize': 'Select Method',
		'/methods/sessions': 'Sessions',
		'/problems': 'Problems',
		'/problems/define': 'Define New',
	};

	// Paths that are layout-only (no +page.svelte) — rendered as plain text, not links
	const nonLinkablePaths = new Set(['/methods', '/interactive_methods']);

    let allCurrentPagePaths = $derived(
        page.url.pathname
        .split('/')
        .filter(Boolean)
        .map((_, i, arr) => {
			const path = '/' + arr.slice(0, i + 1).join('/');
			return {
				path,
				label: breadcrumbMap[path]
			};
		})
		.filter((crumb): crumb is { path: string; label: string } => crumb.label != null)
    );

    // This part controls breadcrumb ellipsis when the path is too long
    const MAX_VISIBLE = 5;
    const HEAD = 1; // Dashboard does not count to this
    const TAIL = 2;

    let visibleBreadcrumbs = $derived(
        (() => {
        const crumbs = allCurrentPagePaths;

        if (crumbs.length <= MAX_VISIBLE) return crumbs;

        return [
            ...crumbs.slice(0, HEAD),
            { ellipsis: true },
            ...crumbs.slice(-1*TAIL)
        ];
    })());
</script>


<Breadcrumb>
    <BreadcrumbList class="text-primary-foreground/80">
        <BreadcrumbItem>
            <BreadcrumbLink href="/dashboard" class="hover:text-primary-foreground">Dashboard</BreadcrumbLink>
        </BreadcrumbItem>

        <BreadcrumbSeparator />

        {#each visibleBreadcrumbs as crumb, i}
            {#if 'ellipsis' in crumb}
                <BreadcrumbItem>
                    <BreadcrumbEllipsis />
                </BreadcrumbItem>
                <BreadcrumbSeparator />
            {:else if i < visibleBreadcrumbs.length - 1}
                <BreadcrumbItem>
                    {#if nonLinkablePaths.has(crumb.path)}
                        <span class="text-primary-foreground/60">{crumb.label}</span>
                    {:else}
                        <BreadcrumbLink href={crumb.path} class="hover:text-primary-foreground">
                            {crumb.label}
                        </BreadcrumbLink>
                    {/if}
                </BreadcrumbItem>
                <BreadcrumbSeparator />
            {:else}
                <BreadcrumbItem>
                    <BreadcrumbPage class="text-primary-foreground">
                        {crumb.label}
                    </BreadcrumbPage>
                </BreadcrumbItem>
            {/if}
        {/each}
    </BreadcrumbList>
</Breadcrumb>
