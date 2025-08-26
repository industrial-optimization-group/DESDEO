<script lang="ts">
	import type { Snippet } from 'svelte';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import ResizableHandle from '$lib/components/ui/resizable/resizable-handle.svelte';

	// Define the interface for your named snippets
	interface Props {
		showLeftSidebar?: boolean;
		showRightSidebar?: boolean;
		leftSidebarWidth?: string;
		rightSidebarWidth?: string;
		bottomPanelTitle?: string; // New prop for the bottom panel title
		// Named snippets
		leftSidebar?: Snippet;
		explorerTitle?: Snippet;
		explorerControls?: Snippet;
		debugPanel?: Snippet;
		visualizationArea?: Snippet;
		tabsList?: Snippet;
		numericalValues?: Snippet;
		savedSolutions?: Snippet;
		rightSidebar?: Snippet;
	}

	let {
		showLeftSidebar = true,
		showRightSidebar = true,
		leftSidebarWidth = 'auto',
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
</script>

<div class="flex min-h-[calc(100vh-3rem)]">
	<!-- Left Sidebar: Preferences and Controls -->
	{#if showLeftSidebar}
		<aside class="left-sidebar" style="width: {leftSidebarWidth}">
			{#if leftSidebar}
				{@render leftSidebar()}
			{/if}
		</aside>
	{/if}

	<!-- Main Content Area -->
	<div class="flex min-w-0 flex-1 flex-col">
		<Resizable.PaneGroup direction="vertical" class="flex-1">
			<Resizable.Pane class="flex min-h-0 flex-col">
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
				<div class="mx-2 min-h-0 flex-1 rounded border bg-gray-100 p-4">
					<!-- Main Visualization Area -->
					<div class="h-full w-full">
						<div class="grid h-full w-full gap-4 xl:grid-cols-1">
							<div class="h-full flex-1 rounded">
								{#if visualizationArea}
									{@render visualizationArea()}
								{/if}
							</div>
						</div>
					</div>
				</div>
			</Resizable.Pane>

			<ResizableHandle />
			<!-- Bottom Panel: Numerical Values and Tables -->
			<Resizable.Pane class="flex min-h-0 flex-col p-2">
					<Tabs.Root value="numerical-values" class="flex flex-col min-h-0 h-full">
						<Tabs.List class="flex-shrink-0">
						{#if tabsList}
							{@render tabsList()}
						{:else}
							<span class='text-black'>{bottomPanelTitle}</span>
						{/if}
						</Tabs.List>

						<!-- Numerical Values Tab Content -->
						<Tabs.Content value="numerical-values" class="min-h-0 flex-grow">
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
			</Resizable.Pane>
		</Resizable.PaneGroup>
	</div>

	<!-- Right Sidebar -->
	{#if showRightSidebar}
		<aside class="right-sidebar" style="width: {rightSidebarWidth}">
			{#if rightSidebar}
				{@render rightSidebar()}
			{/if}
		</aside>
	{/if}
</div>

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
