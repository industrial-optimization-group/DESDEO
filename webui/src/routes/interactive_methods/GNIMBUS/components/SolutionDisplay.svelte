<script lang="ts">
	/**
	 * SolutionDisplay Component
	 *
	 * Displays solution data in a tabular format with optional voting controls.
	 *
	 * @component
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created October 2025
	 */
	import SolutionTable from '$lib/components/custom/nimbus/solution-table.svelte';
	import Button from '$lib/components/ui/button/button.svelte';
	import type { Step, TableData, ProblemInfo } from '../types';
	import VotingControls from './VotingControls.svelte';

	let {
		problem,
		step,
		current_state,
		tableData,
		selected_type_solutions,
		selected_voting_index,
		userSolutionsObjectives,
		isDecisionMaker,
		isOwner,
		onVote,
		onChangeIteration,
		onRowClick
	}: {
		problem: ProblemInfo;
		step: Step;
		current_state: { phase: string; personal_result_index: number | null };
		tableData: TableData[]; // Array of solutions
		selected_type_solutions: string;
		selected_voting_index: number;
		userSolutionsObjectives: { [key: string]: number }[] | undefined;
		isDecisionMaker: boolean;
		isOwner: boolean;
		onVote: (value: number) => void;
		onChangeIteration: () => void;
		onRowClick: (index: number) => void;
	} = $props();
</script>

<div class="flex h-full flex-col">
	<div class="min-h-0 flex-1">
		<SolutionTable
			{problem}
			personalResultIndex={current_state.personal_result_index}
			solverResults={tableData}
			selectedSolutions={[selected_voting_index]}
			savingEnabled={false}
			handle_row_click={onRowClick}
			{selected_type_solutions}
			methodPage="gnimbus"
			secondaryObjectiveValues={userSolutionsObjectives}
		/>
	</div>
	{#if step === 'voting' && isDecisionMaker && selected_type_solutions === 'current'}
		<VotingControls phase={current_state.phase} {selected_voting_index} {onVote} />
	{/if}
	{#if selected_type_solutions === 'all_final' && isOwner}
	<div class="mb-2 flex-none">
		<Button onclick={onChangeIteration} disabled={step === 'voting' || selected_voting_index === -1}>
			Copy selected iteration as starting point for next iteration
		</Button>
	</div>
	{/if}
</div>
