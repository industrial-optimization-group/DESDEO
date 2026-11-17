<script lang="ts">
	/**
	 * Inputs of the antifragility analysis of an evaluation over the objectives in its outcomes:
	 * optional absolute and loss floors of the Taleb classes. Empty entries are left out of the
	 * request; the result is put in `result`. The entries are kept per evaluation in `inputs`.
	 */
	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import type { JinaAntifragilityResponse, ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';
	import ObjectivePointInputs from './ObjectivePointInputs.svelte';
	import { finitePoint } from './reference-point';
	import { evaluatedObjectives } from './robustness-charts';
	import type { AntifragilityInputs, AntifragilityResult, EvaluateState } from './types';

	let {
		problem,
		evaluation,
		baselineLeaf,
		onAnalyse,
		result = $bindable(null),
		inputs = $bindable({})
	}: {
		problem: ProblemInfo;
		evaluation: EvaluateState;
		baselineLeaf: string;
		onAnalyse: (
			evaluateStateId: number,
			request: {
				absolute_floors: Record<string, number> | null;
				loss_floors: Record<string, number> | null;
			}
		) => Promise<JinaAntifragilityResponse | null>;
		result?: AntifragilityResult | null;
		inputs?: Record<number, AntifragilityInputs>;
	} = $props();

	let analysing = $state(false);
	let saved = $derived(inputs[evaluation.state_id]);
	let objectives = $derived(evaluatedObjectives(evaluation.result.outcomes));

	$effect(() => {
		if (!inputs[evaluation.state_id]) {
			inputs[evaluation.state_id] = { absoluteFloors: {}, lossFloors: {} };
		}
	});

	function floors(values: Record<string, number | null>): Record<string, number> | null {
		const point = finitePoint(values, objectives);
		return Object.keys(point).length > 0 ? point : null;
	}

	async function run() {
		if (!saved) return;
		analysing = true;
		const analysis = await onAnalyse(evaluation.state_id, {
			absolute_floors: floors(saved.absoluteFloors),
			loss_floors: floors(saved.lossFloors)
		});
		analysing = false;
		if (analysis) result = { evaluateStateId: evaluation.state_id, analysis, objectives };
	}
</script>

{#if saved}
	<div class="min-w-0 space-y-3">
		<div class="grid gap-1">
			<Label>Absolute floors (optional)</Label>
			<p class="text-xs text-gray-500">
				Worst acceptable outcome; a design beyond it in any scenario is fragile. Leave empty for
				none.
			</p>
			<ObjectivePointInputs
				{problem}
				{objectives}
				idPrefix="absolute-floor"
				bind:values={saved.absoluteFloors}
			/>
		</div>
		<div class="grid gap-1">
			<Label>Loss floors (optional)</Label>
			<p class="text-xs text-gray-500">
				Largest acceptable loss relative to {baselineLeaf}, in the objective's units; a design
				losing more in any scenario is fragile. Leave empty for none.
			</p>
			<ObjectivePointInputs
				{problem}
				{objectives}
				idPrefix="loss-floor"
				bind:values={saved.lossFloors}
			/>
		</div>

		<Button size="sm" disabled={analysing} onclick={run}
			>Analyse evaluation {evaluation.state_id}</Button
		>
	</div>
{/if}
