<script lang="ts">
	/**
	 * score-bands-solution-table.svelte
	 *
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created December 2025
	 *
	 * @description
	 * Simplified solution table component for GDM SCORE-Bands decision phase.
	 * Displays solutions for voting with objective values and voting status.
	 *
	 * @props
	 * @property {ProblemInfo} problem - The current optimization problem
	 * @property {Array<{ [key: string]: number }>} solutions - Solutions to display (already transformed)
	 * @property {number | null} selectedSolution - Index of currently selected solution
	 * @property {Function} onSolutionSelect - Callback when a solution is selected
	 * @property {boolean} [userHasVoted=false] - Whether current user has voted
	 * @property {number | null} [userVotedSolution=null] - Which solution user voted for
	 * @property {{ [key: string]: number }} [groupVotes={}] - Group voting status
	 *
	 * @features
	 * - Simple table showing objective values for each solution
	 * - Click to select solutions for voting
	 * - Highlighting for selected and voted solutions
	 * - Responsive design for decision phase
	 */
	import type { components } from '$lib/api/client-types';
	import { getDisplayAccuracy, formatNumber } from '$lib/helpers';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors.js';

	// Types
	type ProblemInfo = components['schemas']['ProblemInfo'];

	// Props
	let {
		problem,
		solutions,
		selectedSolution,
		onSolutionSelect,
		userHasVoted = false,
		userVotedSolution = null,
		groupVotes = {}
	}: {
		problem: ProblemInfo;
		solutions: Array<{ [key: string]: number }>;
		selectedSolution: number | null;
		onSolutionSelect: (index: number | null, solutionData?: any) => void;
		userHasVoted?: boolean;
		userVotedSolution?: number | null;
		groupVotes?: { [key: string]: number };
	} = $props();

	// Get display accuracy for number formatting
	let displayAccuracy = $derived.by(() => getDisplayAccuracy(problem));

	// Helper function to get solution display name
	function getSolutionName(index: number): string {
		return `Solution ${index + 1}`;
	}

	// Helper function to check if solution is voted by user
	function isUserVotedSolution(index: number): boolean {
		return userHasVoted && userVotedSolution === index;
	}

	// Helper function to get vote count for solution
	function getVoteCount(index: number): number {
		return Object.values(groupVotes).filter(vote => vote === index).length;
	}

	// Helper function to get objective title
	function getObjectiveTitle(objective: any): string {
		if (!objective) return '';
		const tooltip = objective.description || objective.name;
		return objective.unit ? `${tooltip} (${objective.unit})` : tooltip;
	}
</script>
	 * - Svelte Runes mode for reactivity

{#if problem && solutions.length > 0}
	<div class="overflow-auto rounded border shadow-sm">
		<table class="table w-full">
			<thead>
				<tr>
					<!-- Solution name column -->
					<th class="w-32">Solution</th>
					
					<!-- Objective columns -->
					{#each problem.objectives as objective, idx}
						<th 
							class="text-center min-w-24"
							style="border-bottom: 4px solid {COLOR_PALETTE[idx % COLOR_PALETTE.length]}"
							title={getObjectiveTitle(objective)}
						>
							<div class="flex flex-col items-center">
								<span class="font-medium">{objective.name}</span>
								{#if objective.unit}
									<span class="text-xs text-gray-500">({objective.unit})</span>
								{/if}
								<span class="text-xs text-gray-500">({objective.maximize ? 'max' : 'min'})</span>
							</div>
						</th>
					{/each}
					
					<!-- Vote count column -->
					<th class="w-20 text-center">Votes</th>
				</tr>
			</thead>
			
			<tbody>
				{#each solutions as solution, index}
					<tr 
						class="cursor-pointer hover:bg-gray-50 {selectedSolution === index ? 'bg-blue-100 border-l-4 border-blue-600' : ''} {isUserVotedSolution(index) ? 'bg-green-50 border-l-4 border-green-600' : ''}"
						onclick={() => onSolutionSelect(index, solution)}
						role="button"
						tabindex="0"
						onkeydown={(e) => {
							if (e.key === 'Enter' || e.key === ' ') {
								e.preventDefault();
								onSolutionSelect(index, solution);
							}
						}}
					>
						<!-- Solution name -->
						<td class="font-medium">
							<div class="flex flex-col">
								<span>{getSolutionName(index)}</span>
								{#if isUserVotedSolution(index)}
									<span class="text-xs text-green-600 font-medium">✓ Your vote</span>
								{:else if selectedSolution === index}
									<span class="text-xs text-blue-600">Selected</span>
								{/if}
							</div>
						</td>
						
						<!-- Objective values -->
						{#each problem.objectives as objective, objIndex}
							<td class="text-center">
								{#if solution[objective.symbol] !== undefined}
									{formatNumber(solution[objective.symbol], displayAccuracy[objIndex])}
								{:else}
									-
								{/if}
							</td>
						{/each}
						
						<!-- Vote count -->
						<td class="text-center">
							{#if getVoteCount(index) > 0}
								<span class="badge {getVoteCount(index) > 1 ? 'badge-accent' : 'badge-primary'} badge-sm">
									{getVoteCount(index)}
								</span>
							{:else}
								<span class="text-gray-400">0</span>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
	
	<!-- Table Legend -->
	<div class="mt-4 text-sm text-gray-600">
		<div class="flex flex-wrap gap-4">
			<div class="flex items-center gap-2">
				<div class="w-3 h-3 bg-blue-100 border-l-2 border-blue-600"></div>
				<span>Selected for voting</span>
			</div>
			<div class="flex items-center gap-2">
				<div class="w-3 h-3 bg-green-50 border-l-2 border-green-600"></div>
				<span>Your vote</span>
			</div>
			<div class="flex items-center gap-2">
				<span>Click rows to select solutions</span>
			</div>
		</div>
	</div>
{:else}
	<div class="text-center py-8 text-gray-500">
		No solutions available for voting.
	</div>
{/if}

<style>
	.table th {
		position: sticky;
		top: 0;
		background: white;
		z-index: 10;
	}
	
	.table tr:hover td {
		background-color: inherit;
	}
</style>
