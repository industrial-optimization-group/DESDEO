<script lang="ts">
	/**
	 * Evaluates designs in the leaves of a scenario model of the problem: the setup's own model,
	 * or another one as a stress test. Every leaf is re-solved at the domain-criterion thresholds,
	 * one per objective of the model, so evaluating needs a threshold for each.
	 */
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button';
	import Checkbox from '$lib/components/ui/checkbox/checkbox.svelte';
	import { Label } from '$lib/components/ui/label';
	import type {
		JinaDesignInfo,
		JinaScenarioModelInfo,
		ProblemInfo
	} from '$lib/gen/endpoints/DESDEOFastAPI';
	import ObjectivePointInputs from './ObjectivePointInputs.svelte';
	import { finitePoint, midpointPrefill, type Range } from './reference-point';
	import { modelLabel } from './labels';

	let {
		problem,
		setupModelId,
		scenarioModels,
		designs,
		wishlist,
		objectiveRanges,
		modelId = $bindable(''),
		chosen = $bindable([]),
		thresholds = $bindable({}),
		onEvaluate
	}: {
		problem: ProblemInfo;
		setupModelId: number;
		scenarioModels: JinaScenarioModelInfo[];
		designs: JinaDesignInfo[];
		wishlist: number[];
		objectiveRanges: Record<string, Range>;
		modelId?: string;
		chosen?: number[];
		thresholds?: Record<string, number | null>;
		onEvaluate: (request: {
			scenario_model_id: number;
			design_ids: number[];
			thresholds: Record<string, number>;
		}) => void;
	} = $props();

	$effect(() => {
		if (!modelId) modelId = String(setupModelId);
	});
	// Prefills each objective of the chosen model once, with the midpoint of its range if known.
	$effect(() => {
		const missing = (model?.objectives ?? []).filter((obj) => !(obj in thresholds));
		if (missing.length === 0) return;
		thresholds = {
			...thresholds,
			...midpointPrefill(missing, objectiveRanges)
		};
	});
	$effect(() => {
		const known = new Set(designs.map((d) => d.id));
		const kept = chosen.filter((id) => known.has(id));
		if (kept.length !== chosen.length) chosen = kept;
	});

	let model = $derived(scenarioModels.find((m) => String(m.id) === modelId));
	let used = $derived(finitePoint(thresholds, model?.objectives ?? []));
	let complete = $derived(!!model && Object.keys(used).length === model.objectives.length);

	function label(m: JinaScenarioModelInfo, full = false): string {
		return m.id === setupModelId ? `${modelLabel(m, full)} (setup)` : modelLabel(m, full);
	}

	function run() {
		if (!model || !complete) return;
		onEvaluate({ scenario_model_id: model.id, design_ids: chosen, thresholds: used });
	}
</script>

<div class="min-w-0 space-y-3">
	<div class="grid grid-cols-[minmax(0,1fr)] gap-1">
		<Label for="stress-model">Scenario model</Label>
		<Select.Root type="single" bind:value={modelId}>
			<Select.Trigger id="stress-model" class="w-full min-w-0">
				<span class="min-w-0 truncate" title={model ? label(model, true) : ''}>
					{model ? label(model) : 'Select a scenario model'}
				</span>
			</Select.Trigger>
			<Select.Content>
				{#each scenarioModels as m (m.id)}
					<Select.Item value={String(m.id)} title={label(m, true)}>
						<span class="truncate">{label(m)}</span>
					</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
	</div>

	<div class="grid grid-cols-[minmax(0,1fr)] gap-1">
		<div class="flex items-center justify-between">
			<span class="text-sm font-medium">Designs</span>
			<span class="flex gap-1">
				<Button
					variant="ghost"
					size="sm"
					class="h-6 px-2 text-xs"
					onclick={() => (chosen = [...wishlist])}>Wishlist</Button
				>
				<Button
					variant="ghost"
					size="sm"
					class="h-6 px-2 text-xs"
					onclick={() => (chosen = designs.map((d) => d.id))}>All</Button
				>
			</span>
		</div>
		<div class="flex max-h-28 flex-wrap gap-x-3 gap-y-1 overflow-y-auto">
			{#each designs as design (design.id)}
				<div class="flex items-center gap-1">
					<Checkbox
						id="stress-design-{design.id}"
						checked={chosen.includes(design.id)}
						onCheckedChange={(checked) =>
							(chosen = checked ? [...chosen, design.id] : chosen.filter((id) => id !== design.id))}
					/>
					<label for="stress-design-{design.id}" class="text-sm">#{design.id}</label>
				</div>
			{/each}
		</div>
	</div>

	<div class="grid grid-cols-[minmax(0,1fr)] gap-1">
		<span class="text-sm font-medium">Thresholds</span>
		<p class="text-xs text-gray-500">
			Every scenario is re-solved at these with the design variables fixed, and the scenarios
			meeting each are counted.
		</p>
		<ObjectivePointInputs
			{problem}
			objectives={model?.objectives ?? []}
			idPrefix="threshold"
			bind:values={thresholds}
		/>
		{#if model && !complete}
			<p class="text-xs text-red-700">Give a threshold for every objective.</p>
		{/if}
	</div>

	<Button size="sm" disabled={!complete || chosen.length === 0} onclick={run}>Evaluate</Button>
</div>
