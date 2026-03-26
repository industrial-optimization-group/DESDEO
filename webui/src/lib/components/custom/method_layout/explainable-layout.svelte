<script lang="ts">
	import type { Snippet } from 'svelte';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import ResizableHandle from '$lib/components/ui/resizable/resizable-handle.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';

	// Define the interface for your named snippets
	interface Props {
		showLeftSidebar?: boolean;
		showRightSidebar?: boolean;
		leftSidebarWidth?: string;
		leftSidebarMinWidth?: string;
		rightSidebarWidth?: string;
		bottomPanelTitle?: string; // New prop for the bottom panel title
		// Named snippets
		leftSidebar?: Snippet;
		explorerTitle?: Snippet;
		explorerControls?: Snippet;
		debugPanel?: Snippet;
		visualizationArea?: Snippet<[number]>;
		tabsList?: Snippet;
		numericalValues?: Snippet;
		savedSolutions?: Snippet;
		rightSidebar?: Snippet;
	}

	let {
		showLeftSidebar = true,
		showRightSidebar = true,
		leftSidebarWidth = '24em',
		leftSidebarMinWidth = '24rem',
		rightSidebarWidth = 'auto',
		bottomPanelTitle = 'Numerical values', // Default title for the bottom panel
		leftSidebar,
		explorerTitle,
		explorerControls,
		debugPanel,
		visualizationArea,
		tabsList,
		numericalValues,
		savedSolutions,
		rightSidebar
	}: Props = $props();

	let visualizationHeight = $state(0);

	const hasLeft = $derived(showLeftSidebar && !!leftSidebar);
	const hasRight = $derived(showRightSidebar && !!rightSidebar);
	const gridTemplateColumns = $derived(
		hasLeft && hasRight
			? `${leftSidebarWidth} 1fr ${rightSidebarWidth}`
			: hasLeft
				? `${leftSidebarWidth} 1fr`
				: hasRight
					? `1fr ${rightSidebarWidth}`
					: '1fr'
	);
</script>

<Sidebar.Provider
	class="min-h-[calc(100vh-3rem)] w-full"
	style="--sidebar-width: 20rem; --sidebar-width-mobile: 20rem;"
>
	<div
		class="grid min-h-[calc(100vh-3rem)] w-full gap-2"
		style={`grid-template-columns: ${gridTemplateColumns};`}
	>
		<!-- Left Sidebar: Preferences and Controls -->
		{#if hasLeft}
			<div class="left-sidebar h-full" style={`min-width: ${leftSidebarMinWidth};`}>
				{@render leftSidebar?.()}
			</div>
		{/if}

		<Sidebar.Inset class="min-w-0">
			<div class="flex min-w-0 flex-1 flex-col">
				<Resizable.PaneGroup direction="vertical" class="flex-1">
					<Resizable.Pane defaultSize={50} class="flex min-h-0 flex-col">
						<!-- Top Panel: Explorer Title and Controls -->
						<div class="flex-shrink-0 p-2">
							<div class="flex flex-row items-center justify-between gap-4 pb-2">
								<div class="font-semibold">
									{#if explorerTitle}
										{@render explorerTitle()}
									{:else}
										Solution Explorer
									{/if}
								</div>
								<div class="flex items-center gap-2">
									{#if explorerControls}
										{@render explorerControls()}
									{/if}
								</div>
							</div>
						</div>
						<!-- Visualization Area -->
						<div
							class="mx-2 min-h-0 flex-1 rounded border bg-gray-100 p-4"
							bind:clientHeight={visualizationHeight}
						>
							<!-- Main Visualization Area -->
							<div class="h-full w-full">
								<div class="grid h-full w-full gap-4 xl:grid-cols-1">
									<div class="h-full flex-1 rounded">
										{#if visualizationArea}
											{@render visualizationArea(visualizationHeight)}
										{/if}
									</div>
								</div>
							</div>
						</div>
					</Resizable.Pane>

					<ResizableHandle />
					<!-- Bottom Panel: Numerical Values and Tables -->
					<Resizable.Pane defaultSize={50} class="flex min-h-0 flex-col">
						<div class="min-h-0 w-full flex-shrink p-2">
							<Tabs.Root value="numerical-values" class="flex h-full flex-shrink flex-col">
								<Tabs.List class="flex-shrink-0">
									{#if tabsList}
										{@render tabsList()}
									{:else}
										<span class="text-black">{bottomPanelTitle}</span>
									{/if}
								</Tabs.List>

								<!-- Numerical Values Tab Content -->
								<Tabs.Content value="numerical-values" class="min-h-0">
									{#if numericalValues}
										{@render numericalValues()}
									{:else}
										<div class="p-4">Default numerical values content</div>
									{/if}
								</Tabs.Content>

								<!-- Saved Solutions Tab Content -->
								<Tabs.Content value="saved-solutions" class="min-h-0 flex-grow">
									{#if savedSolutions}
										{@render savedSolutions()}
									{:else}
										<div class="p-4">Default saved solutions content</div>
									{/if}
								</Tabs.Content>
							</Tabs.Root>
						</div>
					</Resizable.Pane>
				</Resizable.PaneGroup>
			</div>
		</Sidebar.Inset>

		<!-- Right Sidebar -->
		{#if hasRight}
			<div class="right-sidebar h-full">
				{@render rightSidebar?.()}
			</div>
		{/if}
	</div>
</Sidebar.Provider>

<style>
	.left-sidebar {
		flex-shrink: 0;
		border-right: 1px solid var(--border-color, #e2e8f0);
	}

	.right-sidebar {
		flex-shrink: 0;
		border-left: 1px solid var(--border-color, #e2e8f0);
	}

	/* Responsive design */
	@media (max-width: 768px) {
		.left-sidebar,
		.right-sidebar {
			position: fixed;
			top: 0;
			height: 100vh;
			z-index: 1000;
			background: white;
			box-shadow: 2px 0 4px rgba(0, 0, 0, 0.1);
		}

		.left-sidebar {
			left: 0;
		}

		.right-sidebar {
			right: 0;
		}
	}
</style>
