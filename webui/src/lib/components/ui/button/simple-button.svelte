<script lang="ts">
	interface Props {
		disabled?: boolean;
		type?: 'button' | 'submit' | 'reset';
	}

	let { disabled = false, type = 'button' }: Props = $props();
</script>

<button
	{type}
	{disabled}
	class="focus-visible:border-ring focus-visible:ring-ring/50
         bg-primary text-primary-foreground shadow-xs hover:bg-primary/90 inline-flex h-9
         shrink-0 items-center justify-center gap-2 whitespace-nowrap
         rounded-md
         px-4 py-2
         text-sm font-medium outline-none transition-all
         focus-visible:ring-[3px] disabled:pointer-events-none disabled:opacity-50"
>
	<slot />
</button>
