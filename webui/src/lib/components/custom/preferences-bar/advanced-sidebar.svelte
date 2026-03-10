<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import InfoIcon from '@lucide/svelte/icons/info';
	import AlertTriangleIcon from '@lucide/svelte/icons/alert-triangle';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors.js';

	import { PREFERENCE_TYPES, SIGNIFICANT_DIGITS } from '$lib/constants/index.js';
	import { getValueRange } from '$lib/components/visualizations/utils/math';
	import type { ProblemInfo, Solution, SolutionType, MethodMode, PeriodKey } from '$lib/types';
	import ExpBarchart from '$lib/components/visualizations/barchart/exp-barchart.svelte';
	import ExpRankingBarchart from '$lib/components/visualizations/barchart/exp-ranking-barchart.svelte';
	import { Combobox } from '$lib/components/ui/combobox';
	import type { symbol } from 'd3';
	import { cons } from 'effect/List';

	interface Props {
		problem: ProblemInfo;
		preferenceValues: number[];
		solutions: Array<Solution>;
		multipliers: Record<string, number> | null;
		tradeoffs: Record<string, Record<string, number>> | null;
		activeObjectives: Array<string>;
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
		activeObjectives,
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

	const activeObjectiveLabels = $derived(
		activeObjectives.map((sym) => objectiveNames[sym] || sym).join(', ')
	);

	const inactiveObjectiveLabels = $derived(
		problem.objectives
			.filter((obj) => !activeObjectives.includes(obj.symbol))
			.map((obj) => objectiveNames[obj.symbol] || obj.symbol)
			.join(', ')
	);

	const inactiveObjectiveCount = $derived(
		problem.objectives.filter((obj) => !activeObjectives.includes(obj.symbol)).length
	);

	const isTradeoffOutsideActiveObjectives = $derived(
		(selectedObjectiveSymbol && !activeObjectives.includes(selectedObjectiveSymbol)) ||
		(selectedTradeoffSymbol && !activeObjectives.includes(selectedTradeoffSymbol))
	);

	const isSelectedObjectiveActive = $derived(
		selectedObjectiveSymbol ? activeObjectives.includes(selectedObjectiveSymbol) : false
	);
	const isSelectedTradeoffActive = $derived(
		selectedTradeoffSymbol ? activeObjectives.includes(selectedTradeoffSymbol) : false
	);

	//Check if its outside the range of the ideal and nadir values for that objective (ideal - nadir is the range where we expect to see tradeoffs, outside of that the tradeoff values might be less reliable)
	const isOutsideRange = (value: number, objectiveSymbol: string) => {
		const ideal = problem.objectives.find((obj) => obj.symbol === objectiveSymbol)?.ideal;
		const nadir = problem.objectives.find((obj) => obj.symbol === objectiveSymbol)?.nadir;

		console.log('Ideal and nadir values for', objectiveSymbol, ':', ideal, nadir);
		if (ideal === undefined || nadir === undefined || ideal ===null || nadir ===null) return false;

		const [min, max] = ideal < nadir ? [ideal, nadir] : [nadir, ideal];

		const range = max - min;
		console.log('Checking range for', objectiveSymbol, 'value:', value, 'ideal:', ideal, 'nadir:', nadir);
	
		console.log('Value is outside range:', value < min, value > max, 'with range:', range);
		return Math.abs(value) > range;
	};

	// Calculate the rank of the selected tradeoff (1 = strongest, higher = weaker)
	const selectedTradeoffRank = $derived.by(() => {
		if (!tradeoffs || !selectedObjectiveSymbol || !selectedTradeoffSymbol || !tradeoffs[selectedObjectiveSymbol]) {
			return null;
		}

		const selectedRow = tradeoffs[selectedObjectiveSymbol];
		const sortedEntries = Object.entries(selectedRow)
			.filter(([symbol]) => symbol !== selectedObjectiveSymbol)
			.sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));

		const rank = sortedEntries.findIndex(([symbol]) => symbol === selectedTradeoffSymbol) + 1;
		return rank > 0 ? rank : null;
	});

	// Get descriptive text for tradeoff strength
	const tradeoffStrengthText = $derived.by(() => {
		if (selectedTradeoffRank === null || selectedTradeoffRank === 0) return 'a tradeoff';
		if (selectedTradeoffRank === 1) return 'a strong tradeoff';
		if (selectedTradeoffRank === 2) return 'a moderate tradeoff';
		return 'a slight tradeoff';
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
						{#if activeObjectives.length > 0}
							<div class=" bg-amber-50 border-l-4 border-amber-400 rounded-r-lg p-3 space-y-2 text-amber-900">
								<p class="text-sm leading-relaxed text-amber-900">
									The objectives that influence this solution are
									<span class="font-semibold"> {activeObjectiveLabels}</span>.
								</p>
									{#if inactiveObjectiveCount === 0}
										<p class="mt-1 text-sm leading-relaxed text-amber-800">No other objectives currently affect the trade-offs.</p>
									{:else}
										<p class="mt-1 text-sm leading-relaxed text-amber-800">
											<span class="font-semibold">{inactiveObjectiveLabels}</span> currently {inactiveObjectiveCount === 1 ? 'has' : 'have'} little impact on the trade-offs.
										</p>
									{/if}
							</div>
						{/if}
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
										<Tooltip.Content class="tooltip-content max-w-xs">
										<p>
														The values represent local effects near
														<span class="text-primary font-semibold"
															>{solutions[selectedSolutions[0]].name == null
																? 'Solution ' + (selectedSolutions[0] + 1)
																: solutions[selectedSolutions[0]].name}</span
														>. TIP: To improve
														<span class="text-primary font-semibold"
															>{objectiveNames[selectedObjectiveSymbol] ||
																selectedObjectiveSymbol}</span
														> impair the objective function with the highest rank in the plot.
													</p>
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
<!-- 								<div class="flex bg-amber-50 border-l-4 border-amber-400 rounded-r-lg p-3 space-y-2">
									<p class="text-sm font-semibold text-amber-900">
										{objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol} is most strongly impaired by {highestTradeoffObjectiveName}
									</p>
									<Tooltip.Root>
										<Tooltip.Trigger><InfoIcon class="h-4 w-4 text-amber-600" /></Tooltip.Trigger>
										<Tooltip.Content side="right" class="tooltip-content max-w-xs">
											To improve {objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol}, at least one other objective needs to be impaired. If you do not want to impair {highestTradeoffObjectiveName}, choose a lower ranked objective. Lower ranked objectives usually mean a smaller impact. 
										</Tooltip.Content>
									</Tooltip.Root>
								</div> -->

{#if selectedTradeoffSymbol !== null && selectedTradeoffSymbol !== undefined && selectedTradeoffSymbol !== ''}
	<!-- Selected Tradeoff Details -->
	<div class="bg-purple-50 border-l-4 border-purple-400 rounded-r-lg p-3">
		<div class="flex items-center gap-2 mb-1">
			<p class="text-sm font-semibold text-purple-900">
				{#if isTradeoffOutsideActiveObjectives}
					Tradeoff Information
<!-- 					<Tooltip.Root>
					<Tooltip.Trigger><AlertTriangleIcon class="h-4 w-4 text-amber-600" /></Tooltip.Trigger>
					<Tooltip.Content side="right" class="tooltip-content max-w-xs">
						<div class="mt-2 text-xs items-start gap-1">
	<span class="font-semibold">Use with caution:</span>
	<span>
		The current solution does not provide reliable trade-off estimates for
		<span class="font-semibold">{objectiveNames[selectedObjectiveSymbol]}</span>.
		This ranking should be treated as exploratory.
	</span>
</div>
					</Tooltip.Content>
				</Tooltip.Root> -->
				{:else}
					Tradeoff Rate
				{/if}
			</p>

			
<!-- 				<Tooltip.Root>
					<Tooltip.Trigger><InfoIcon class="h-4 w-4 text-purple-600" /></Tooltip.Trigger>
					<Tooltip.Content side="right" class="tooltip-content max-w-xs">
						This solution does not clearly show how improving
						{objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol}
						would affect
						{objectiveNames[selectedTradeoffSymbol] || selectedTradeoffSymbol}.
					</Tooltip.Content>
				</Tooltip.Root> -->
			
		</div>

		<p class="text-sm text-purple-800">
			{#if isTradeoffOutsideActiveObjectives}
		The current solution does not provide reliable trade-off estimates for
		<span class="font-semibold">{!isSelectedObjectiveActive ? objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol : !isSelectedTradeoffActive ? objectiveNames[selectedTradeoffSymbol] || selectedTradeoffSymbol : ''}</span>.
		This ranking should be treated as exploratory.
			{:else}
				{#if isOutsideRange(tradeoffs[selectedObjectiveSymbol][selectedTradeoffSymbol], selectedTradeoffSymbol)}
					The current solution does not provide reliable trade-off estimates between
					<span class="font-semibold">{objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol}</span> and
					<span class="font-semibold">{objectiveNames[selectedTradeoffSymbol] || selectedTradeoffSymbol}</span>. 
					
				{:else}

				Improving <span class="font-semibold">{objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol}</span> by one unit will impair
				<span class="font-semibold">{objectiveNames[selectedTradeoffSymbol] || selectedTradeoffSymbol}</span> by approximately
				<span class="font-semibold">{formatTradeoffValue(tradeoffs[selectedObjectiveSymbol][selectedTradeoffSymbol])}</span> units.
				{/if}
			{/if}
		</p>

<!-- 		{#if isTradeoffOutsideActiveObjectives}
			<p class="mt-2 text-sm text-purple-700">
				To understand it better, explore a solution where
				<span class="font-semibold">{objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol}</span>
				has more influence.
			</p>
		{/if} -->
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
