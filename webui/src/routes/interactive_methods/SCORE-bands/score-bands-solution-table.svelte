<script lang="ts">
	/**
	 * score-bands-solution-table.svelte
	 *
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created December 2025
	 *
	 * @description
	 * Solution table component for single-user SCORE-bands method.
	 * Placeholder component adapted from GDM version for individual decision making.
	 *
	 * @status PLACEHOLDER - Ready for adaptation to single-user workflow
	 *
	 * @props
	 * @property {ProblemInfo} problem - The optimization problem information
	 * @property {Array<{ [key: string]: number }>} solutions - Solutions to display
	 * @property {number | null} selectedSolution - Currently selected solution index
	 * @property {Function} onSolutionSelect - Callback for solution selection
	 * @property {boolean} [userHasSelected=false] - Whether user has made selection
	 * @property {number | null} [userSelectedSolution=null] - User's selected solution
	 *
	 * @features
	 * - Sortable columns for objective values
	 * - Solution selection for preference input
	 * - Highlighting for selected solutions
	 * - Responsive design
	 *
	 * @todo
	 * - Adapt voting logic to single-user preference handling
	 * - Remove group-specific functionality
	 * - Connect to single-user SCORE-bands method workflow
	 */
	import {
		type ColumnDef,
		type Column,
		type Row,
		type SortingState,
		getCoreRowModel,
		getSortedRowModel
	} from '@tanstack/table-core';
	import { createSvelteTable } from '$lib/components/ui/data-table/data-table.svelte.js';
	import FlexRender from '$lib/components/ui/data-table/flex-render.svelte';
	import * as Table from '$lib/components/ui/table/index.js';
	import { renderSnippet } from '$lib/components/ui/data-table/render-helpers.js';
	import type { components } from '$lib/api/client-types';
	import { getDisplayAccuracy, formatNumber } from '$lib/helpers';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors.js';
	import ArrowUpIcon from '@lucide/svelte/icons/arrow-up';
	import ArrowDownIcon from '@lucide/svelte/icons/arrow-down';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';

	// Types
	type ProblemInfo = components['schemas']['ProblemInfo'];
	type SolutionData = { [key: string]: number } & { index: number };

	// Props
	let {
		problem,
		solutions,
		selectedSolution,
		onSolutionSelect,
		userVotedSolution = null,
		groupVotes = {}
	}: {
		problem: ProblemInfo;
		solutions: Array<{ [key: string]: number }>;
		selectedSolution: number | null;
		onSolutionSelect: (index: number | null, solutionData?: any) => void;
		userVotedSolution?: number | null;
		groupVotes?: { [key: string]: number };
	} = $props();

	// Get display accuracy for number formatting
	let displayAccuracy = $derived.by(() => getDisplayAccuracy(problem));

	// Transform solutions to include index for table
	let tableData = $derived.by(() => {
		return solutions.map((solution, index) => ({
			...solution,
			index
		}));
	});

	// Helper function to get solution display name
	function getSolutionName(index: number): string {
		return `Solution ${index + 1}`;
	}

	// Helper function to check if solution is voted by user
	function isUserVotedSolution(index: number): boolean {
		return userVotedSolution === index;
	}

	// Helper function to get vote count for solution
	function getVoteCount(index: number): number {
		return Object.values(groupVotes).filter((vote) => vote === index).length;
	}

	// Helper function to get objective title
	function getObjectiveTitle(objective: any): string {
		if (!objective) return '';
		const tooltip = objective.description || objective.name;
		return objective.unit ? `${tooltip} (${objective.unit})` : tooltip;
	}

	// Table state
	let sorting = $state<SortingState>([]);

	// Define columns for the table
	const columns: ColumnDef<SolutionData>[] = $derived.by(() => {
		return [
			// Solution name column
			{
				accessorKey: 'index',
				header: ({ column }) => renderSnippet(ColumnHeader, { column, title: 'Solution' }),
				cell: ({ row }) => renderSnippet(SolutionNameCell, { solution: row.original }),
				enableSorting: false
			},
			// Add columns for each objective
			...problem.objectives.map((objective, idx) => ({
				accessorKey: objective.symbol,
				header: ({ column }: { column: Column<SolutionData> }) =>
					renderSnippet(ObjectiveColumnHeader, { column, objective, idx }),
				cell: ({ row }: { row: Row<SolutionData> }) =>
					renderSnippet(ObjectiveCell, {
						value: row.original[objective.symbol],
						accuracy: displayAccuracy[idx]
					}),
				enableSorting: true
			})),
			// Vote count column
			{
				accessorKey: 'votes',
				header: ({ column }) => renderSnippet(ColumnHeader, { column, title: 'Votes' }),
				cell: ({ row }) => renderSnippet(VoteCountCell, { solution: row.original }),
				enableSorting: false
			}
		];
	});

	// Create the table
	const table = createSvelteTable<SolutionData>({
		get data() {
			return (tableData || []) as SolutionData[];
		},
		get columns() {
			return columns as ColumnDef<SolutionData, any>[];
		},
		state: {
			get sorting() {
				return sorting;
			}
		},
		onSortingChange: (updater) => {
			if (typeof updater === 'function') {
				sorting = updater(sorting);
			} else {
				sorting = updater;
			}
		},
		getCoreRowModel: getCoreRowModel(),
		getSortedRowModel: getSortedRowModel()
	});

	// Handle row clicks
	function handleRowClick(solution: SolutionData) {
		onSolutionSelect(solution.index, solution);
	}
</script>

{#snippet SolutionNameCell({ solution }: { solution: SolutionData })}
	<div class="font-medium">
		<div class="flex flex-col">
			<span>{getSolutionName(solution.index)}</span>
		</div>
	</div>
{/snippet}

{#snippet ObjectiveColumnHeader({
	column,
	objective,
	idx
}: {
	column: Column<SolutionData>;
	objective: any;
	idx: number;
})}
	<div
		class="flex items-center justify-center"
		style="border-bottom: 4px solid {COLOR_PALETTE[
			idx % COLOR_PALETTE.length
		]}; width: 100%; padding: 0.5rem;"
		title={getObjectiveTitle(objective)}
	>
		<button
			class="flex items-center gap-2 rounded px-2 py-1 hover:bg-gray-50"
			onclick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
		>
			<div class="flex flex-col items-center">
				<span class="font-medium">{objective.name}</span>
				{#if objective.unit}
					<span class="text-xs text-gray-500">({objective.unit})</span>
				{/if}
				<span class="text-xs text-gray-500">({objective.maximize ? 'max' : 'min'})</span>
			</div>
			{#if column.getIsSorted() === 'desc'}
				<ArrowDownIcon class="h-4 w-4" />
			{:else if column.getIsSorted() === 'asc'}
				<ArrowUpIcon class="h-4 w-4" />
			{:else}
				<ChevronsUpDownIcon class="h-4 w-4 opacity-50" />
			{/if}
		</button>
	</div>
{/snippet}

{#snippet ObjectiveCell({
	value,
	accuracy
}: {
	value: number | null | undefined;
	accuracy: number;
})}
	<div class="text-center">
		{value != null ? formatNumber(value, accuracy) : '-'}
	</div>
{/snippet}

{#snippet VoteCountCell({ solution }: { solution: SolutionData })}
	<div class="text-center">
		{#if getVoteCount(solution.index) > 0}
			<span
				class="badge {getVoteCount(solution.index) > 1 ? 'badge-accent' : 'badge-primary'} badge-sm"
			>
				{getVoteCount(solution.index)}
			</span>
		{:else}
			<span class="text-gray-400">0</span>
		{/if}
	</div>
{/snippet}

{#snippet ColumnHeader({ column, title }: { column: Column<SolutionData>; title: string })}
	<div class="px-2 py-1 font-medium">
		{title}
	</div>
{/snippet}

{#if problem && solutions.length > 0}
	<div class="flex h-full flex-col items-start">
		<div class="w-full overflow-auto rounded border shadow-sm">
			<Table.Root>
				<Table.Header>
					{#each table.getHeaderGroups() as headerGroup (headerGroup.id)}
						<Table.Row>
							{#each headerGroup.headers as header (header.id)}
								<Table.Head class="text-center">
									{#if !header.isPlaceholder}
										<FlexRender
											content={header.column.columnDef.header}
											context={header.getContext()}
										/>
									{/if}
								</Table.Head>
							{/each}
						</Table.Row>
					{/each}
				</Table.Header>

				<Table.Body>
					{#each table.getRowModel().rows as row (row.id)}
						<Table.Row
							onclick={() => handleRowClick(row.original)}
							class="cursor-pointer hover:bg-gray-50 {selectedSolution === row.original.index
								? 'border-l-4 border-blue-600 bg-blue-100'
								: ''} {isUserVotedSolution(row.original.index)
								? 'border-l-4 border-green-600 bg-green-50'
								: ''}"
							role="button"
							tabindex={0}
							aria-label="Select solution {row.original.index + 1}"
						>
							{#each row.getVisibleCells() as cell (cell.id)}
								<Table.Cell>
									<FlexRender content={cell.column.columnDef.cell} context={cell.getContext()} />
								</Table.Cell>
							{/each}
						</Table.Row>
					{:else}
						<Table.Row>
							<Table.Cell colspan={columns.length} class="h-24 text-center">
								No solutions available for voting.
							</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		</div>

		<!-- Table Legend -->
		<div class="mt-4 w-full text-sm text-gray-600">
			<div class="flex flex-wrap gap-4">
				<div class="flex items-center gap-2">
					<div class="h-3 w-3 border-l-2 border-blue-600 bg-blue-100"></div>
					<span>Selected for voting</span>
				</div>
				<div class="flex items-center gap-2">
					<div class="h-3 w-3 border-l-2 border-green-600 bg-green-50"></div>
					<span>Your vote</span>
				</div>
				<div class="flex items-center gap-2">
					<span>Click rows to select • Click column headers to sort</span>
				</div>
			</div>
		</div>
	</div>
{:else}
	<div class="py-8 text-center text-gray-500">No solutions available for voting.</div>
{/if}
