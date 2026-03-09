<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import InfoIcon from '@lucide/svelte/icons/info';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors.js';

	import { PREFERENCE_TYPES, SIGNIFICANT_DIGITS } from '$lib/constants/index.js';
	import { getValueRange } from '$lib/components/visualizations/utils/math';
	import type { ProblemInfo, Solution, SolutionType, MethodMode, PeriodKey } from '$lib/types';
	import ExpBarchart from '$lib/components/visualizations/barchart/exp-barchart.svelte';
	import ExpRankingBarchart from '$lib/components/visualizations/barchart/exp-ranking-barchart.svelte';
	import { Combobox } from '$lib/components/ui/combobox';
	import type { symbol } from 'd3';

	interface Props {
		problem: ProblemInfo;
		preferenceValues: number[];
		solutions: Array<Solution>;
		multipliers: Record<string, number> | null;
		tradeoffs: Record<string, Record<string, number>> | null;
		currentObjectiveValues?: Record<string, number> | null;
		selectedSolutions?: Array<number>;
		selectedObjectiveSymbol?: string | null;
		selectedTradeoffSymbol?: string | null;
		handleObjectiveClick?: (event: { value: string }) => void;
		handleTradeoffClick?: (event: { value: string }) => void;
		ref?: HTMLElement | null;
	}

	let {
		problem,
		preferenceValues,
		solutions,
		multipliers,
		tradeoffs,
		currentObjectiveValues = null,
		selectedSolutions,
		selectedObjectiveSymbol,
		selectedTradeoffSymbol,
		handleObjectiveClick,
		handleTradeoffClick,
		ref = null
	}: Props = $props();
	// Create a dictionary of objective names and their symbols
	const objectiveNames: Record<string, string> = {};

	problem.objectives.forEach((obj) => {
		objectiveNames[obj.symbol] = obj.name ?? obj.symbol;
	});

	function formatTradeofftoDict(tradeoffs_row: Record<string, number>, problem: ProblemInfo) {
		if (tradeoffs_row && problem) {
			const formatedDict: Array<{
				name: string;
				symbol: string;
				value: number;
				direction: 'max' | 'min';
			}> = [];
			problem.objectives.forEach((obj) => {
				formatedDict.push({
					name: obj.name ?? obj.symbol,
					symbol: obj.symbol,
					value: tradeoffs_row[obj.symbol],
					direction: obj.maximize ? 'max' : 'min'
				});
			});
			console.log('formatedDict', formatedDict);
			return formatedDict;
		}
		return undefined;
	}

	// Compute current objective values from selected solution
	const selectedSolutionObjectiveValues = $derived.by(() => {
		if (!selectedSolutions || selectedSolutions.length === 0 || !solutions[selectedSolutions[0]]) {
			return null;
		}
		const selectedSolution = solutions[selectedSolutions[0]];
		// objective_values is already an object mapping symbol -> value
		return selectedSolution.objective_values || null;
	});

		const highestTradeoffObjectiveSymbol = $derived.by(() => {
		if (!tradeoffs || !selectedObjectiveSymbol || !tradeoffs[selectedObjectiveSymbol]) {
			return null;
		}

		let highestSymbol: string | null = null;
		let highestValue = -Infinity;
		const selectedRow = tradeoffs[selectedObjectiveSymbol];

		for (const [symbol, value] of Object.entries(selectedRow)) {
			if (symbol === selectedObjectiveSymbol) {
				continue;
			}

			const absValue = Math.abs(value);
			if (absValue > highestValue) {
				highestValue = absValue;
				highestSymbol = symbol;
			}
		}

		return highestSymbol;
	});

	const highestTradeoffObjectiveName = $derived(
		highestTradeoffObjectiveSymbol
			? objectiveNames[highestTradeoffObjectiveSymbol] || highestTradeoffObjectiveSymbol
			: 'N/A'
	);

	// Format number with significant digits, avoiding "0.00" for very small values
	function formatTradeoffValue(value: number): string {
		const absValue = Math.abs(value);
		if (absValue === 0) return '0';
		
		// For very small numbers, use scientific notation
		if (absValue < 0.001) {
			return absValue.toExponential(SIGNIFICANT_DIGITS);
		}
		
		// For values less than 1, show enough decimals to capture significant digits
		if (absValue < 1) {
			return absValue.toPrecision(SIGNIFICANT_DIGITS);
		}
		
		// For larger values, use fixed decimal places
		return absValue.toFixed(SIGNIFICANT_DIGITS);
	}

	function formatMultiplierToDict(multipliers: Record<string, number>, problem: ProblemInfo) {
		if (multipliers && problem) {
			const formatedDict: Array<{
				name: string;
				symbol: string;
				value: number;
				direction: 'max' | 'min';
			}> = [];
			problem.objectives.forEach((obj) => {
				formatedDict.push({
					name: obj.name ?? obj.symbol,
					symbol: obj.symbol,
					value: -1 * multipliers[obj.symbol],
					direction: obj.maximize ? 'max' : 'min'
				});
			});
			return formatedDict;
		}
		return undefined;
	}

</script>

<Sidebar.Root side="right" class="fixed top-12 right-0 h-[calc(100vh-3rem)]">
	<Sidebar.Header>
		<span class="text-sm font-semibold">Explanations</span>
	</Sidebar.Header>
	<Sidebar.Content class="px-4">
		{#if solutions.length === 0 || multipliers === null}
			<div class="py-8 text-center text-sm text-gray-500">No solutions available to analyze.</div>
		{:else if selectedSolutions == null || selectedSolutions.length === 0}
			<div class="py-8 text-center text-sm text-gray-500">
				Please select a solution to view its explanations.
			</div>
		{:else}
			<div class="space-y-6">
				{#if multipliers}
					<!-- Impact Section -->
					<div class="space-y-3">
						<div class="flex items-center gap-2">
							<h3 class="text-sm font-semibold">
								Impact Analysis for 
								<span class="text-primary">
									{solutions[selectedSolutions[0]].name == null
										? 'Solution ' + (selectedSolutions[0] + 1)
										: solutions[selectedSolutions[0]].name}
								</span>
							</h3>
							<Tooltip.Root>
								<Tooltip.Trigger><InfoIcon class="h-4 w-4 text-gray-400" /></Tooltip.Trigger>
								<Tooltip.Content side="right" class="tooltip-content max-w-xs">
									The height of each bar represents how strongly each objective function
									influences the selected solution. When you select an objective function, you can see how improving it affects the other objectives.
								</Tooltip.Content>
							</Tooltip.Root>
						</div>

						<div class="bg-gray-50 rounded-lg p-3">
							<ExpBarchart
								data={formatMultiplierToDict(multipliers, problem)}
								options={{ showLabels: true, type: 'multipliers' }}
								onSelect={handleObjectiveClick}
								selected_objective_symbol={selectedObjectiveSymbol}
							/>
						</div>
					</div>

					<!-- Objective Selection Section -->
					<div class="space-y-2">
						<label class="text-sm font-medium text-gray-700">
							Select objective function to improve
						</label>
						<Combobox
							placeholder="Select Objective to View Trade-offs"
							width={300}
							options={objectiveNames
								? problem.objectives.map((obj, idx) => ({
										label: objectiveNames[obj.symbol] || obj.symbol,
										value: obj.symbol
									}))
								: []}
							defaultSelected={selectedObjectiveSymbol !== null &&
							selectedObjectiveSymbol !== undefined
								? selectedObjectiveSymbol
								: ''}
							onChange={(value) => {
								if (handleObjectiveClick) {
									handleObjectiveClick(value);
								}
							}}
						/>
					</div>

					{#if selectedObjectiveSymbol !== null && selectedObjectiveSymbol !== undefined && selectedObjectiveSymbol !== ''}
						{#if tradeoffs && selectedObjectiveSymbol}
							<!-- Tradeoff Ranking Section -->
							<div class="border-t pt-4 space-y-4">
								<div class="flex items-center gap-2">
									<h3 class="text-sm font-semibold text-primary">Tradeoff Ranking</h3>
									<Tooltip.Root>
										<Tooltip.Trigger class="w-4 h-4 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold hover:bg-blue-200 cursor-help">
											?
										</Tooltip.Trigger>
										<Tooltip.Content class="text-sm max-w-xs">
											Click on any bar to see their expected changes when improving <span class="font-semibold">{objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol}</span>
										</Tooltip.Content>
									</Tooltip.Root>
								</div>

								<p class="text-sm text-gray-600">
									Tradeoff levels ranked from the strongest to the weakest.
								</p>

								<div class="bg-gray-50 rounded-lg p-3">
									<ExpRankingBarchart
										data={formatTradeofftoDict(tradeoffs[selectedObjectiveSymbol], problem)}
										options={{ showLabels: false }}
										onSelect={handleTradeoffClick}
										selectedBarSymbol={selectedTradeoffSymbol}
										selected_objective_symbol={selectedObjectiveSymbol}
									/>
								</div>

								<!-- Decision Guidance -->
								<div class="flex bg-amber-50 border-l-4 border-amber-400 rounded-r-lg p-3 space-y-2">
									<p class="text-sm font-semibold text-amber-900">
										{objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol} is most strongly impaired by {highestTradeoffObjectiveName}
									</p>
									<Tooltip.Root>
										<Tooltip.Trigger><InfoIcon class="h-4 w-4 text-amber-600" /></Tooltip.Trigger>
										<Tooltip.Content side="right" class="tooltip-content max-w-xs">
											To improve {objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol}, at least one other objective needs to be impaired. If you do not want to impair {highestTradeoffObjectiveName}, choose a lower ranked objective. Lower ranked objectives usually mean a smaller impact. 
										</Tooltip.Content>
									</Tooltip.Root>
								</div>

								{#if selectedTradeoffSymbol !== null && selectedTradeoffSymbol !== undefined && selectedTradeoffSymbol !== ''}
									<!-- Selected Tradeoff Details -->
									<div class="bg-purple-50 border-l-4 border-purple-400 rounded-r-lg p-3">
										<p class="text-sm font-semibold text-purple-900 mb-1">Tradeoff Rate</p>
										<p class="text-sm text-purple-800">
											Improving <span class="font-semibold">{objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol}</span> by one unit will impair 
											<span class="font-semibold">{objectiveNames[selectedTradeoffSymbol] || selectedTradeoffSymbol}</span> by approximately
											<span class="font-semibold">{formatTradeoffValue(tradeoffs[selectedObjectiveSymbol][selectedTradeoffSymbol])}</span> units.
										</p>
									</div>
								{/if}
							</div>
						{/if}
					{/if}
				{/if}
			</div>
		{/if}
	</Sidebar.Content>
	<Sidebar.Rail />
</Sidebar.Root>
