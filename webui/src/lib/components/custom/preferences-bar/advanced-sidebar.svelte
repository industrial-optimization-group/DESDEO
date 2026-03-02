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
		allPreferenceSuggestions?: Record<string, any> | null;
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
		allPreferenceSuggestions = null,
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

	// Derived reactive variables for preference suggestions
	const currentSuggestions = $derived(
		selectedObjectiveSymbol && allPreferenceSuggestions && allPreferenceSuggestions[selectedObjectiveSymbol]
			? allPreferenceSuggestions[selectedObjectiveSymbol]
			: null
	);

	const primaryConflicts = $derived(currentSuggestions?.primary_conflicts || []);
	const resilient = $derived(currentSuggestions?.resilient_objectives || []);

	// Compute current objective values from selected solution
	const selectedSolutionObjectiveValues = $derived.by(() => {
		if (!selectedSolutions || selectedSolutions.length === 0 || !solutions[selectedSolutions[0]]) {
			return null;
		}
		const selectedSolution = solutions[selectedSolutions[0]];
		// objective_values is already an object mapping symbol -> value
		return selectedSolution.objective_values || null;
	});

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
								<!-- Preference Suggestions Section (PRIMARY - shown first) -->
								{#if selectedObjectiveSymbol && currentSuggestions}
									<div class="mt-4 pt-4 border-t border-gray-200">
										<div class="mb-3 flex flex-row items-center gap-2">
											<span class="text-sm font-semibold">✨ Recommended Actions</span>
											<Tooltip.Root>
												<Tooltip.Trigger><InfoIcon class="h-4 w-4" /></Tooltip.Trigger>
												<Tooltip.Content side="right" class="tooltip-content max-w-xs">
													<p>
														Based on the tradeoff analysis, here's what to adjust to improve
														<span class="text-primary font-semibold"
															>{objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol}</span
														>.
													</p>
												</Tooltip.Content>
											</Tooltip.Root>
										</div>

										<!-- Primary action: improve selected objective -->
										<div class="mb-3 p-3 bg-blue-50 rounded">
											<div class="flex items-start justify-between gap-2">
												<div class="flex-1">
													<p class="font-semibold text-blue-700 text-sm mb-2">
														To improve {objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol}:
													</p>
													<div class="text-xs text-blue-900 mb-2 space-y-1">
														<div class="flex justify-between">
															<span>Current solution value:</span>
															<span class="font-mono font-semibold"
																>{selectedSolutionObjectiveValues && selectedObjectiveSymbol
																	? selectedSolutionObjectiveValues[selectedObjectiveSymbol]?.toFixed(4)
																	: 'N/A'}
																</span
															>
														</div>
														<div class="flex justify-between text-green-700">
															<span>Suggested aspiration:</span>
															<span class="font-mono font-semibold"
																>{currentSuggestions.suggested_preferences[selectedObjectiveSymbol]?.toFixed(4) ||
																	'N/A'}</span
															>
														</div>
													</div>
													<p class="text-xs text-blue-700 italic">
														({currentSuggestions.improvement_direction}) ~25% improvement from current
													</p>
												</div>
												<Tooltip.Root>
													<Tooltip.Trigger><InfoIcon class="h-4 w-4 flex-shrink-0 text-blue-600" /></Tooltip.Trigger>
													<Tooltip.Content side="right" class="tooltip-content max-w-xs">
														<p>
															This suggestion is 25% better than the current objective value (or 25% of the way toward the bound if available). It's an ambitious but feasible target based on the solution space.
														</p>
													</Tooltip.Content>
												</Tooltip.Root>
											</div>
										</div>

										{#if primaryConflicts.length > 0}
											<div class="mb-3 p-3 bg-red-50 rounded">
												<div class="flex items-start gap-2 mb-2">
													<p class="font-semibold text-red-700 text-sm">
														⚠️ Expected impacts on objectives with strong tradeoffs:
													</p>
													<Tooltip.Root>
														<Tooltip.Trigger><InfoIcon class="h-4 w-4 flex-shrink-0 text-red-600" /></Tooltip.Trigger>
														<Tooltip.Content side="right" class="tooltip-content max-w-xs">
															<p>
																These objectives are heavily affected when improving
																<span class="text-primary font-semibold"
																	>{objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol}</span
																>. The suggested values are slightly relaxed from the current solution to make
																room for improvement.
															</p>
														</Tooltip.Content>
													</Tooltip.Root>
												</div>
												<div class="text-red-600 space-y-2 text-xs">
													{#each primaryConflicts as objSymbol}
														<div class="border-l-2 border-red-300 pl-2">
															<div class="flex justify-between items-start mb-1">
																<span class="font-semibold">{objectiveNames[objSymbol] || objSymbol}</span>
															</div>
															<div class="space-y-0.5 text-red-700">
																<div class="flex justify-between">
																	<span class="text-gray-600">Current:</span>
																	<span class="font-mono"
																		>{selectedSolutionObjectiveValues && objSymbol
																			? selectedSolutionObjectiveValues[objSymbol]?.toFixed(4)
																			: 'N/A'}</span
																	>
																</div>
																<div class="flex justify-between">
																	<span class="font-semibold">→ Suggested:</span>
																	<span class="font-mono font-semibold"
																		>{currentSuggestions.suggested_preferences[objSymbol]?.toFixed(4) ||
																			'N/A'}</span
																	>
																</div>
															</div>
															{#if currentSuggestions.preferences_explanations[objSymbol]}
																<p class="text-red-600 italic text-xs mt-1">
																	{currentSuggestions.preferences_explanations[objSymbol].split(':')[0]}
																</p>
															{/if}
														</div>
													{/each}
												</div>
											</div>
										{/if}

										{#if resilient.length > 0}
											<div class="mb-3 p-3 bg-green-50 rounded">
												<div class="flex items-start gap-2 mb-2">
													<p class="font-semibold text-green-700 text-sm">✓ Objectives resilient to changes:</p>
													<Tooltip.Root>
														<Tooltip.Trigger><InfoIcon class="h-4 w-4 flex-shrink-0 text-green-600" /></Tooltip.Trigger>
														<Tooltip.Content side="right" class="tooltip-content max-w-xs">
															<p>
																These objectives are barely affected when improving
																<span class="text-primary font-semibold"
																	>{objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol}</span
																>. You can slightly tighten them with minimal impact.
															</p>
														</Tooltip.Content>
													</Tooltip.Root>
												</div>
												<div class="text-green-600 space-y-2 text-xs">
													{#each resilient as objSymbol}
														<div class="border-l-2 border-green-300 pl-2">
															<div class="flex justify-between items-start mb-1">
																<span class="font-semibold">{objectiveNames[objSymbol] || objSymbol}</span>
															</div>
															<div class="space-y-0.5 text-green-700">
																<div class="flex justify-between">
																	<span class="text-gray-600">Current:</span>
																	<span class="font-mono"
																		>{selectedSolutionObjectiveValues && objSymbol
																			? selectedSolutionObjectiveValues[objSymbol]?.toFixed(4)
																			: 'N/A'}</span
																	>
																</div>
																<div class="flex justify-between">
																	<span class="font-semibold">→ Suggested:</span>
																	<span class="font-mono font-semibold"
																		>{currentSuggestions.suggested_preferences[objSymbol]?.toFixed(4) ||
																			'N/A'}</span
																	>
																</div>
															</div>
														</div>
													{/each}
												</div>
											</div>
										{/if}

										<!-- Tradeoff ranking chart as secondary detail -->
										{#if tradeoffs && selectedObjectiveSymbol}
											<div class="mt-4 pt-3 border-t border-gray-200">
												<div class="flex items-center gap-2 mb-2">
													<p class="text-xs font-semibold text-gray-600">📊 Tradeoff Ranking (details)</p>
													<Tooltip.Root>
														<Tooltip.Trigger class="w-4 h-4 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold hover:bg-blue-200 cursor-help">
															?
														</Tooltip.Trigger>
														<Tooltip.Content class="text-xs max-w-xs">
															Click on any bar to see how to adjust that objective when improving <span class="font-semibold">{objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol}</span>
														</Tooltip.Content>
													</Tooltip.Root>
												</div>
												<ExpRankingBarchart
													data={formatTradeofftoDict(tradeoffs[selectedObjectiveSymbol], problem)}
													options={{ showLabels: false }}
													onSelect={handleTradeoffClick}
													selectedBarSymbol={selectedTradeoffSymbol}
													selected_objective_symbol={selectedObjectiveSymbol}
												/>
												{#if selectedTradeoffSymbol !== null && selectedTradeoffSymbol !== undefined && selectedTradeoffSymbol !== ''}
													<div class="mt-3 p-3 bg-purple-50 rounded">
														<p class="text-xs font-semibold text-purple-700 mb-2">
															If you improve {objectiveNames[selectedObjectiveSymbol] || selectedObjectiveSymbol}, handle {objectiveNames[selectedTradeoffSymbol] || selectedTradeoffSymbol} as follows:
														</p>
														<div class="text-xs text-purple-800 space-y-1">
															<div class="flex justify-between">
																<span>Current:</span>
																<span class="font-mono font-semibold"
																	>{selectedSolutionObjectiveValues && selectedTradeoffSymbol
																		? selectedSolutionObjectiveValues[selectedTradeoffSymbol]?.toFixed(4)
																		: 'N/A'}</span
																>
															</div>
															<div class="flex justify-between">
																<span>Suggested:</span>
																<span class="font-mono font-semibold text-purple-900"
																	>{currentSuggestions.suggested_preferences[selectedTradeoffSymbol]?.toFixed(4) || 'N/A'}</span
																>
															</div>
															{#if currentSuggestions.preferences_explanations[selectedTradeoffSymbol]}
																<p class="text-purple-700 italic mt-1">
																	{currentSuggestions.preferences_explanations[selectedTradeoffSymbol].split(':')[0]}
																</p>
															{/if}
														</div>
													</div>
												{/if}
											</div>
										{/if}
									</div>
								{/if}
							</div>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	</Sidebar.Content>
	<Sidebar.Rail />
</Sidebar.Root>
