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
		multipliers: Record<string, number> | null; // Fixed: Remove nested array
		tradeoffs: Record<string, Record<string, number>> | null;
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
			<div>
				<!-- 				<h4 class="mb-3 text-sm font-semibold">
					{solutions[selectedSolutions[0]].name == null
						? 'Solution ' + (selectedSolutions[0] + 1)
						: solutions[selectedSolutions[0]].name}
				</h4> -->

				<!-- Objective values -->
				<div class="mb-4">
					<div>
						{#if multipliers}
							<div class="mb-4">
								<div class="mb-2 flex flex-row">
									<span class="text-sm"
										>Impact of each objective function value in <span
											class="text-primary font-semibold"
										>
											{solutions[selectedSolutions[0]].name == null
												? 'Solution ' + (selectedSolutions[0] + 1)
												: solutions[selectedSolutions[0]].name}</span
										>.</span
									>

									<Tooltip.Root>
										<Tooltip.Trigger><InfoIcon class="h-5 w-5" /></Tooltip.Trigger>
										<Tooltip.Content side="right" class="tooltip-content">
											The height of each bar represents how strongly each objective function
											influences the selected solution (<span class="text-primary font-semibold"
												>{solutions[selectedSolutions[0]].name == null
													? 'Solution ' + (selectedSolutions[0] + 1)
													: solutions[selectedSolutions[0]].name}</span
											>). When you select an objective function, you can see how improving it by one
											unit affects the other objective functions.
										</Tooltip.Content>
									</Tooltip.Root>
								</div>

								<div>
									<ExpBarchart
										data={multipliers && selectedSolutions.length > 0
											? Object.entries(multipliers).map(([key, value]) => {
													const obj = problem.objectives.find((o) => o.symbol === key);
													return {
														name: obj?.name ?? key,
														symbol: key,
														value: -1 * value,
														direction: obj?.maximize ? 'max' : 'min'
													};
												})
											: []}
										options={{ showLabels: true, type: 'multipliers' }}
										onSelect={handleObjectiveClick}
										selected_objective_symbol={selectedObjectiveSymbol}
									/>
								</div>
								<span class="text-sm"> Select an objective function you want to improve. </span>

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
								<div>
									{#if selectedObjectiveSymbol !== null && selectedObjectiveSymbol !== undefined && tradeoffs}
										<div class="my-4 mb-2 flex flex-row">
											<span class="text-sm"
												>Estimated impairment in other objective functions when <span
													class="text-primary font-semibold"
													>{objectiveNames[selectedObjectiveSymbol] ||
														selectedObjectiveSymbol}</span
												> is improved by one unit, ranked from most to least impaired.</span
											>

											<Tooltip.Root>
												<Tooltip.Trigger><InfoIcon class="h-5 w-5" /></Tooltip.Trigger>
												<Tooltip.Content side="right" class="tooltip-content">
													<p>
														The values represent local effects near
														<span class="text-primary font-semibold"
															>{solutions[selectedSolutions[0]].name == null
																? 'Solution ' + (selectedSolutions[0] + 1)
																: solutions[selectedSolutions[0]].name}</span
														>. They indicate how much each objective function is expected to be
														impaired if the selected objective function (<span
															class="text-primary font-semibold"
															>{objectiveNames[selectedObjectiveSymbol] ||
																selectedObjectiveSymbol}</span
														>) is improved by one unit.
													</p>
												</Tooltip.Content>
											</Tooltip.Root>
										</div>
										<!-- 										<ExpBarchart
											data={tradeoffs && selectedObjectiveSymbol
												? formatTradeofftoDict(tradeoffs[selectedObjectiveSymbol], problem)
												: []}
											options={{ showLabels: false, type: 'tradeoffs' }}
											onSelect={handleObjectiveClick}
											selected_objective_symbol={selectedObjectiveSymbol}
										/> -->
										<ExpRankingBarchart
											data={tradeoffs && selectedObjectiveSymbol
												? formatTradeofftoDict(tradeoffs[selectedObjectiveSymbol], problem)
												: []}
											options={{ showLabels: false }}
											onSelect={handleTradeoffClick}
											selectedBarSymbol={selectedTradeoffSymbol}
											selected_objective_symbol={selectedObjectiveSymbol}
										/>

										{#if selectedTradeoffSymbol !== null && selectedTradeoffSymbol !== undefined && selectedTradeoffSymbol !== ''}
											<p>
												Improving <span class="text-primary font-semibold"
													>{objectiveNames[selectedObjectiveSymbol] ||
														selectedObjectiveSymbol}</span
												>
												in one unit is expected to impair
												<span class="text-primary font-semibold"
													>{objectiveNames[selectedTradeoffSymbol] || selectedTradeoffSymbol}</span
												>
												in {Math.abs(
													tradeoffs[selectedObjectiveSymbol][selectedTradeoffSymbol]
												).toFixed(4)} units.
											</p>
										{/if}
									{/if}
								</div>
							</div>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	</Sidebar.Content>
	<Sidebar.Rail />
</Sidebar.Root>
