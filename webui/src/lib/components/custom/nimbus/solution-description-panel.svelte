<script lang="ts">
	interface Props {
		description: string | null
	}

	let { description }: Props = $props()
</script>

<div class="flex h-full flex-col overflow-hidden p-4">
	{#if description}
		<h3 class="mb-3 text-lg font-medium">Solution Description</h3>
		<div class="flex-1 overflow-y-auto rounded border bg-gray-50 p-3 text-sm" style="white-space: pre-wrap;">
			{description}
		</div>
	{:else}
		<div class="flex h-full items-center justify-center text-gray-400 text-sm">
			Select a solution to view its description
		</div>
	{/if}
</div>
