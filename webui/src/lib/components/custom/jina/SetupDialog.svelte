<script lang="ts">
	/**
	 * Dialog that starts a JINA setup: scenario model, design variables, aggregation measure and
	 * optional baseline leaf. Once `/setup` accepts the request it closes and passes the new setup
	 * state to `onStarted`; a rejected request shows its error in the dialog.
	 */
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button';
	import Checkbox from '$lib/components/ui/checkbox/checkbox.svelte';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import type {
		JinaScenarioModelInfo,
		JinaSetupRequest,
		JinaStateResponse,
		JinaSetupRequestMeasure
	} from '$lib/gen/endpoints/DESDEOFastAPI';
	import { MEASURE_LABELS, modelLabel } from './labels';

	let {
		open = $bindable(false),
		problemId,
		scenarioModels,
		onStart,
		onStarted
	}: {
		open?: boolean;
		problemId: number;
		scenarioModels: JinaScenarioModelInfo[];
		onStart: (
			request: JinaSetupRequest
		) => Promise<{ data: JinaStateResponse | null; error: string | null }>;
		onStarted: (state: JinaStateResponse) => void;
	} = $props();

	const MEASURES = Object.keys(MEASURE_LABELS) as JinaSetupRequestMeasure[];
	const NO_BASELINE = '';

	let modelId = $state('');
	let designVariables = $state<string[]>([]);
	let measure = $state<JinaSetupRequestMeasure>('worst_case');
	let cvarAlpha = $state(0.9);
	let baselineLeaf = $state(NO_BASELINE);

	let error = $state<string | null>(null);
	let starting = $state(false);

	let model = $derived(scenarioModels.find((m) => String(m.id) === modelId));

	$effect(() => {
		if (!modelId && scenarioModels.length > 0) selectModel(String(scenarioModels[0].id));
	});

	function selectModel(id: string) {
		modelId = id;
		const selected = scenarioModels.find((m) => String(m.id) === id);
		designVariables = [...(selected?.default_design_variables ?? [])];
		if (selected && !selected.leaves.includes(baselineLeaf)) baselineLeaf = NO_BASELINE;
	}

	function toggleVariable(symbol: string, checked: boolean) {
		designVariables = checked
			? (model?.root_variables ?? []).filter((s) => s === symbol || designVariables.includes(s))
			: designVariables.filter((s) => s !== symbol);
	}

	async function run() {
		if (!model) return;
		starting = true;
		const { data, error: message } = await onStart({
			problem_id: problemId,
			scenario_model_id: model.id,
			design_variables: designVariables,
			measure,
			cvar_alpha: cvarAlpha,
			baseline_leaf: baselineLeaf || null
		});
		starting = false;
		error = message;
		if (data) {
			open = false;
			onStarted(data);
		}
	}

	let canRun = $derived(
		!!model &&
			designVariables.length > 0 &&
			(measure !== 'cvar' || (cvarAlpha > 0 && cvarAlpha < 1))
	);
</script>

<Dialog.Root bind:open>
	<Dialog.Portal>
		<Dialog.Overlay />
		<Dialog.Content class="max-w-lg">
			<Dialog.Header>
				<Dialog.Title>Set up JINA</Dialog.Title>
				<Dialog.Description>
					Choose the scenario model, the variables that form a design and how the scenarios are
					aggregated.
				</Dialog.Description>
			</Dialog.Header>

			<div class="min-w-0 space-y-4 py-2">
				<div class="grid grid-cols-[minmax(0,1fr)] gap-1">
					<Label for="jina-model">Scenario model</Label>
					<Select.Root type="single" value={modelId} onValueChange={selectModel}>
						<Select.Trigger
							id="jina-model"
							class="w-full min-w-0"
							title={model ? modelLabel(model, true) : ''}
						>
							<span class="min-w-0 truncate">
								{model ? modelLabel(model) : 'Select a scenario model'}
							</span>
						</Select.Trigger>
						<Select.Content>
							{#each scenarioModels as m (m.id)}
								<Select.Item value={String(m.id)} title={modelLabel(m, true)}>
									<span class="truncate">{modelLabel(m)}</span>
								</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				</div>

				{#if model}
					<fieldset class="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-1">
						<legend class="mb-1 text-sm font-medium">Design variables</legend>
						{#if model.root_variables.length === 0}
							<p class="text-sm text-red-700">
								This scenario model has no variables shared by all scenarios.
							</p>
						{/if}
						<div class="flex max-h-40 flex-wrap gap-x-4 gap-y-2 overflow-y-auto">
							{#each model.root_variables as symbol (symbol)}
								<div class="flex items-center gap-2">
									<Checkbox
										id="jina-var-{symbol}"
										checked={designVariables.includes(symbol)}
										onCheckedChange={(checked) => toggleVariable(symbol, !!checked)}
									/>
									<label for="jina-var-{symbol}" class="cursor-pointer text-sm">{symbol}</label>
								</div>
							{/each}
						</div>
					</fieldset>

					<div class="grid grid-cols-2 gap-3">
						<div class="grid grid-cols-[minmax(0,1fr)] gap-1">
							<Label for="jina-measure">Aggregation measure</Label>
							<Select.Root
								type="single"
								value={measure}
								onValueChange={(v) => (measure = v as JinaSetupRequestMeasure)}
							>
								<Select.Trigger id="jina-measure" class="w-full min-w-0">
									{MEASURE_LABELS[measure]}
								</Select.Trigger>
								<Select.Content>
									{#each MEASURES as m (m)}
										<Select.Item value={m}>{MEASURE_LABELS[m]}</Select.Item>
									{/each}
								</Select.Content>
							</Select.Root>
						</div>
						{#if measure === 'cvar'}
							<div class="grid grid-cols-[minmax(0,1fr)] gap-1">
								<Label for="jina-alpha">CVaR confidence level α</Label>
								<Input
									id="jina-alpha"
									type="number"
									min="0"
									max="1"
									step="0.01"
									bind:value={cvarAlpha}
								/>
							</div>
						{/if}
					</div>

					<div class="grid grid-cols-[minmax(0,1fr)] gap-1">
						<Label for="jina-baseline">Baseline leaf for antifragility analysis</Label>
						<Select.Root type="single" bind:value={baselineLeaf}>
							<Select.Trigger id="jina-baseline" class="w-full min-w-0">
								{baselineLeaf || 'None'}
							</Select.Trigger>
							<Select.Content>
								<Select.Item value={NO_BASELINE}>None</Select.Item>
								{#each model.leaves as leaf (leaf)}
									<Select.Item value={leaf}>{leaf}</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
					</div>
				{/if}

				{#if error}
					<p class="rounded border border-red-300 bg-red-50 p-2 text-sm text-red-800" role="alert">
						{error}
					</p>
				{/if}
			</div>

			<Dialog.Footer>
				<Button variant="default" disabled={!canRun || starting} onclick={run}>Start</Button>
			</Dialog.Footer>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>
