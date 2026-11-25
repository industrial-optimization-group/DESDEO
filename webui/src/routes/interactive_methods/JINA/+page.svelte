<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import { methodSelection } from '../../../stores/methodSelection';
	import { errorMessage, isLoading } from '../../../stores/uiState';
	import LoadingSpinner from '$lib/components/custom/notifications/loading-spinner.svelte';
	import Alert from '$lib/components/custom/notifications/alert.svelte';
	import { SegmentedControl } from '$lib/components/custom/segmented-control';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import ResizableHandle from '$lib/components/ui/resizable/resizable-handle.svelte';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';
	import { PREFERENCE_TYPES } from '$lib/constants';

	import SetupDialog from '$lib/components/custom/jina/SetupDialog.svelte';
	import ReferencePointEditor from '$lib/components/custom/jina/ReferencePointEditor.svelte';
	import DesignTable from '$lib/components/custom/jina/DesignTable.svelte';
	import ScenarioBreakdown from '$lib/components/custom/jina/ScenarioBreakdown.svelte';
	import WishlistPanel from '$lib/components/custom/jina/WishlistPanel.svelte';
	import RobustnessPanel from '$lib/components/custom/jina/RobustnessPanel.svelte';
	import AntifragilityPanel from '$lib/components/custom/jina/AntifragilityPanel.svelte';
	import type { AntifragilityInputs, AntifragilityResult } from '$lib/components/custom/jina/types';
	import JobStatus from '$lib/components/custom/jina/JobStatus.svelte';
	import {
		midpoint,
		objectiveRanges,
		type Range
	} from '$lib/components/custom/jina/reference-point';
	import {
		MEASURE_LABELS,
		baselineFirst,
		modelLabel,
		plural
	} from '$lib/components/custom/jina/labels';
	import { orderTargets } from '$lib/components/custom/jina/fill';
	import { pointArray, viewProblem, viewRows } from '$lib/components/custom/jina/view-problem';
	import {
		aggregateAvailable,
		aggregateLines,
		concatLines,
		defaultChartSelection,
		hideLines,
		scenarioColor,
		scenarioLines,
		scenarioProblem,
		scenarioReferencePoint
	} from '$lib/components/custom/jina/scenario-chart';
	import {
		extendToValues,
		outcomeLines,
		outcomeRows,
		rowKey,
		solvedOutcomes,
		targetLines
	} from '$lib/components/custom/jina/scenario-optimal';
	import ScenarioPicker from '$lib/components/custom/jina/ScenarioPicker.svelte';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';

	import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';
	import type {
		EvaluateState,
		IterateState,
		JinaDesignInfo,
		JinaScenarioModelInfo,
		JinaStateResponse,
		SelectState,
		SetupState,
		SolveView,
		Target
	} from './types';
	import {
		analyseAntifragility,
		evaluate,
		fetchDesigns,
		loadSession,
		importDesigns,
		iterate,
		select,
		startSetup
	} from './handlers';

	const { data } = $props<{ data: { problems: ProblemInfo[] } }>();
	let problemList = $derived(data.problems ?? []);

	type Tab = SolveView | 'robustness' | 'antifragility';
	const TABS: { value: Tab; label: string }[] = [
		{ value: 'aggregated', label: 'Aggregated' },
		{ value: 'per_scenario', label: 'Per-scenario' },
		{ value: 'scenario_optimal', label: 'Scenario-optimal' },
		{ value: 'robustness', label: 'Robustness' },
		{ value: 'antifragility', label: 'Antifragility' }
	];

	let problem = $state<ProblemInfo | null>(null);
	let scenarioModels = $state<JinaScenarioModelInfo[]>([]);
	let setup = $state<SetupState | null>(null);
	let states = $state<JinaStateResponse[]>([]);
	let designs = $state<JinaDesignInfo[]>([]);
	let pending = $state<{ id: number; label: string }[]>([]);

	let showSetup = $state(false);
	let setupJobId = $state<number | null>(null);
	let designsRequest = 0;
	let tab = $state<Tab>('aggregated');
	// The scenario chosen in the Scenario-optimal tab (null: the first in leaf order).
	let chosenLeaf = $state<string | null>(null);
	let selectedDesignId = $state<number | null>(null);
	// The key of the scenario-optimal row clicked last.
	let clickedRowKey = $state<string | null>(null);
	let shownIteration = $state<Record<Tab, string>>({
		aggregated: '',
		per_scenario: '',
		scenario_optimal: '',
		robustness: '',
		antifragility: ''
	});
	// The reference point being edited by point key.
	let referencePoints = $state<Record<string, Record<string, number>>>({});

	let ready = $derived(!!setup && setup.is_ready && !setup.error && !!setup.result.ranges);
	// The Robustness and Antifragility tabs edit no reference point; their view is only a placeholder.
	let analysisTab = $derived(tab === 'robustness' || tab === 'antifragility');
	// Antifragility needs a baseline leaf, so its tab is shown only for setups with one.
	let tabs = $derived(
		setup?.result.baseline_leaf ? TABS : TABS.filter((t) => t.value !== 'antifragility')
	);
	let view = $derived<SolveView>(analysisTab ? 'aggregated' : (tab as SolveView));
	let setupModel = $derived(scenarioModels.find((m) => m.id === setup?.result.scenario_model_id));
	let leafOrder = $derived(
		baselineFirst(setupModel?.leaves ?? [], setup?.result.baseline_leaf ?? null)
	);
	// The scenario the Scenario-optimal tab optimises for; null in the other tabs.
	let leaf = $derived(view === 'scenario_optimal' ? (chosenLeaf ?? leafOrder[0] ?? null) : null);
	let targets = $derived(viewTargets(view, leaf));
	let ranges = $derived(viewRanges(view, leaf));

	// The targets and ranges of a view, in the scenario-optimal view those of the scenario `leaf`.
	function viewTargets(view: SolveView, leaf: string | null): Target[] {
		if (view !== 'scenario_optimal') return setup?.result.targets?.[view] ?? [];
		return setup?.result.scenario_targets?.[leaf ?? ''] ?? [];
	}

	function viewRanges(view: SolveView, leaf: string | null): Record<string, Range> {
		if (view !== 'scenario_optimal') return setup?.result.ranges?.[view] ?? {};
		return setup?.result.scenario_ranges?.[leaf ?? ''] ?? {};
	}

	// The key of a view's reference point; the scenario-optimal view has one per scenario.
	function pointKey(view: SolveView, leaf: string | null): string {
		return leaf === null ? view : `${view}:${leaf}`;
	}

	let referencePoint = $derived(referencePoints[pointKey(view, leaf)] ?? {});

	let iterations = $derived(
		states.filter((s): s is IterateState => s.result.kind === 'jina.iterate')
	);
	let evaluations = $derived(
		states.filter((s): s is EvaluateState => s.result.kind === 'jina.evaluate')
	);
	let lastSelect = $derived(
		states.filter((s): s is SelectState => s.result.kind === 'jina.select').at(-1)
	);
	let wishlist = $derived(lastSelect?.result.wishlist ?? []);
	let finalId = $derived(lastSelect?.result.final_design_id ?? null);

	let tabIterations = $derived(
		iterations.filter((s) => s.result.mode === 'solve' && s.result.view === tab)
	);
	let iteration = $derived(
		tabIterations.find((s) => String(s.state_id) === shownIteration[tab]) ?? tabIterations.at(-1)
	);
	let iterationTargets = $derived<Target[]>(
		iteration?.result.view ? viewTargets(iteration.result.view, iteration.result.leaf) : []
	);

	// The latest reference point iterated with by point key.
	let previousPoints = $derived.by(() => {
		const result: Record<string, Record<string, number>> = {};
		for (const { result: r } of iterations) {
			if (r.view) result[pointKey(r.view, r.leaf)] = r.reference_point;
		}
		return result;
	});

	let objRanges = $derived.by(() => {
		const result: Record<string, Range> = {};
		for (const objective of problem?.objectives ?? []) {
			if (objective.ideal != null && objective.nadir != null) {
				result[objective.symbol] = [objective.ideal, objective.nadir];
			}
		}
		const perScenario = setup?.result.targets?.per_scenario ?? [];
		const perScenarioRanges = (setup?.result.ranges?.per_scenario ?? {}) as Record<string, Range>;
		return { ...result, ...objectiveRanges(perScenario, perScenarioRanges) };
	});

	let selectedDesign = $derived(designs.find((d) => d.id === selectedDesignId) ?? null);
	let representativeSets = $derived(
		(problem?.problem_metadata?.representative_nd_metadata ?? []).flatMap((s) =>
			s.id == null ? [] : [{ id: s.id, name: s.name }]
		)
	);

	// Starts each reference point at its previous one, or at the middle of each range.
	$effect(() => {
		if (!ready || !setup) return;
		const points: [SolveView, string | null][] = [
			['aggregated', null],
			['per_scenario', null],
			...leafOrder.map((l): [SolveView, string] => ['scenario_optimal', l])
		];
		for (const [v, l] of points) {
			const key = pointKey(v, l);
			const pointTargets = viewTargets(v, l);
			if (referencePoints[key] || pointTargets.length === 0) continue;
			const pointRanges = viewRanges(v, l);
			const start =
				previousPoints[key] ??
				Object.fromEntries(pointTargets.map((t) => [t.symbol, midpoint(pointRanges[t.symbol])]));
			referencePoints[key] = { ...start };
		}
	});

	onMount(async () => {
		const id = $methodSelection.selectedProblemId;
		if (!id) return;
		problem = problemList.find((p: ProblemInfo) => String(p.id) === String(id)) ?? null;
		if (!problem) return;

		const { models, restored } = await loadSession(problem.id);
		scenarioModels = models ?? [];
		if (!restored) return;
		if (!restored.setup) {
			showSetup = true;
			return;
		}
		applySetup(restored.setup as SetupState, restored.states);
		if (!ready) setupJobId = restored.setup.state_id;
	});

	function applySetup(state: SetupState, children: JinaStateResponse[] = []) {
		setup = state;
		states = children;
		if (tab === 'antifragility' && !state.result.baseline_leaf) tab = 'robustness';
		designs = [];
		selectedDesignId = null;
		clickedRowKey = null;
		// The latest iteration is shown, so its scenario is chosen.
		chosenLeaf = iterations.findLast((s) => s.result.leaf !== null)?.result.leaf ?? null;
		referencePoints = {};
		shownIteration = {
			aggregated: '',
			per_scenario: '',
			scenario_optimal: '',
			robustness: '',
			antifragility: ''
		};
		chartSelections = { aggregated: null, per_scenario: null, scenario_optimal: null };
		hiddenDesigns = [];
		collapsedGroups = [];
		evaluationId = null;
		evaluateModelId = '';
		evaluateDesignIds = [];
		thresholds = {};
		antifragilityResult = null;
		antifragilityInputs = {};
		chartIterationIds = {
			aggregated: [],
			per_scenario: [],
			scenario_optimal: [],
			robustness: [],
			antifragility: []
		};
		pending = children
			.filter((s) => !s.is_ready)
			.map((s) => ({ id: s.state_id, label: jobLabel(s) }));
		if (ready) void refreshDesigns();
	}

	// Only the response to the latest request for the current setup is kept.
	async function refreshDesigns() {
		if (!problem || !setup) return;
		const request = ++designsRequest;
		const setupId = setup.state_id;
		const result = await fetchDesigns(problem.id, setupId);
		if (result && request === designsRequest && setup?.state_id === setupId) designs = result;
	}

	function jobLabel(state: JinaStateResponse): string {
		if (state.result.kind === 'jina.evaluate') return `Evaluation ${state.state_id}`;
		if (state.result.kind === 'jina.iterate' && state.result.mode === 'import') {
			return `Import ${state.state_id}`;
		}
		return `Iteration ${state.state_id}`;
	}

	function upsert(state: JinaStateResponse) {
		const index = states.findIndex((s) => s.state_id === state.state_id);
		states = index < 0 ? [...states, state] : states.with(index, state);
	}

	function track(state: JinaStateResponse) {
		upsert(state);
		if (!state.is_ready) pending = [...pending, { id: state.state_id, label: jobLabel(state) }];
		else afterIterate(state);
	}

	function jobDone(state: JinaStateResponse) {
		upsert(state);
		if (!state.error) {
			pending = pending.filter((p) => p.id !== state.state_id);
			afterIterate(state);
		}
	}

	function afterIterate(state: JinaStateResponse) {
		if (state.result.kind !== 'jina.iterate') return;
		void refreshDesigns();
		const first = state.result.results.find((r) => r.design_id != null)?.design_id;
		if (state.result.mode !== 'import' && first != null) selectedDesignId = first;
	}

	async function runIterate() {
		if (!problem || !setup) return;
		const point = Object.fromEntries(
			targets
				.filter((t) => referencePoint[t.symbol] !== undefined)
				.map((t) => [t.symbol, referencePoint[t.symbol]])
		);
		const state = await iterate({
			problem_id: problem.id,
			setup_state_id: setup.state_id,
			view,
			leaf,
			reference_point: point
		});
		if (state) {
			shownIteration[tab] = '';
			track(state);
		}
	}

	async function saveSelection(nextWishlist: number[], nextFinal: number | null) {
		if (!problem || !setup) return;
		const state = await select({
			problem_id: problem.id,
			setup_state_id: setup.state_id,
			wishlist: nextWishlist,
			final_design_id: nextFinal
		});
		if (state) upsert(state);
	}

	async function runImport(setId: number, referencePoint: Record<string, number>) {
		if (!problem || !setup) return;
		const state = await importDesigns({
			problem_id: problem.id,
			setup_state_id: setup.state_id,
			representative_set_id: setId,
			reference_point: referencePoint
		});
		if (state) track(state);
	}

	async function runEvaluate(request: {
		scenario_model_id: number;
		design_ids: number[];
		thresholds: Record<string, number>;
	}) {
		if (!problem || !setup) return;
		const state = await evaluate({
			problem_id: problem.id,
			setup_state_id: setup.state_id,
			...request
		});
		if (state) track(state);
	}

	function runAntifragility(
		evaluateStateId: number,
		request: {
			absolute_floors: Record<string, number> | null;
			loss_floors: Record<string, number> | null;
		}
	) {
		if (!problem || !setup) return Promise.resolve(null);
		return analyseAntifragility({
			problem_id: problem.id,
			setup_state_id: setup.state_id,
			evaluate_state_id: evaluateStateId,
			...request
		});
	}

	function setupDone(state: JinaStateResponse) {
		if (state.error) return;
		setupJobId = null;
		applySetup(state as SetupState);
	}

	function leafLabel(l: string): string {
		return l === setup?.result.baseline_leaf ? `★ ${l}` : l;
	}

	function iterationLabel(s: IterateState, index: number): string {
		return `Iteration ${index + 1}${s.result.leaf ? ` (${s.result.leaf})` : ''}`;
	}

	// Showing a scenario-optimal iteration also chooses its scenario.
	function showIteration(id: string) {
		shownIteration[tab] = id;
		chosenLeaf = iteration?.result.leaf ?? chosenLeaf;
	}

	const emptyMessage = 'No designs in this iteration.';

	// Chart state of the current setup: per view, the scenarios plotted and whether the aggregate
	// is (null: the default), the designs hidden from the chart and the iterations plotted in each
	// tab (none chosen: the shown iteration).
	let chartSelections = $state<Record<SolveView, { leaves: string[]; aggregate: boolean } | null>>({
		aggregated: null,
		per_scenario: null,
		scenario_optimal: null
	});
	let hiddenDesigns = $state<number[]>([]);
	// The evaluation chosen in the Robustness and Antifragility tabs (null: the latest).
	let evaluationId = $state<number | null>(null);
	// The Robustness tab's evaluate inputs: scenario model, designs and thresholds.
	let evaluateModelId = $state('');
	let evaluateDesignIds = $state<number[]>([]);
	let thresholds = $state<Record<string, number | null>>({});
	// The latest antifragility analysis, for the Antifragility tab's charts and table.
	let antifragilityResult = $state<AntifragilityResult | null>(null);
	// The floor entries of each evaluation, kept across tab switches.
	let antifragilityInputs = $state<Record<number, AntifragilityInputs>>({});
	// Objective groups collapsed in the reference-point editor.
	let collapsedGroups = $state<string[]>([]);
	let chartIterationIds = $state<Record<Tab, number[]>>({
		aggregated: [],
		per_scenario: [],
		scenario_optimal: [],
		robustness: [],
		antifragility: []
	});

	let leafColors = $derived(Object.fromEntries(leafOrder.map((l, i) => [l, scenarioColor(i)])));
	let chartSelection = $derived(chartSelections[view] ?? defaultChartSelection(view, leafOrder));
	let chartIterations = $derived.by(() => {
		const chosen = tabIterations.filter((s) => chartIterationIds[tab].includes(s.state_id));
		return chosen.length > 0 ? chosen : iteration ? [iteration] : [];
	});

	function selectChart(change: Partial<{ leaves: string[]; aggregate: boolean }>) {
		chartSelections[view] = { ...chartSelection, ...change };
	}

	// The aggregate entry of the aggregated view: its targets on the original objective axes.
	let perScenarioTargets = $derived(setup?.result.targets?.per_scenario ?? []);
	let aggregatedTargets = $derived(setup?.result.targets?.aggregated ?? []);
	let objectiveSymbols = $derived([...new Set(perScenarioTargets.map((t) => t.objective))]);
	let aggregateEntry = $derived(
		view === 'aggregated' && setup
			? {
					label: `Aggregate (${MEASURE_LABELS[setup.result.measure]}${
						setup.result.measure === 'cvar' ? `, α = ${setup.result.cvar_alpha}` : ''
					})`,
					available: aggregateAvailable(aggregatedTargets, objectiveSymbols),
					note: 'Some objectives exist only in some scenarios, so the aggregate has no value on every objective axis.'
				}
			: null
	);
	let showAggregate = $derived(
		!!aggregateEntry?.available && chartSelection.aggregate && perScenarioTargets.length > 0
	);
	let objectiveMode = $derived(
		showAggregate || (chartSelection.leaves.length > 0 && perScenarioTargets.length > 0)
	);

	// The target view's axes are the shown iteration's targets, so it plots only iterations for the
	// same scenario; the objective axes plot them all.
	let comparable = (s: IterateState) => objectiveMode || s.result.leaf === iteration?.result.leaf;
	let plottedIterations = $derived(chartIterations.filter(comparable));
	let plottedIds = $derived([
		...new Set(
			plottedIterations.flatMap((s) =>
				s.result.results.flatMap((r) => (r.success && r.design_id != null ? [r.design_id] : []))
			)
		)
	]);
	let allHidden = $derived(
		plottedIds.length > 0 && plottedIds.every((id) => hiddenDesigns.includes(id))
	);

	// The rows of the plotted scenario-optimal iterations whose designs are visible.
	let plottedRows = $derived(
		outcomeRows(plottedIterations).filter((r) => !hiddenDesigns.includes(r.result.design_id!))
	);

	// The selected scenario-optimal row: the one clicked last if it has the selected design, else a
	// row with that design, first from the shown iteration, then from the plotted ones.
	let selectedRow = $derived.by(() => {
		if (!iteration) return null;
		const rows = outcomeRows([iteration, ...plottedIterations, ...tabIterations]).filter(
			(r) => r.result.design_id === selectedDesignId
		);
		return rows.find((r) => rowKey(r.stateId, r.result.name) === clickedRowKey) ?? rows[0] ?? null;
	});
	let selectedRowKey = $derived(
		selectedRow && rowKey(selectedRow.stateId, selectedRow.result.name)
	);
	let selectedOutcomes = $derived(selectedRow && solvedOutcomes(selectedRow.result, leafOrder));

	// The selected solution's values of the edited targets.
	let solution = $derived.by(() => {
		if (view !== 'scenario_optimal') return selectedDesign?.target_values[view] ?? null;
		return (selectedOutcomes ?? selectedDesign?.leaf_objectives)?.[leaf ?? ''] ?? null;
	});

	// The edited reference point's targets are those of the shown iteration.
	let pointComparable = $derived(
		!!iteration?.result.view &&
			pointKey(iteration.result.view, iteration.result.leaf) === pointKey(view, leaf)
	);

	// Target view: the shown iteration's targets as axes, one line per visible design of the plotted
	// iterations, or per row in the scenario-optimal view. The reference point is the one being edited;
	// the previous one is the shown iteration's. In the scenario-optimal view, the axes cover all drawn
	// values.
	let targetChart = $derived.by(() => {
		if (!problem || !iteration) return null;
		const ranges = iteration.result.view
			? viewRanges(iteration.result.view, iteration.result.leaf)
			: {};
		const results = plottedIterations.flatMap((s) => s.result.results);
		const lines =
			view === 'scenario_optimal'
				? targetLines(plottedRows, iterationTargets)
				: {
						...hideLines(viewRows(results, iterationTargets), hiddenDesigns),
						rowKeys: null
					};
		const current = pointComparable ? pointArray(referencePoint, iterationTargets) : null;
		const previous = pointArray(iteration.result.reference_point, iterationTargets);
		const points = [current, previous].filter((p) => p !== null);
		const chartProblem = viewProblem(problem, iterationTargets, ranges);
		return {
			problem:
				view === 'scenario_optimal'
					? extendToValues(chartProblem, [...lines.values, ...points])
					: chartProblem,
			designIds: lines.designIds,
			labels: lines.labels,
			values: lines.values,
			rowKeys: lines.rowKeys,
			colors: undefined,
			reference: current,
			referenceLabel: 'Reference point',
			previous: previous ? [previous] : [],
			previousLabel: 'Previous reference point',
			note: null as string | null
		};
	});

	// Objective axes: the original objectives, one line per visible design and checked scenario with
	// its objective values there, coloured by scenario, and in the aggregated view one per design
	// with its aggregated target values. In the scenario-optimal view, one line per visible row and
	// checked scenario, and the reference points of the optimised scenario.
	let scenarioChart = $derived.by(() => {
		if (!problem || !iteration || !setup || !objectiveMode) return null;
		const leaves = chartSelection.leaves;
		const chartProblem = scenarioProblem(
			problem,
			perScenarioTargets,
			(setup.result.ranges?.per_scenario ?? {}) as Record<string, Range>,
			leaves,
			showAggregate
				? {
						targets: aggregatedTargets,
						ranges: (setup.result.ranges?.aggregated ?? {}) as Record<string, Range>
					}
				: null
		);
		const objectives = chartProblem.objectives.map((o) => o.symbol);
		if (view === 'scenario_optimal') {
			const lines = outcomeLines(plottedRows, leaves, leafOrder, objectives, selectedRowKey);
			const current = pointComparable ? pointArray(referencePoint, chartProblem.objectives) : null;
			const previous = pointArray(iteration.result.reference_point, chartProblem.objectives);
			const points = [current, previous].filter((p) => p !== null);
			return {
				problem: extendToValues(chartProblem, [...lines.values, ...points]),
				designIds: lines.designIds,
				labels: lines.labels,
				values: lines.values,
				rowKeys: lines.rowKeys,
				colors: lines.colors,
				reference: current,
				referenceLabel: `Reference point (for ${iteration.result.leaf})`,
				previous: previous ? [previous] : [],
				previousLabel: `Previous reference point (for ${iteration.result.leaf})`,
				note: "In other scenarios, each level is limited to the scenario's ideal–nadir range."
			};
		}
		const ids = plottedIds.filter((id) => !hiddenDesigns.includes(id));
		const leafObjectives = Object.fromEntries(designs.map((d) => [d.id, d.leaf_objectives]));
		const aggregatedValues = Object.fromEntries(
			designs.map((d) => [d.id, d.target_values.aggregated])
		);
		// Aggregate lines last so they are drawn on top of the scenario lines.
		const lines = concatLines(
			scenarioLines(ids, leafObjectives, leaves, leafOrder, objectives, selectedDesignId),
			...(showAggregate
				? [aggregateLines(ids, aggregatedValues, aggregatedTargets, objectives, selectedDesignId)]
				: [])
		);
		const current = scenarioReferencePoint(targets, referencePoint, objectives, leaves);
		const previous = scenarioReferencePoint(
			iterationTargets,
			iteration.result.reference_point,
			objectives,
			leaves
		);
		const suffix = (shared: boolean) => (shared ? '' : ` — ${leaves[0]}`);
		return {
			problem: chartProblem,
			designIds: lines.designIds,
			labels: lines.labels,
			values: lines.values,
			rowKeys: null,
			colors: lines.colors,
			reference: current.values,
			referenceLabel: `Reference point${suffix(current.shared)}`,
			previous: previous.values ? [previous.values] : [],
			previousLabel: `Previous reference point${suffix(previous.shared)}`,
			note: current.note ?? previous.note
		};
	});

	let chart = $derived(scenarioChart ?? targetChart);
	let chartSelected = $derived(
		chart
			? chart.designIds.flatMap((id, i) =>
					(chart.rowKeys ? chart.rowKeys[i] === selectedRowKey : id === selectedDesignId) ? [i] : []
				)
			: []
	);

	// Keeps the selection on a design of the shown iteration when another iteration is shown.
	$effect(() => {
		const ids = (iteration?.result.results ?? [])
			.map((r) => r.design_id)
			.filter((id): id is number => id != null);
		const current = untrack(() => selectedDesignId);
		if (current === null || !ids.includes(current)) selectedDesignId = ids[0] ?? null;
		clickedRowKey = null;
	});

	function toggleChartIteration(id: number, on: boolean) {
		const current =
			chartIterationIds[tab].length > 0
				? chartIterationIds[tab]
				: iteration
					? [iteration.state_id]
					: [];
		chartIterationIds[tab] = on ? [...current, id] : current.filter((c) => c !== id);
	}
</script>

<svelte:head>
	<title>JINA | DESDEO</title>
	<meta
		name="description"
		content="This page implements the JINA interactive method for scenario-based design in DESDEO"
	/>
</svelte:head>

{#if $isLoading}
	<LoadingSpinner />
{/if}

{#if $errorMessage}
	<Alert title="Error" message={$errorMessage} variant="destructive" />
{/if}

{#if problem}
	<SetupDialog
		bind:open={showSetup}
		problemId={problem.id}
		{scenarioModels}
		onStart={startSetup}
		onStarted={(state: JinaStateResponse) => (setupJobId = state.state_id)}
	/>
{/if}

<BaseLayout
	showLeftSidebar={ready && !analysisTab}
	showRightSidebar={!!problem}
	leftSidebarWidth="20rem"
	rightSidebarWidth="24rem"
	bottomPanelTitle="Iteration results"
	showNumericalValues={!analysisTab}
>
	{#snippet leftSidebar()}
		<!-- At most the viewport's height: the editor scrolls and the solve button stays visible. -->
		<div class="flex max-h-[calc(100vh-3rem)] flex-col gap-4 p-3">
			{#if ready && problem && !analysisTab}
				{#if view === 'scenario_optimal'}
					<div class="grid grid-cols-[minmax(0,1fr)] gap-1">
						<Label for="jina-leaf">Optimise for scenario</Label>
						<Select.Root
							type="single"
							bind:value={() => leaf ?? '', (l: string) => (chosenLeaf = l)}
						>
							<Select.Trigger id="jina-leaf" class="w-full min-w-0">
								<span class="min-w-0 truncate">{leafLabel(leaf ?? '')}</span>
							</Select.Trigger>
							<Select.Content>
								{#each leafOrder as l (l)}
									<Select.Item value={l}>{leafLabel(l)}</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
					</div>
				{/if}
				<h3 class="text-sm font-semibold">Reference point</h3>
				<div class="relative min-h-0 flex-1 overflow-y-auto pr-1">
					<ReferencePointEditor
						{problem}
						targets={orderTargets(targets, leafOrder)}
						{ranges}
						previous={previousPoints[pointKey(view, leaf)] ?? null}
						{solution}
						{leafColors}
						bind:value={
							() => referencePoint,
							(point: Record<string, number>) => (referencePoints[pointKey(view, leaf)] = point)
						}
						checkedLeaves={chartSelection.leaves}
						limit={view === 'scenario_optimal'}
						bind:collapsed={collapsedGroups}
					/>
				</div>
				<Button class="w-full shrink-0" onclick={runIterate}>Solve</Button>
			{/if}
		</div>
	{/snippet}

	{#snippet explorerTitle()}
		<span class="whitespace-nowrap">Solution Explorer</span>
	{/snippet}

	{#snippet explorerControls()}
		{#if ready}
			<!-- Wraps onto further lines rather than overflowing a narrow pane. -->
			<div class="flex min-w-0 flex-wrap items-center justify-end gap-2">
				<SegmentedControl bind:value={tab} options={tabs} />
				{#if tabIterations.length > 0 && iteration}
					<Select.Root type="single" bind:value={() => shownIteration[tab], showIteration}>
						<Select.Trigger class="w-56 max-w-full min-w-0">
							<span class="min-w-0 truncate">
								{iterationLabel(iteration, tabIterations.indexOf(iteration))}
							</span>
						</Select.Trigger>
						<Select.Content>
							{#each tabIterations as s, i (s.state_id)}
								<Select.Item value={String(s.state_id)}>{iterationLabel(s, i)}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				{/if}
				{#if tabIterations.length > 1 && iteration}
					<DropdownMenu.Root>
						<DropdownMenu.Trigger>
							{#snippet child({ props })}
								<Button {...props} variant="outline" size="sm" class="shrink-0">
									Chart: {chartIterationIds[tab].length > 0
										? plural(plottedIterations.length, 'iteration')
										: 'shown iteration'}
								</Button>
							{/snippet}
						</DropdownMenu.Trigger>
						<DropdownMenu.Content align="end">
							<DropdownMenu.Item onclick={() => (chartIterationIds[tab] = [])}>
								Shown iteration only
							</DropdownMenu.Item>
							<DropdownMenu.Separator />
							{#each tabIterations as s, i (s.state_id)}
								<DropdownMenu.CheckboxItem
									checked={chartIterations.includes(s) && comparable(s)}
									disabled={!comparable(s)}
									onCheckedChange={(on: boolean) => toggleChartIteration(s.state_id, on)}
									closeOnSelect={false}
								>
									{iterationLabel(s, i)}
									{#if !comparable(s)}
										<span class="text-xs text-gray-500">(other scenario)</span>
									{/if}
								</DropdownMenu.CheckboxItem>
							{/each}
							{#if tabIterations.some((s) => !comparable(s))}
								<DropdownMenu.Separator />
								<p class="max-w-64 px-2 py-1 text-xs text-gray-500">
									Iterations for another scenario have other targets; check a scenario to compare
									them by their objective values.
								</p>
							{/if}
						</DropdownMenu.Content>
					</DropdownMenu.Root>
				{/if}
				{#if finalId !== null}
					<span
						class="shrink-0 rounded bg-green-100 px-1.5 py-0.5 text-xs whitespace-nowrap text-green-800"
						title="Final design"
					>
						Final #{finalId}
					</span>
				{/if}
			</div>
		{/if}
	{/snippet}

	{#snippet visualizationArea()}
		{#if problem && setup && ready && tab === 'robustness'}
			<RobustnessPanel
				{problem}
				{setup}
				{scenarioModels}
				{designs}
				{wishlist}
				{evaluations}
				objectiveRanges={objRanges}
				bind:selectedId={selectedDesignId}
				bind:evaluationId
				bind:evaluateModelId
				bind:evaluateDesignIds
				bind:thresholds
				onEvaluate={runEvaluate}
			/>
		{:else if problem && setup && ready && tab === 'antifragility'}
			<AntifragilityPanel
				{problem}
				{setup}
				{evaluations}
				bind:selectedId={selectedDesignId}
				bind:evaluationId
				bind:result={antifragilityResult}
				bind:inputs={antifragilityInputs}
				onAnalyse={runAntifragility}
			/>
		{:else if !problem}
			<div class="flex h-full items-center justify-center text-gray-500">
				Select a problem with a scenario model to use JINA.
			</div>
		{:else if !ready}
			<div class="flex h-full items-center justify-center text-gray-500">Set up JINA to start.</div>
		{:else if !iteration}
			<div class="flex h-full items-center justify-center text-gray-500">
				Give a reference point and solve.
			</div>
		{:else}
			<Resizable.PaneGroup direction="horizontal" class="h-full">
				<Resizable.Pane defaultSize={50} minSize={30} class="h-full p-2">
					{#if !iteration.is_ready}
						<div class="flex h-full items-center justify-center text-gray-500">Solving…</div>
					{:else if !chart || chart.designIds.length === 0}
						<div class="flex h-full items-center justify-center text-gray-500">
							{iteration.error ??
								(allHidden
									? 'All designs are hidden. Use Show all or the eye icons to plot them.'
									: iteration.result.results.some((r) => r.success && r.design_id != null)
										? 'No visible designs to plot.'
										: emptyMessage)}
						</div>
					{:else}
						<div class="flex h-full flex-col">
							<div class="min-h-0 flex-1">
								<VisualizationsPanel
									problem={chart.problem}
									solutionsObjectiveValues={chart.values}
									currentPreferenceValues={chart.reference ?? []}
									previousPreferenceValues={chart.previous}
									currentPreferenceType={PREFERENCE_TYPES.ReferencePoint}
									previousPreferenceType={PREFERENCE_TYPES.ReferencePoint}
									externalSelectedIndexes={chartSelected}
									onSelectSolution={(index: number) => {
										selectedDesignId = chart?.designIds[index] ?? null;
										clickedRowKey = chart?.rowKeys?.[index] ?? null;
									}}
									lineLabels={Object.fromEntries(
										chart.labels.map((label, i) => [String(i), label])
									)}
									colorByIndex={chart.colors}
									showHeader={false}
									verticalAxisLabels
									compactTickLabels
									fitMargins
									improvementArrows
									minAxisSpacing={80}
									referenceDataLabels={{
										currentRefLabel: chart.referenceLabel,
										previousRefLabel: chart.previousLabel
									}}
								/>
							</div>
							{#if chart.note}
								<p class="shrink-0 text-xs text-gray-500">{chart.note}</p>
							{/if}
						</div>
					{/if}
				</Resizable.Pane>
				<ResizableHandle withHandle />
				<Resizable.Pane defaultSize={50} minSize={30} class="h-full">
					<div class="h-full min-w-0 space-y-3 overflow-auto p-2">
						<ScenarioPicker
							leaves={leafOrder}
							baselineLeaf={setup?.result.baseline_leaf ?? null}
							bind:checked={
								() => chartSelection.leaves, (leaves: string[]) => selectChart({ leaves })
							}
							aggregate={aggregateEntry}
							bind:aggregateChecked={
								() => chartSelection.aggregate, (aggregate: boolean) => selectChart({ aggregate })
							}
						/>
						{#if view === 'scenario_optimal' ? selectedRow : selectedDesign}
							<div class="border-t pt-2">
								<h3 class="mb-1 text-sm font-semibold">
									Design #{selectedDesignId}
									{selectedRow
										? `(${selectedRow.result.name}) by scenario, optimised for ${selectedRow.leaf}`
										: 'by scenario'}
								</h3>
								<ScenarioBreakdown
									{problem}
									leafObjectives={selectedOutcomes ?? selectedDesign?.leaf_objectives ?? {}}
									baselineLeaf={setup?.result.baseline_leaf ?? null}
									{leafColors}
									checkedLeaves={objectiveMode ? chartSelection.leaves : []}
								/>
							</div>
						{:else}
							<p class="text-sm text-gray-500">
								Select a {view === 'scenario_optimal' ? 'row or line' : 'design'} to see its values by
								scenario.
							</p>
						{/if}
					</div>
				</Resizable.Pane>
			</Resizable.PaneGroup>
		{/if}
	{/snippet}

	{#snippet numericalValues()}
		{#if problem && setup && iteration?.is_ready && iteration.result.results.length === 0}
			<p class="p-2 text-sm text-gray-500">{iteration.error ?? emptyMessage}</p>
		{:else if problem && setup && iteration}
			<DesignTable
				{problem}
				targets={iterationTargets}
				results={iteration.result.results}
				{designs}
				designVariables={setup.result.design_variables}
				bind:selectedId={selectedDesignId}
				bind:selectedName={
					() =>
						view !== 'scenario_optimal'
							? undefined
							: selectedRow?.stateId === iteration.state_id
								? selectedRow.result.name
								: null,
					(name: string | null | undefined) =>
						(clickedRowKey = name ? rowKey(iteration.state_id, name) : null)
				}
				bind:hidden={hiddenDesigns}
			/>
		{/if}
	{/snippet}

	{#snippet rightSidebar()}
		<div class="flex flex-col gap-3 p-3 pb-0">
			{#if setup && setupModel}
				<div class="space-y-1 text-xs text-gray-600">
					<p class="truncate" title={modelLabel(setupModel, true)}>
						Scenario model {modelLabel(setupModel)}
					</p>
					<p>
						Aggregation: {MEASURE_LABELS[setup.result.measure]}{setup.result.measure === 'cvar'
							? ` (α = ${setup.result.cvar_alpha})`
							: ''}
					</p>
					<p>Design variables: {setup.result.design_variables.join(', ')}</p>
					<p>Baseline leaf: {setup.result.baseline_leaf ?? 'none'}</p>
				</div>
			{/if}
			<Button variant="outline" size="sm" class="self-start" onclick={() => (showSetup = true)}>
				{setup ? 'New setup' : 'Set up'}
			</Button>
			{#if setupJobId !== null}
				<JobStatus
					stateId={setupJobId}
					label="Computing target ranges"
					onDone={setupDone}
					onDismiss={() => (setupJobId = null)}
				/>
			{/if}
		</div>
		{#if problem && setup && ready}
			{#key setup.state_id}
				<div class="min-w-0 space-y-3 p-3">
					{#each pending as job (job.id)}
						<JobStatus
							stateId={job.id}
							label={job.label}
							onDone={jobDone}
							onDismiss={() => (pending = pending.filter((p) => p.id !== job.id))}
						/>
					{/each}
					<WishlistPanel
						{problem}
						{designs}
						{wishlist}
						{finalId}
						bind:selectedId={selectedDesignId}
						{representativeSets}
						importObjectives={setupModel?.objectives ?? []}
						objectiveRanges={objRanges}
						onSave={saveSelection}
						onImport={runImport}
					/>
				</div>
			{/key}
		{/if}
	{/snippet}
</BaseLayout>
