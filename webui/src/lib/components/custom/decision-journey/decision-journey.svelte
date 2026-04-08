<script lang="ts">
	import type { ENautilusSessionTreeResponse, ENautilusSimulateResponse, ProblemInfo, SolverResults } from '$lib/gen/models';
	import { extractPathToLeaf, computeJourneyData, buildNormalizationMaps, computeSimulatedJourneySteps, type JourneyStep, type WhatIfSimulation } from './journey-utils';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors';
	import { formatNumber } from '$lib/helpers';
	import { simulateMethodEnautilusSimulatePost } from '$lib/gen/endpoints/DESDEOFastAPI';
	import ObjectiveEvolutionChart from './objective-evolution-chart.svelte';
	import PreferenceProfileChart from './preference-profile-chart.svelte';
	import TradeoffSummary from './tradeoff-summary.svelte';
	import StepParallelAxes from './step-parallel-axes.svelte';

	interface Props {
		sessionTree: ENautilusSessionTreeResponse;
		leafNodeId: number;
		problem: ProblemInfo;
		/** Projected final solution values (from representative solutions).
		 *  Overrides the last step's raw values so the chart matches the final view. */
		finalSolutionPoint?: Record<string, number> | null;
		/** Called when the user wants to adopt the what-if simulation's final solution. */
		onAdoptSolution?: (solution: SolverResults) => void;
	}

	let { sessionTree, leafNodeId, problem, finalSolutionPoint = null, onAdoptSolution }: Props = $props();

	let tooltipEl = $state<HTMLDivElement>();
	let selectedStep = $state<JourneyStep | null>(null);
	let whatIfSimulation = $state<WhatIfSimulation | null>(null);
	let whatIfLoading = $state(false);
	let whatIfSectionEl = $state<HTMLDivElement>();

	let journeyData = $derived.by(() => {
		try {
			const path = extractPathToLeaf(sessionTree, leafNodeId);
			return computeJourneyData(path, sessionTree.decision_events, problem, finalSolutionPoint);
		} catch (err) {
			console.error("[DecisionJourney] Error computing journey data:", err);
			return {
				steps: [],
				objectiveKeys: [],
				objectiveLabels: [],
				objectiveMaximize: [],
				preferenceProfile: [],
				pairwiseTradeoffs: [],
			};
		}
	});

	function handleStepClick(step: JourneyStep) {
		selectedStep = step;
		whatIfSimulation = null;
	}

	async function handleWhatIf(objectiveSymbol: string, deprioritize = false) {
		if (!selectedStep || selectedStep.nodeId < 0) return;

		whatIfLoading = true;
		try {
			const result = await simulateMethodEnautilusSimulatePost({
				state_id: selectedStep.nodeId,
				preferred_objective: objectiveSymbol,
				deprioritize,
			});
			if (result.status !== 200) {
				console.error('[DecisionJourney] Simulation failed:', result.status);
				whatIfLoading = false;
				return;
			}
			const response: ENautilusSimulateResponse = result.data;

			// Build normalization maps
			const path = extractPathToLeaf(sessionTree, leafNodeId);
			const rootPoint = path.length > 0 ? (path[0].selected_point as Record<string, number> | null) : null;
			const { idealMap, nadirMap } = buildNormalizationMaps(problem, rootPoint);

			// Convert simulation steps to JourneyStep[]
			const simSteps = computeSimulatedJourneySteps(
				response.steps,
				journeyData.objectiveKeys,
				idealMap,
				nadirMap,
			);

			// Find branch step index
			const branchIdx = journeyData.steps.findIndex((s) => s.nodeId === selectedStep!.nodeId);

			// Extract final solution values, handling both scalar and array forms
			const rawObjectives = response.final_solution.optimal_objectives ?? {};
			const finalSolution: Record<string, number> = {};
			for (const [k, v] of Object.entries(rawObjectives)) {
				finalSolution[k] = Array.isArray(v) ? v[0] : (v as number);
			}

			whatIfSimulation = {
				branchStepIdx: branchIdx >= 0 ? branchIdx : 0,
				preferredObjective: response.preferred_objective,
				deprioritize,
				steps: simSteps,
				finalSolution,
				fullSolverResults: response.final_solution,
			};

			// Scroll the what-if section into view after render
			requestAnimationFrame(() => {
				whatIfSectionEl?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
			});
		} catch (err) {
			console.error('[DecisionJourney] What-if simulation failed:', err);
		}
		whatIfLoading = false;
	}

	function fmtPct(val: number): string {
		const sign = val > 0 ? '+' : '';
		return `${sign}${formatNumber(val, 1)}%`;
	}
</script>

<div class="absolute inset-0 flex gap-4 overflow-hidden p-4">
	<!-- LEFT: Journey overview (chart + preference profile + tradeoffs) -->
	<div class="flex min-w-0 flex-1 flex-col overflow-hidden">
		<h2 class="mb-2 shrink-0 text-lg font-semibold text-gray-800">Decision Journey</h2>

		{#if journeyData.steps.length < 2}
			<div class="flex flex-1 items-center justify-center text-sm text-gray-500">
				Not enough iterations to show a decision journey.
			</div>
		{:else}
			<div class="flex min-h-0 flex-1 gap-4">
				<!-- Evolution chart -->
				<div class="min-w-0 flex-[3] flex flex-col">
					<h3 class="mb-1 shrink-0 text-xs font-medium text-gray-500">Objective evolution</h3>
					<div class="min-h-0 flex-1">
						<ObjectiveEvolutionChart
							steps={journeyData.steps}
							objectiveKeys={journeyData.objectiveKeys}
							objectiveLabels={journeyData.objectiveLabels}
							objectiveMaximize={journeyData.objectiveMaximize}
							bind:tooltipEl={tooltipEl}
							onStepClick={handleStepClick}
							{whatIfSimulation}
							selectedIteration={selectedStep?.iteration ?? null}
						/>
					</div>
				</div>

				<!-- Preference profile + tradeoff summary -->
				<div class="flex min-w-[180px] flex-1 flex-col overflow-auto">
					<h3 class="mb-1 shrink-0 text-xs font-medium text-gray-500">Preference profile</h3>
					<div class="shrink-0">
						<PreferenceProfileChart profile={journeyData.preferenceProfile} />
					</div>

					{#if journeyData.pairwiseTradeoffs.length > 0}
						<h3 class="mb-1 mt-3 shrink-0 text-xs font-medium text-gray-500">Average tradeoffs</h3>
						<div class="shrink-0">
							<TradeoffSummary tradeoffs={journeyData.pairwiseTradeoffs} />
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>

	<!-- RIGHT: Iteration detail panel (shown when a step is clicked) -->
	{#if selectedStep && selectedStep.alternativeDeltas && selectedStep.alternativeDeltas.length > 0}
		<div class="flex w-1/3 shrink-0 flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
			<div class="flex items-center justify-between border-b border-gray-100 px-4 py-3">
				<h3 class="text-sm font-semibold text-gray-800">
					Iteration {selectedStep.iteration}
				</h3>
				<button
					class="text-lg leading-none text-gray-400 hover:text-gray-700"
					onclick={() => { selectedStep = null; whatIfSimulation = null; }}
				>&times;</button>
			</div>

			<div class="flex-1 overflow-auto px-4 py-3">
				<!-- Objective values -->
				<div class="mb-3 text-xs">
					{#each journeyData.objectiveKeys as oKey, j}
						{@const raw = selectedStep.rawValues[oKey]}
						{#if raw != null}
							<div class="flex items-center gap-1.5">
								<span
									class="inline-block h-2 w-2 shrink-0 rounded-full"
									style="background:{COLOR_PALETTE[j % COLOR_PALETTE.length]}"
								></span>
								<span class="text-gray-700">
									{journeyData.objectiveLabels[j] ?? oKey}
									({journeyData.objectiveMaximize[j] ? 'max' : 'min'}):
									<b>{formatNumber(raw, 4)}</b>
								</span>
							</div>
						{/if}
					{/each}
				</div>

				<!-- Prioritized / sacrificed -->
				{#if selectedStep.tradeoffs}
					{@const prioritized = selectedStep.tradeoffs
						.filter((t) => t.normalizedRank <= 0.25)
						.map((t) => journeyData.objectiveLabels[journeyData.objectiveKeys.indexOf(t.key)] ?? t.key)}
					{@const sacrificed = selectedStep.tradeoffs
						.filter((t) => t.normalizedRank >= 0.75)
						.map((t) => journeyData.objectiveLabels[journeyData.objectiveKeys.indexOf(t.key)] ?? t.key)}

					<div class="mb-3 flex flex-wrap gap-x-3 gap-y-1 text-xs">
						{#if prioritized.length > 0}
							<div><span class="font-semibold text-green-700">Prioritized:</span> {prioritized.join(', ')}</div>
						{/if}
						{#if sacrificed.length > 0}
							<div><span class="font-semibold text-red-700">Sacrificed:</span> {sacrificed.join(', ')}</div>
						{/if}
					</div>
				{/if}

				<!-- Parallel axes snapshot -->
				{#if selectedStep.intermediatePoints && selectedStep.chosenOptionIdx != null}
					<div class="mb-3 h-[220px] rounded border border-gray-100 bg-gray-50">
						<StepParallelAxes
							options={selectedStep.intermediatePoints}
							chosenIdx={selectedStep.chosenOptionIdx}
							objectiveKeys={journeyData.objectiveKeys}
							objectiveLabels={journeyData.objectiveLabels}
							objectiveMaximize={journeyData.objectiveMaximize}
						/>
					</div>
				{/if}

				<!-- Delta table -->
				<div class="overflow-x-auto">
					<table class="w-full text-xs">
						<thead>
							<tr class="border-b border-gray-200 text-left text-gray-500">
								<th class="pb-1 pr-2 font-medium">vs</th>
								{#each journeyData.objectiveKeys as oKey, j}
									<th class="pb-1 px-1.5 font-medium text-center">
										<div class="flex items-center justify-center gap-1">
											<span
												class="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
												style="background:{COLOR_PALETTE[j % COLOR_PALETTE.length]}"
											></span>
											{oKey}
										</div>
									</th>
								{/each}
							</tr>
						</thead>
						<tbody>
							{#each selectedStep.alternativeDeltas as alt}
								<tr class="border-b border-gray-100">
									<td class="py-1 pr-2 font-medium text-gray-600">Opt {alt.optionIdx + 1}</td>
									{#each journeyData.objectiveKeys as oKey, j}
										{@const pct = alt.pctDeltas[oKey]}
										{@const isGood = journeyData.objectiveMaximize[j] ? (pct ?? 0) > 0 : (pct ?? 0) < 0}
										{@const isBad = journeyData.objectiveMaximize[j] ? (pct ?? 0) < 0 : (pct ?? 0) > 0}
										<td class="py-1 px-1.5 text-center font-semibold"
											style="color: {isGood ? '#059669' : isBad ? '#dc2626' : '#666'}"
										>
											{pct != null ? fmtPct(pct) : '—'}
										</td>
									{/each}
								</tr>
							{/each}
						</tbody>
					</table>
				</div>

				<p class="mt-2 text-[10px] text-gray-400">
					% relative to ideal–nadir range. Green = better than alternative, red = worse.
				</p>

				<!-- What-if simulation section -->
				<div bind:this={whatIfSectionEl} class="mt-4 border-t border-gray-200 pt-3">
					<div class="mb-2 text-xs font-medium text-gray-500">What if you had always picked the best...</div>
					<div class="flex flex-wrap gap-1.5">
						{#each journeyData.objectiveKeys as oKey, j}
							{@const oLabel = journeyData.objectiveLabels[j] ?? oKey}
							{@const dir = journeyData.objectiveMaximize[j] ? '↑' : '↓'}
							{@const isActive = whatIfSimulation?.preferredObjective === oKey && !whatIfSimulation?.deprioritize}
							<button
								class="rounded border px-2 py-1 text-xs transition-colors {isActive ? 'border-blue-400 bg-blue-50 text-blue-700 font-semibold' : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:bg-gray-50'}"
								disabled={whatIfLoading}
								onclick={() => handleWhatIf(oKey)}
							>
								{oLabel} {dir}
							</button>
						{/each}
					</div>

					<div class="mt-2 mb-2 text-xs font-medium text-gray-500">...or always picked the worst?</div>
					<div class="flex flex-wrap gap-1.5">
						{#each journeyData.objectiveKeys as oKey, j}
							{@const oLabel = journeyData.objectiveLabels[j] ?? oKey}
							{@const dir = journeyData.objectiveMaximize[j] ? '↓' : '↑'}
							{@const isActive = whatIfSimulation?.preferredObjective === oKey && whatIfSimulation?.deprioritize}
							<button
								class="rounded border px-2 py-1 text-xs transition-colors {isActive ? 'border-red-400 bg-red-50 text-red-700 font-semibold' : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:bg-gray-50'}"
								disabled={whatIfLoading}
								onclick={() => handleWhatIf(oKey, true)}
							>
								{oLabel} {dir}
							</button>
						{/each}
					</div>

					{#if whatIfLoading}
						<div class="mt-2 text-xs text-gray-400 italic">Simulating...</div>
					{/if}

					{#if whatIfSimulation}
						<div class="mt-3">
							<div class="mb-1 text-xs font-medium text-gray-500">Actual vs What-if final</div>
							<table class="w-full text-xs">
								<thead>
									<tr class="border-b border-gray-200 text-left text-gray-500">
										<th class="pb-1 pr-2 font-medium">Objective</th>
										<th class="pb-1 px-1.5 font-medium text-center">Actual</th>
										<th class="pb-1 px-1.5 font-medium text-center">What-if</th>
										<th class="pb-1 px-1.5 font-medium text-center">Δ</th>
									</tr>
								</thead>
								<tbody>
									{#each journeyData.objectiveKeys as oKey, j}
										{@const actualRaw = journeyData.steps[journeyData.steps.length - 1]?.rawValues[oKey]}
										{@const whatIfRaw = whatIfSimulation.finalSolution[oKey]}
										{@const delta = actualRaw != null && whatIfRaw != null ? whatIfRaw - actualRaw : null}
										{@const isMax = journeyData.objectiveMaximize[j]}
										{@const isGood = delta != null && ((isMax && delta > 0) || (!isMax && delta < 0))}
										{@const isBad = delta != null && ((isMax && delta < 0) || (!isMax && delta > 0))}
										<tr class="border-b border-gray-100">
											<td class="py-1 pr-2 text-gray-600">
												<span class="inline-block h-1.5 w-1.5 rounded-full mr-1" style="background:{COLOR_PALETTE[j % COLOR_PALETTE.length]}"></span>
												{journeyData.objectiveLabels[j] ?? oKey}
											</td>
											<td class="py-1 px-1.5 text-center">{actualRaw != null ? formatNumber(actualRaw, 4) : '—'}</td>
											<td class="py-1 px-1.5 text-center">{whatIfRaw != null ? formatNumber(whatIfRaw, 4) : '—'}</td>
											<td class="py-1 px-1.5 text-center font-semibold" style="color: {isGood ? '#059669' : isBad ? '#dc2626' : '#666'}">
												{delta != null ? (delta > 0 ? '+' : '') + formatNumber(delta, 4) : '—'}
											</td>
										</tr>
									{/each}
								</tbody>
							</table>

							<div class="mt-2 flex gap-2">
							{#if onAdoptSolution}
								<button
									class="rounded border border-blue-300 bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100"
									onclick={() => onAdoptSolution?.(whatIfSimulation!.fullSolverResults)}
								>
									Use this solution
								</button>
							{/if}
							<button
								class="rounded border border-gray-200 px-2 py-1 text-xs text-gray-500 hover:bg-gray-50"
								onclick={() => (whatIfSimulation = null)}
							>
								Clear what-if
							</button>
						</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	{:else}
		<div class="flex w-1/3 shrink-0 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50 text-sm text-gray-400">
			Click a point on the chart to see iteration details.
		</div>
	{/if}

	<!-- Tooltip -->
	<div
		bind:this={tooltipEl}
		class="pointer-events-none absolute rounded border border-gray-200 bg-white px-3 py-2 text-xs shadow-lg"
		style="opacity: 0; transition: opacity 0.15s; z-index: 50; max-width: 320px;"
	></div>
</div>
