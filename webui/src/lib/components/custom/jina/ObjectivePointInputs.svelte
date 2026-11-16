<script lang="ts">
	/** One number input per objective; an emptied input holds null. */
	import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';
	import { Input } from '$lib/components/ui/input';
	import { objectiveLabel } from './labels';

	let {
		problem,
		objectives,
		idPrefix,
		values = $bindable({})
	}: {
		problem: ProblemInfo;
		objectives: string[];
		idPrefix: string;
		values?: Record<string, number | null>;
	} = $props();
</script>

{#each objectives as obj (obj)}
	<div class="flex items-center justify-between gap-2">
		<label for="{idPrefix}-{obj}" class="text-sm">{objectiveLabel(problem, obj)}</label>
		<Input
			id="{idPrefix}-{obj}"
			type="number"
			step="any"
			class="h-8 w-28 border-gray-400 px-2 text-sm"
			bind:value={values[obj]}
		/>
	</div>
{/each}
