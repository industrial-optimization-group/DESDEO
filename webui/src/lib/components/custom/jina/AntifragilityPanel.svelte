<script lang="ts">
	/**
	 * The antifragility tab: pick a finished evaluation, give optional floors, analyse it relative
	 * to the setup's baseline leaf and chart the results. Shares the evaluations and the chosen
	 * one with the robustness tab. Scrolls vertically inside the tab.
	 */
	import * as Select from '$lib/components/ui/select/index.js';
	import { Label } from '$lib/components/ui/label';
	import type { JinaAntifragilityResponse, ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';
	import AnalysisPanel from './AnalysisPanel.svelte';
	import AntifragilityCharts from './AntifragilityCharts.svelte';
	import { evaluationLabel } from './labels';
	import type {
		AntifragilityInputs,
		AntifragilityResult,
		EvaluateState,
		SetupState
	} from './types';

	let {
		problem,
		setup,
		evaluations,
		selectedId = $bindable(null),
		evaluationId = $bindable(null),
		result = $bindable(null),
		inputs = $bindable({}),
		onAnalyse
	}: {
		problem: ProblemInfo;
		setup: SetupState;
		evaluations: EvaluateState[];
		selectedId?: number | null;
		evaluationId?: number | null;
		result?: AntifragilityResult | null;
		inputs?: Record<number, AntifragilityInputs>;
		onAnalyse: (
			evaluateStateId: number,
			request: {
				absolute_floors: Record<string, number> | null;
				loss_floors: Record<string, number> | null;
			}
		) => Promise<JinaAntifragilityResponse | null>;
	} = $props();

	let baselineLeaf = $derived(setup.result.baseline_leaf);
	let finished = $derived(evaluations.filter((e) => e.is_ready && !e.error));
	let evaluation = $derived(
		finished.find((e) => e.state_id === evaluationId) ?? finished.at(-1) ?? null
	);
	// Whether some design has an outcome in the baseline leaf, which the analysis needs.
	let hasBaseline = $derived(
		!!baselineLeaf &&
			Object.values(evaluation?.result.outcomes ?? {}).some(
				(leaves) => leaves[baselineLeaf]?.status
			)
	);

	function label(e: EvaluateState): string {
		return evaluationLabel(e.state_id, e.result.scenario_model_id, setup.result.scenario_model_id);
	}
</script>

<!-- The scroller is positioned out of flow, so the layout's auto-sized grid row cannot grow to the
     content's height, and it anchors the chart's absolutely positioned tooltip. -->
<div class="relative h-full min-h-0 min-w-0">
	<div class="@container absolute inset-0 space-y-4 overflow-y-auto p-3">
		{#if !baselineLeaf}
			<p class="text-sm text-gray-500">
				Antifragility compares each design with itself in a baseline scenario. Choose a baseline
				leaf in a new setup to use it.
			</p>
		{:else if !evaluation}
			<p class="text-sm text-gray-500">
				No finished evaluations. Evaluate designs in the Robustness tab first.
			</p>
		{:else}
			<section class="max-w-xl min-w-0 space-y-3 rounded border bg-white p-3">
				<h3 class="text-sm font-semibold">Analyse relative to {baselineLeaf}</h3>
				<div class="grid grid-cols-[minmax(0,1fr)] gap-1">
					<Label for="antifragility-evaluation">Evaluation</Label>
					<Select.Root
						type="single"
						bind:value={
							() => String(evaluation?.state_id ?? ''), (v: string) => (evaluationId = Number(v))
						}
					>
						<Select.Trigger id="antifragility-evaluation" class="w-full min-w-0">
							<span class="min-w-0 truncate">{label(evaluation)}</span>
						</Select.Trigger>
						<Select.Content>
							{#each [...finished].reverse() as e (e.state_id)}
								<Select.Item value={String(e.state_id)}>{label(e)}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				</div>
				{#if hasBaseline}
					<AnalysisPanel
						{problem}
						{evaluation}
						{baselineLeaf}
						{onAnalyse}
						bind:result
						bind:inputs
					/>
				{:else}
					<p class="text-sm text-gray-500">
						No design has an outcome in {baselineLeaf} in this evaluation.
					</p>
				{/if}
			</section>

			{#if result?.evaluateStateId === evaluation.state_id}
				<AntifragilityCharts {problem} {result} {baselineLeaf} bind:selectedId />
			{/if}
		{/if}
	</div>
</div>
