<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import InfoIcon from '@lucide/svelte/icons/info';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors.js';

	import { PREFERENCE_TYPES, SIGNIFICANT_DIGITS } from '$lib/constants/index.js';
	import { getValueRange } from '$lib/components/visualizations/utils/math';
	import type { ProblemInfo, Solution, SolutionType, MethodMode, PeriodKey } from '$lib/types';
	import ExpBarchart from '$lib/components/visualizations/barchart/exp-barchart.svelte';
	import { Combobox } from '$lib/components/ui/combobox';

	interface Props {
		problem: ProblemInfo;
		preferenceValues: number[];
		solutions: Array<Solution>;
		multipliers: Record<string, number> | null; // Fixed: Remove nested array
		tradeoffs: number[][] | null;
		selectedSolutions?: Array<number>;
		selectedObjectiveIndex?: number | null;
		handleObjectiveClick?: (index: number) => void;
		ref?: HTMLElement | null;
	}

	let {
		problem,
		preferenceValues,
		solutions,
		multipliers,
		tradeoffs,
		selectedSolutions,
		selectedObjectiveIndex,
		handleObjectiveClick,
		ref = null
	}: Props = $props();
	// Create a dictionary of objective names and their symbols
	const objectiveNames: Record<string, string> = {};
	problem.objectives.forEach((obj) => {
		objectiveNames[obj.symbol] = obj.name ?? obj.symbol;
	});

	// Get the row corresponding to the selected objective index from tradeoffs
	function formatTradeofftoDict(
		tradeoffs: number[][] | null,
		selectedObjectiveIndex: number | null | undefined
	) {
		if (!tradeoffs || selectedObjectiveIndex === null || selectedObjectiveIndex === undefined)
			return {};
		const row_tradeoff = selectedObjectiveIndex !== null ? tradeoffs[selectedObjectiveIndex] : null;
		if (!row_tradeoff) return {};

		const tradeoffDict: Record<string, number> = {};
		problem.objectives.forEach((obj, idx) => {
			tradeoffDict[obj.symbol] = row_tradeoff[idx];
		});
		return tradeoffDict;
	}
</script>

<Sidebar.Root side="right" class="fixed right-0 top-12 h-[calc(100vh-3rem)]">
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
											influences the selected solution ({solutions[selectedSolutions[0]].name ==
											null
												? 'Solution ' + (selectedSolutions[0] + 1)
												: solutions[selectedSolutions[0]].name}). When you select an objective
											function, you can see how improving it by one unit affects the other objective
											functions.
										</Tooltip.Content>
									</Tooltip.Root>
								</div>
								<span class="text-sm"> Select an objective function you want to improve. </span>

								<div>
									<!-- 								{#each Object.entries(multipliers[0] ?? {}) as [objName, value]}
										<div class="flex justify-between rounded bg-blue-50 p-2 text-xs">
											<span class="font-medium">{objName}:</span>
											<span class="font-mono"
												>{formatNumber(Number(value), SIGNIFICANT_DIGITS)}</span
											>
										</div>
									{/each} -->

									<ExpBarchart
										data={Object.entries(multipliers ?? {}).map(([objName, value]) => ({
											name: objectiveNames[objName] || objName,
											value: Number(-1 * value),
											direction: 'min'
										}))}
										options={{ showLabels: true, orientation: 'vertical' }}
										onSelect={handleObjectiveClick}
									/>
								</div>
								<!-- <Combobox
									placeholder="Select Objective to View Trade-offs"
									width={300}
									options={objectiveNames
										? problem.objectives.map((obj, idx) => ({
												label: objectiveNames[obj.symbol] || obj.symbol,
												value: idx.toString()
											}))
										: []}
									defaultSelected={selectedObjectiveIndex !== null &&
									selectedObjectiveIndex !== undefined
										? objectiveNames[problem.objectives[selectedObjectiveIndex].symbol] ||
											problem.objectives[selectedObjectiveIndex].symbol
										: undefined}
									onChange={undefined}
								/> -->
								<div>
									{#if selectedObjectiveIndex !== null && selectedObjectiveIndex !== undefined && tradeoffs}
										<div class="my-4 mb-2 flex flex-row">
											<span class="text-sm"
												>Estimated changes in other objective functions when <span
													class="text-primary font-semibold"
													>{objectiveNames[problem.objectives[selectedObjectiveIndex].symbol] ||
														problem.objectives[selectedObjectiveIndex].symbol}</span
												> is improved by one unit.</span
											>

											<Tooltip.Root>
												<Tooltip.Trigger><InfoIcon class="h-5 w-5" /></Tooltip.Trigger>
												<Tooltip.Content side="right" class="tooltip-content">
													<p>
														The values represent local effects near
														{solutions[selectedSolutions[0]].name == null
															? 'Solution ' + (selectedSolutions[0] + 1)
															: solutions[selectedSolutions[0]].name}. They indicate how much each
														objective function is expected to change if the selected objective
														function is improved by one unit.
													</p>
												</Tooltip.Content>
											</Tooltip.Root>
										</div>
										<ExpBarchart
											data={Object.entries(
												formatTradeofftoDict(tradeoffs, selectedObjectiveIndex) ?? {}
											).map(([objName, value]) => ({
												name: objectiveNames[objName] || objName,
												value: Number(value),
												direction: 'min'
											}))}
											options={{ showLabels: true, orientation: 'horizontal' }}
											onSelect={handleObjectiveClick}
										/>
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
