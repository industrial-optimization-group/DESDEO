<script lang="ts">
	/**
	 * VotingControls Component
	 *
	 * Provides voting interface controls for decision makers in the GNIMBUS method.
	 * Adapts the UI based on the current phase (decision or learning/CRP).
	 *
	 * @component
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created October 2025
	 *
	 * @props {string} phase - Current phase ('decision' or other)
	 * @props {number} selected_voting_index - Index of currently selected solution
	 * @props {function} onVote - Callback function for vote submission
	 */
	import Button from '$lib/components/ui/button/button.svelte';

	export let phase: string;
	export let selected_voting_index: number;
	export let onVote: (value: number) => void;
</script>

{#if phase === 'decision' || phase === 'compromise'}
	<div class="mb-2 flex-none">
		<Button variant="default" onclick={() => onVote(1)}>Select as the final solution</Button>
		<Button variant="destructive" onclick={() => onVote(0)}>Continue to next iteration</Button>
	</div>
{:else}
	<div class="mb-2 flex-none">
		<Button disabled={selected_voting_index === -1} onclick={() => onVote(selected_voting_index)}
			>Vote</Button
		>
	</div>
{/if}
