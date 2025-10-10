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
	import type { Step, TableData, ProblemInfo } from '../types';
	import VotingControls from './VotingControls.svelte';

	let {
		problem,
		step,
		current_state,
		tableData,
		selected_voting_index,
		previousValues,
		isDecisionMaker,
		onVote,
		onRowClick
	}: {
		problem: ProblemInfo;
		step: Step;
		current_state: { phase: string; personal_result_index: number | null };
		tableData: TableData[]; // Array of solutions
		selected_voting_index: number;
		previousValues: { [key: string]: number }[] | undefined;
		isDecisionMaker: boolean;
		onVote: (value: number) => void;
		onRowClick: (index: number) => void;
	} = $props();
</script>

<div class="flex h-full flex-col">
	{#if step === 'voting' && isDecisionMaker}
		<VotingControls phase={current_state.phase} {selected_voting_index} {onVote} />
	{/if}
	<div class="min-h-0 flex-1">
		<SolutionTable
			{problem}
			personalResultIndex={current_state.personal_result_index}
			solverResults={tableData}
			selectedSolutions={[selected_voting_index]}
			savingEnabled={false}
			handle_row_click={onRowClick}
			selected_type_solutions={'current'}
			previousObjectiveValuesType="user_results"
			previousObjectiveValues={previousValues}
		/>
	</div>
</div>
