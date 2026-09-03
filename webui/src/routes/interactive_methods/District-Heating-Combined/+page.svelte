<script lang="ts">
	/**
	 * JINA (interactive combined multi-scenario) — reference-point matching with no worst-case
	 * aggregation.
	 *
	 * The sibling "JINA (interactive two-stage robustness)" method collapses each objective to its worst
	 * case across the scenarios and asks for one aspiration level per objective. That is a strong
	 * assumption: one target has to speak for every scenario, so "zero unmet demand under a demand
	 * spike, but a loose cost target under a price spike" cannot be said at all.
	 *
	 * This method keeps the combined problem un-aggregated — one objective per (objective,
	 * scenario) cell — and takes an aspiration level for every cell. One ASF solve honours all of
	 * them at once and reports which cells *bind*, i.e. which aspirations the solution is actually
	 * limited by. Those are the only ones worth relaxing.
	 *
	 * The analysis cards below follow the multi-scenario method's pattern (wish list, trade-off and
	 * per-scenario views, domain criterion) so a DM moving between the two reads them the same way.
	 * One difference is structural: a solve here produces one design per round, not one per
	 * scalarizer variant, so designs accumulate across iterations rather than arriving in batches.
	 *
	 * Port of the decision maker's `only-combined-multiscenario-multiobjective.ipynb`. Every label,
	 * scenario name and range comes from the backend — nothing here is hard-coded to district
	 * heating.
	 */
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import * as Card from '$lib/components/ui/card';
	import * as Table from '$lib/components/ui/table';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Badge } from '$lib/components/ui/badge';
	import ParallelCoordinates from '$lib/components/visualizations/parallel-coordinates/parallel-coordinates.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';
	import {
		combinedWishlistAdd,
		combinedWishlistRemove,
		getCombinedAnalysis,
		getCombinedSessionTree,
		getOrInitializeCombined,
		initializeCombined,
		runCombinedIteration
	} from './handlers';
	import {
		SOLUTION_COLORS,
		type CombinedAnalysisResult,
		type CombinedCell,
		type CombinedCellResult,
		type CombinedGrid,
		type CombinedResult,
		type CombinedSessionTreeEntry,
		type CombinedSolution
	} from './types';

	const { data } = $props<{ data: { problems: ProblemInfo[] } }>();
	let problem_list = $derived(data.problems ?? []);
	let problem = $state<ProblemInfo | null>(null);
	let problemId: number | null = $state(null);
	let sessionId: number | null = $state(null);

	let grid: CombinedGrid | null = $state(null);
	let current: CombinedResult | null = $state(null);
	let sessionTree: CombinedSessionTreeEntry[] = $state([]);
	let wishList: number[] = $state([]);
	let loading = $state(false);
	let solving = $state(false);
	let errorText: string | null = $state(null);

	/** Aspiration level per cell symbol. Null until the DM (or the row-fill below) sets one. */
	let levels: Record<string, number | null> = $state({});
	/** One value per base objective, used to fill that objective's whole row at once. */
	let rowFill: Record<string, number | null> = $state({});
	let note = $state('');

	function fmt(v: number | null | undefined): string {
		if (v === null || v === undefined || !Number.isFinite(v as number)) return '—';
		return (v as number).toLocaleString(undefined, { maximumFractionDigits: 1 });
	}

	// Every read of `grid`/`current` goes through a `$derived.by` closure. A top-level
	// `$derived(grid?.cells ?? [])` is a plain expression, and TypeScript's control-flow analysis
	// narrows `grid` to its `null` initializer there — collapsing the chain to `never` and every
	// callback parameter below it to an implicit `any`.
	let cells: CombinedCell[] = $derived.by(() => grid?.cells ?? []);
	let scenarios: string[] = $derived.by(() => grid?.scenarios ?? []);
	let objectives: string[] = $derived.by(() => grid?.objectives ?? []);
	let objectiveLabels: Record<string, string> = $derived.by(() => grid?.objective_labels ?? {});

	let cellsBySymbol = $derived.by(() => {
		const map: Record<string, CombinedCell> = {};
		for (const c of cells) map[c.symbol] = c;
		return map;
	});

	// A shared objective (one that depends only on the first-stage decision, so it cannot differ
	// between scenarios) has a single cell rather than one per scenario. Splitting the two kinds
	// keeps the grid honest: repeating a shared objective across every scenario column would invite
	// the DM to set several different targets for something that can only take one value.
	let sharedCells = $derived.by(() => cells.filter((c) => c.shared));
	let scenarioObjectives = $derived.by(() => {
		const seen = new Set(cells.filter((c) => !c.shared).map((c) => c.obj_symbol));
		return objectives.filter((o) => seen.has(o));
	});

	function cellFor(objSymbol: string, scenario: string): CombinedCell | null {
		return (
			cells.find((c) => !c.shared && c.obj_symbol === objSymbol && c.scenario === scenario) ?? null
		);
	}

	/** Every cell filled in? The ASF scalarizes exactly the cells it is given, so a partial grid
	 *  would silently drop cells from the solve — the backend rejects it and so does this. */
	let missingCount = $derived.by(
		() =>
			cells.filter((c) => {
				const v = levels[c.symbol];
				return v === null || v === undefined || !Number.isFinite(v);
			}).length
	);
	let canSolve = $derived(cells.length > 0 && missingCount === 0 && !solving);

	function applyRowFill(objSymbol: string) {
		const v = rowFill[objSymbol];
		if (v === null || v === undefined || !Number.isFinite(v)) return;
		for (const c of cells) {
			if (c.obj_symbol === objSymbol) levels[c.symbol] = v;
		}
	}

	/** Fill everything with each cell's own ideal — the notebook's default template. Not jointly
	 *  attainable (each ideal assumes the investment is tailored to that one scenario), which is
	 *  the point: a starting position to relax from, not a proposal. */
	function fillWithIdeals() {
		for (const c of cells) levels[c.symbol] = c.ideal;
		for (const o of objectives) {
			const first = cells.find((c) => c.obj_symbol === o);
			rowFill[o] = first ? first.ideal : null;
		}
	}

	// --- Designs discovered this session --------------------------------------------------------
	// One solve per round means designs arrive one at a time, and the same build can resurface in a
	// later round (the backend gives it back its original id). Deduplicating by design_id here is
	// what keeps the charts, the wish list and the domain criterion from counting it twice.
	let designs = $derived.by(() => {
		const byId = new Map<number, { solution: CombinedSolution; iteration: number }>();
		for (const entry of sessionTree) {
			const sol = entry.solution;
			if (!sol) continue;
			if (!byId.has(sol.design_id)) byId.set(sol.design_id, { solution: sol, iteration: entry.iteration_number });
		}
		return [...byId.values()].sort((a, b) => a.solution.solution_number - b.solution.solution_number);
	});

	let selectedDesignId: number | null = $state(null);

	function designColor(designId: number): string {
		const idx = designs.findIndex((d) => d.solution.design_id === designId);
		return SOLUTION_COLORS[(idx < 0 ? 0 : idx) % SOLUTION_COLORS.length];
	}

	function toggleDesignSelection(designId: number | null) {
		selectedDesignId = selectedDesignId === designId ? null : designId;
	}

	// --- Trade-off + per-scenario views ---------------------------------------------------------
	// Axis ranges span each objective's envelope over all of its cells (best ideal to worst nadir),
	// so every panel and every line is on one scale and a line's height means the same thing
	// everywhere — the same guarantee the multi-scenario method's shared ranges give.
	let axisRanges = $derived.by(() => {
		const ranges: Record<string, [number, number]> = {};
		for (const obj of objectives) {
			const objCells = cells.filter((c) => c.obj_symbol === obj);
			if (objCells.length === 0) {
				ranges[obj] = [0, 1];
				continue;
			}
			let lo = Math.min(...objCells.map((c) => Math.min(c.ideal, c.nadir)));
			let hi = Math.max(...objCells.map((c) => Math.max(c.ideal, c.nadir)));
			if (hi === lo) {
				const pad = Math.abs(lo) * 0.01 || 1.0;
				lo -= pad;
				hi += pad;
			}
			ranges[obj] = [lo, hi];
		}
		return ranges;
	});

	let objDirections = $derived.by(() => {
		const dirs: Record<string, 'min' | 'max'> = {};
		for (const obj of objectives) {
			dirs[obj] = cells.find((c) => c.obj_symbol === obj)?.maximize ? 'max' : 'min';
		}
		return dirs;
	});

	function shortLabel(obj: string): string {
		const label = objectiveLabels[obj] ?? obj;
		return label.length > 14 ? `${label.slice(0, 13)}…` : label;
	}

	/** One row per (design, scenario) pair, plus the ordinal Scenario axis so the chart can be
	 *  brushed down to a single scenario. */
	let chartRows = $derived.by(() => {
		const rows: Record<string, number>[] = [];
		for (const d of designs) {
			for (const br of d.solution.breakdown) {
				const scenarioName = String(br.scenario);
				const sIdx = scenarios.indexOf(scenarioName);
				const row: Record<string, number> = {};
				for (const obj of objectives) {
					const v = br[obj];
					if (typeof v === 'number') row[obj] = v;
				}
				row.scenario_idx = sIdx >= 0 ? sIdx + 1 : 0;
				rows.push(row);
			}
		}
		return rows;
	});

	let chartRowDesignId = $derived.by(() => {
		const out: number[] = [];
		for (const d of designs) {
			for (let i = 0; i < d.solution.breakdown.length; i += 1) out.push(d.solution.design_id);
		}
		return out;
	});

	const MUTED_LINE_COLOR = '#d4d4d8';

	let chartColorByIndex = $derived.by(() => {
		const map: Record<string, string> = {};
		chartRowDesignId.forEach((designId, row) => {
			map[String(row)] =
				selectedDesignId === null || selectedDesignId === designId
					? designColor(designId)
					: MUTED_LINE_COLOR;
		});
		return map;
	});

	let chartLineLabels = $derived.by(() => {
		const map: Record<string, string> = {};
		let row = 0;
		for (const d of designs) {
			for (const br of d.solution.breakdown) {
				const values = objectives
					.map((obj) => {
						const v = br[obj];
						return `${shortLabel(obj)}: ${typeof v === 'number' ? fmt(v) : '—'}`;
					})
					.join('<br>');
				map[String(row)] =
					`<strong>Solution ${d.solution.solution_number}</strong> (design ${d.solution.design_id}) — ${String(br.scenario)}<br>${values}`;
				row += 1;
			}
		}
		return map;
	});

	let chartDimensions = $derived.by(() => [
		...objectives.map((obj) => ({
			symbol: obj,
			name: shortLabel(obj),
			min: axisRanges[obj]?.[0] ?? 0,
			max: axisRanges[obj]?.[1] ?? 1,
			direction: objDirections[obj] ?? ('min' as 'min' | 'max')
		})),
		...(scenarios.length > 0
			? [{ symbol: 'scenario_idx', name: 'Scenario', min: 1, max: scenarios.length, categories: scenarios }]
			: [])
	]);

	// One panel per scenario, all on the shared ranges above.
	let panelDimensions = $derived.by(() =>
		objectives.map((obj) => ({
			symbol: obj,
			name: shortLabel(obj),
			min: axisRanges[obj]?.[0] ?? 0,
			max: axisRanges[obj]?.[1] ?? 1,
			direction: objDirections[obj] ?? ('min' as 'min' | 'max')
		}))
	);

	const PANEL_OPTIONS = {
		showAxisLabels: true,
		highlightOnHover: true,
		strokeWidth: 2,
		opacity: 0.7,
		enableBrushing: false
	};

	let scenarioPanels = $derived.by(() =>
		scenarios.map((scenario, sIdx) => {
			const rows: Record<string, number>[] = [];
			const designIdByRow: number[] = [];
			for (const d of designs) {
				const br = d.solution.breakdown.find((b) => String(b.scenario) === scenario);
				if (!br) continue;
				const row: Record<string, number> = {};
				for (const obj of objectives) {
					const v = br[obj];
					if (typeof v === 'number') row[obj] = v;
				}
				rows.push(row);
				designIdByRow.push(d.solution.design_id);
			}
			return { scenario, number: sIdx + 1, rows, designIdByRow };
		})
	);

	function panelColorByIndex(designIdByRow: number[]): Record<string, string> {
		const map: Record<string, string> = {};
		designIdByRow.forEach((designId, row) => {
			map[String(row)] =
				selectedDesignId === null || selectedDesignId === designId
					? designColor(designId)
					: MUTED_LINE_COLOR;
		});
		return map;
	}

	function panelLineLabels(panel: { rows: Record<string, number>[]; designIdByRow: number[] }) {
		const map: Record<string, string> = {};
		panel.designIdByRow.forEach((designId, row) => {
			const d = designs.find((x) => x.solution.design_id === designId);
			if (!d) return;
			const values = objectives
				.map((obj) => `${shortLabel(obj)}: ${fmt(panel.rows[row]?.[obj])}`)
				.join('<br>');
			map[String(row)] =
				`<strong>Solution ${d.solution.solution_number}</strong> (design ${designId})<br>${values}`;
		});
		return map;
	}

	let panelAxisLegend = $derived.by(() =>
		objectives.map((obj) => ({
			symbol: obj,
			label: objectiveLabels[obj] ?? obj,
			range: axisRanges[obj] ?? [0, 1]
		}))
	);

	// --- Domain criterion -----------------------------------------------------------------------
	let domainThresholds: Record<string, number | null> = $state({});
	let domainThresholdsSeeded = $state(false);
	let analysis: CombinedAnalysisResult | null = $state(null);
	let analysisLoading = $state(false);
	let analysisError: string | null = $state(null);

	let thresholdedObjectives = $derived.by(() =>
		objectives.filter((o) => {
			const v = domainThresholds[o];
			return v !== null && v !== undefined && Number.isFinite(v);
		})
	);

	// Only objectives that actually carry a count get an axis. The backend returns null for an
	// objective with no threshold (it is excluded from the criterion rather than counted as
	// passing), and `Number(null)` is 0 — which would draw a full-height "met in 0 scenarios" axis
	// for something that was never assessed at all.
	let domainChartObjectives = $derived.by(() => {
		const rows = analysis?.domain_criterion ?? [];
		if (rows.length === 0) return [];
		return objectives.filter((obj) => rows.some((r) => typeof r[obj] === 'number'));
	});

	let domainChartRows = $derived.by(() =>
		(analysis?.domain_criterion ?? []).map((r) => {
			const out: Record<string, number> = {};
			for (const obj of domainChartObjectives) out[obj] = Number(r[obj]);
			return out;
		})
	);

	let domainDimensions = $derived.by(() =>
		domainChartObjectives.map((obj) => ({
			symbol: obj,
			name: `${shortLabel(obj)} met`,
			min: 0,
			max: analysis?.scenario_count ?? scenarios.length,
			// Higher is better here regardless of the objective's own direction: the axis counts
			// scenarios where the threshold held, not the objective value.
			direction: 'max' as const
		}))
	);

	let domainColorByIndex = $derived.by(() => {
		const map: Record<string, string> = {};
		(analysis?.domain_criterion ?? []).forEach((r, i) => {
			map[String(i)] = designColor(r.design_id);
		});
		return map;
	});

	let domainLineLabels = $derived.by(() => {
		const map: Record<string, string> = {};
		const total = analysis?.scenario_count ?? scenarios.length;
		(analysis?.domain_criterion ?? []).forEach((r, i) => {
			const d = designs.find((x) => x.solution.design_id === r.design_id);
			const name = d ? `Solution ${d.solution.solution_number}` : `Design ${r.design_id}`;
			const counts = domainChartObjectives
				.map((obj) => `${shortLabel(obj)}: ${r[obj]} / ${total}`)
				.join('<br>');
			map[String(i)] = `<strong>${name}</strong> (design ${r.design_id})<br>${counts}`;
		});
		return map;
	});

	async function loadAnalysis() {
		if (problemId === null) return;
		analysisLoading = true;
		analysisError = null;
		try {
			const thresholds: Record<string, number> = {};
			for (const o of thresholdedObjectives) thresholds[o] = domainThresholds[o] as number;
			analysis = await getCombinedAnalysis({
				problem_id: problemId,
				...(sessionId != null ? { session_id: sessionId } : {}),
				domain_thresholds: thresholds
			});
		} catch (e) {
			analysis = null;
			analysisError = e instanceof Error ? e.message : 'Failed to run the analysis.';
		} finally {
			analysisLoading = false;
		}
	}

	// --- Loading and actions --------------------------------------------------------------------
	async function loadAll() {
		if (problemId === null) return;
		loading = true;
		errorText = null;
		try {
			grid = await initializeCombined(problemId, sessionId);
			if (Object.keys(levels).length === 0) fillWithIdeals();
			current = await getOrInitializeCombined(problemId, sessionId);
			wishList = current.wish_list ?? [];
			if (!domainThresholdsSeeded) {
				domainThresholds = { ...(current.default_domain_thresholds ?? {}) };
				domainThresholdsSeeded = true;
			}
			// Resuming a session: start from the reference point that produced the last round, so a
			// DM picks up where they left off instead of retyping every cell.
			if (current.iteration_number > 0 && Object.keys(current.reference_point ?? {}).length > 0) {
				for (const [sym, v] of Object.entries(current.reference_point)) levels[sym] = v;
			}
			sessionTree = await getCombinedSessionTree(problemId, sessionId);
		} catch (e) {
			errorText = e instanceof Error ? e.message : 'Failed to load the method state.';
		} finally {
			loading = false;
		}
	}

	async function handleSolve() {
		if (problemId === null || !canSolve) return;
		solving = true;
		errorText = null;
		try {
			const reference_point: Record<string, number> = {};
			for (const c of cells) reference_point[c.symbol] = levels[c.symbol] as number;
			current = await runCombinedIteration({
				problem_id: problemId,
				...(sessionId != null ? { session_id: sessionId } : {}),
				reference_point,
				...(note.trim() ? { note: note.trim() } : {})
			});
			wishList = current.wish_list ?? [];
			sessionTree = await getCombinedSessionTree(problemId, sessionId);
			if (current.solution) selectedDesignId = null;
		} catch (e) {
			errorText = e instanceof Error ? e.message : 'Failed to run the iteration.';
		} finally {
			solving = false;
		}
	}

	async function handleWishlist(designId: number, add: boolean) {
		if (problemId === null) return;
		errorText = null;
		try {
			const body = {
				problem_id: problemId,
				...(sessionId != null ? { session_id: sessionId } : {}),
				design_ids: [designId]
			};
			const res = add ? await combinedWishlistAdd(body) : await combinedWishlistRemove(body);
			wishList = res.wish_list;
			// The domain criterion is computed over the wish list, so a stale table after a change
			// would be actively misleading rather than merely out of date.
			if (analysis) await loadAnalysis();
		} catch (e) {
			errorText = e instanceof Error ? e.message : 'Failed to update the wish list.';
		}
	}

	onMount(() => {
		sessionId = $methodSelection.selectedSessionId;
		problemId = $methodSelection.selectedProblemId;
		if (problemId !== null) {
			problem = problem_list.find((p: ProblemInfo) => String(p.id) === String(problemId)) ?? null;
			loadAll();
		}
	});
</script>

<svelte:head>
	<title>JINA (interactive combined multi-scenario) | DESDEO</title>
	<meta
		name="description"
		content="Reference-point matching with one aspiration level per (objective, scenario) cell — no worst-case aggregation."
	/>
</svelte:head>

<div class="container mx-auto max-w-6xl space-y-6 px-4 py-8">
	<div>
		<h1 class="text-3xl font-bold tracking-tight">JINA (interactive combined multi-scenario)</h1>
		<p class="text-muted-foreground mt-1 text-sm italic">JINA: Joint Infrastructure Network Adaptation</p>
		<p class="text-muted-foreground mt-1">
			One aspiration level per <strong>(objective, scenario)</strong> cell — no worst-case
			aggregation. Set a different target in each scenario (zero unmet demand under a demand
			spike, a loose cost target under a price spike) and one solve honours them all at once,
			reporting which of your aspirations the solution is actually limited by.
		</p>
		{#if problem}
			<p class="text-muted-foreground mt-2 text-sm">
				Problem: <strong>{problem.name}</strong>
				<a href="/methods/initialize" class="ml-2 underline">Change</a>
			</p>
		{/if}
	</div>

	{#if problemId === null}
		<Card.Root>
			<Card.Header>
				<Card.Title>Select a problem first</Card.Title>
				<Card.Description>
					This method needs a DESDEO problem with an attached scenario model — the same problems
					the multi-scenario method works with. Pick one from the methods page before starting.
				</Card.Description>
			</Card.Header>
			<Card.Content>
				<Button onclick={() => goto('/methods/initialize')}>Choose a problem</Button>
			</Card.Content>
		</Card.Root>
	{:else}
		{#if errorText}
			<div class="rounded-md border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-800">
				{errorText}
			</div>
		{/if}

		{#if loading}
			<Card.Root>
				<Card.Content class="text-muted-foreground py-6 text-sm">
					Building the combined problem and computing each cell's attainable range — this runs one
					payoff table per scenario and can take a minute on first load.
				</Card.Content>
			</Card.Root>
		{/if}

		{#if grid}
			<Card.Root>
				<Card.Header>
					<Card.Title>Set aspiration levels</Card.Title>
					<Card.Description>
						{cells.length} cells: {scenarioObjectives.length} objective(s) × {scenarios.length}
						scenarios{#if sharedCells.length > 0}, plus {sharedCells.length} shared objective(s) that
							do not vary by scenario{/if}. Each input shows its own attainable span — ideal is
						what that objective could reach if the investment were tailored to that scenario
						<em>alone</em>, so the ideals are not jointly reachable. Use the row-fill boxes to set a
						whole objective at once, then override only the cells you care about.
					</Card.Description>
				</Card.Header>
				<Card.Content class="space-y-4">
					<div class="flex flex-wrap items-end gap-3 rounded-md border p-3">
						<span class="text-sm font-medium">Fill a whole objective:</span>
						{#each objectives as obj (obj)}
							<div>
								<Label for={`fill-${obj}`} class="text-xs">{objectiveLabels[obj] ?? obj}</Label>
								<div class="flex gap-1">
									<Input
										id={`fill-${obj}`}
										type="number"
										class="w-40"
										bind:value={rowFill[obj]}
										placeholder="raw value"
									/>
									<Button size="sm" variant="outline" onclick={() => applyRowFill(obj)}>Apply</Button>
								</div>
							</div>
						{/each}
						<Button size="sm" variant="ghost" onclick={fillWithIdeals}>Reset to ideals</Button>
					</div>

					{#if scenarioObjectives.length > 0}
						<div class="overflow-x-auto">
							<Table.Root>
								<Table.Header>
									<Table.Row>
										<Table.Head>Scenario</Table.Head>
										{#each scenarioObjectives as obj (obj)}
											<Table.Head>{objectiveLabels[obj] ?? obj}</Table.Head>
										{/each}
									</Table.Row>
								</Table.Header>
								<Table.Body>
									{#each scenarios as scenario, si (scenario)}
										<Table.Row>
											<Table.Cell class="font-medium">{si + 1}. {scenario}</Table.Cell>
											{#each scenarioObjectives as obj (obj)}
												{@const cell = cellFor(obj, scenario)}
												<Table.Cell>
													{#if cell}
														<Input
															type="number"
															class="w-40"
															bind:value={levels[cell.symbol]}
															placeholder="aspiration"
														/>
														<p class="text-muted-foreground mt-1 text-xs">
															ideal {fmt(cell.ideal)} · nadir {fmt(cell.nadir)}
														</p>
													{:else}
														<span class="text-muted-foreground text-xs">—</span>
													{/if}
												</Table.Cell>
											{/each}
										</Table.Row>
									{/each}
								</Table.Body>
							</Table.Root>
						</div>
					{/if}

					{#if sharedCells.length > 0}
						<div class="rounded-md border p-3">
							<p class="mb-1 text-sm font-medium">Shared across all scenarios</p>
							<p class="text-muted-foreground mb-3 text-xs">
								These depend only on the first-stage decision, so they take the same value in every
								scenario and get one aspiration level rather than one per scenario.
							</p>
							<div class="flex flex-wrap gap-4">
								{#each sharedCells as cell (cell.symbol)}
									<div>
										<Label for={`shared-${cell.symbol}`} class="text-xs">{cell.label}</Label>
										<Input
											id={`shared-${cell.symbol}`}
											type="number"
											class="w-48"
											bind:value={levels[cell.symbol]}
											placeholder="aspiration"
										/>
										<p class="text-muted-foreground mt-1 text-xs">
											ideal {fmt(cell.ideal)} · nadir {fmt(cell.nadir)}
										</p>
									</div>
								{/each}
							</div>
						</div>
					{/if}

					<div class="flex flex-wrap items-end gap-3">
						<div>
							<Label for="combined-note" class="text-xs">Note (optional)</Label>
							<Input id="combined-note" class="w-64" bind:value={note} placeholder="e.g. round 2" />
						</div>
						<Button disabled={!canSolve} onclick={handleSolve}>
							{solving ? 'Solving live (this can take a minute)…' : 'Run iteration'}
						</Button>
						{#if missingCount > 0}
							<p class="text-muted-foreground text-xs">
								{missingCount} cell(s) still empty — every cell needs a level, or it would be left
								out of the solve entirely.
							</p>
						{/if}
					</div>
				</Card.Content>
			</Card.Root>
		{/if}

		{#if current?.solution}
			{@const sol = current.solution}
			<Card.Root>
				<Card.Header>
					<Card.Title>Iteration {current.iteration_number} — result</Card.Title>
					<Card.Description>
						{#if sol.all_reached}
							Every aspiration level was reached (α = {fmt(sol.alpha)} ≤ 0) — the targets were loose
							enough that the solution cleared all of them, so there is room to ask for more.
						{:else}
							α = {fmt(sol.alpha)}: the largest shortfall over all cells, on the shared scaled axis.
							The cells marked <strong>binds</strong> are the ones the solution is limited by —
							relaxing one of those is what buys improvement elsewhere; relaxing any other cell
							changes nothing.
						{/if}
					</Card.Description>
				</Card.Header>
				<Card.Content class="space-y-4">
					<div class="flex flex-wrap items-center gap-3">
						<span class="flex items-center gap-1.5 text-sm font-medium">
							<span
								class="inline-block h-3 w-3 rounded-full"
								style={`background-color:${designColor(sol.design_id)}`}
							></span>
							Solution {sol.solution_number} (design {sol.design_id})
						</span>
						{#if sol.repeat}
							<Badge variant="outline">repeat of an earlier round</Badge>
						{/if}
						{#if wishList.includes(sol.design_id)}
							<Button size="sm" variant="outline" onclick={() => handleWishlist(sol.design_id, false)}>
								Remove from wish list
							</Button>
						{:else}
							<Button size="sm" onclick={() => handleWishlist(sol.design_id, true)}>
								Add to wish list
							</Button>
						{/if}
					</div>

					<div class="overflow-x-auto">
						<Table.Root>
							<Table.Header>
								<Table.Row>
									<Table.Head>(objective, scenario)</Table.Head>
									<Table.Head>Aspiration</Table.Head>
									<Table.Head>Achieved</Table.Head>
									<Table.Head>Scaled</Table.Head>
									<Table.Head></Table.Head>
								</Table.Row>
							</Table.Header>
							<Table.Body>
								{#each sol.cell_results as r (r.symbol)}
									{@const cell = cellsBySymbol[r.symbol]}
									<Table.Row>
										<Table.Cell class="font-medium">
											{cell ? cell.label : r.symbol}
											{#if cell && !cell.shared}
												<span class="text-muted-foreground">· {cell.scenario}</span>
											{:else if cell}
												<span class="text-muted-foreground">· all scenarios</span>
											{/if}
										</Table.Cell>
										<Table.Cell>{fmt(r.aspiration)}</Table.Cell>
										<Table.Cell>{fmt(r.achieved)}</Table.Cell>
										<Table.Cell>{r.scaled.toFixed(3)}</Table.Cell>
										<Table.Cell>
											{#if r.binds}<Badge>binds</Badge>{/if}
										</Table.Cell>
									</Table.Row>
								{/each}
							</Table.Body>
						</Table.Root>
					</div>

					{#if Object.keys(sol.strategic_values).length > 0}
						<div class="rounded-md border p-3">
							<p class="mb-2 text-sm font-medium">First-stage capacities this solution builds</p>
							<div class="flex flex-wrap gap-x-6 gap-y-1 text-sm">
								{#each Object.entries(sol.strategic_values) as [sym, value] (sym)}
									<span>
										<span class="text-muted-foreground">{sym}:</span>
										{fmt(value)}
									</span>
								{/each}
							</div>
						</div>
					{/if}
				</Card.Content>
			</Card.Root>
		{/if}

		{#if designs.length > 0}
			<Card.Root>
				<Card.Header>
					<Card.Title>Trade-off view</Card.Title>
					<Card.Description>
						Each line is one (design, scenario) pair — {scenarios.length} lines per design, its full
						performance across the scenarios. Lines sharing a colour belong to the same design.
						Drag on the Scenario axis (right) to narrow to a single scenario. Designs accumulate
						across iterations: one solve produces one design, so this fills in as you go.
					</Card.Description>
				</Card.Header>
				<Card.Content class="space-y-3">
					<div class="flex flex-wrap items-center gap-2">
						{#each designs as d (d.solution.design_id)}
							<button
								type="button"
								class="hover:bg-accent flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs"
								class:opacity-40={selectedDesignId !== null && selectedDesignId !== d.solution.design_id}
								class:border-foreground={selectedDesignId === d.solution.design_id}
								onclick={() => toggleDesignSelection(d.solution.design_id)}
							>
								<span
									class="inline-block h-3 w-3 rounded-full"
									style={`background-color:${designColor(d.solution.design_id)}`}
								></span>
								Solution {d.solution.solution_number}
							</button>
						{/each}
						{#if selectedDesignId !== null}
							<Button size="sm" variant="ghost" onclick={() => (selectedDesignId = null)}>Clear</Button>
						{/if}
					</div>
					<div style="height: 420px;">
						<ParallelCoordinates
							data={chartRows}
							dimensions={chartDimensions}
							colorByIndex={chartColorByIndex}
							lineLabels={chartLineLabels}
						/>
					</div>
				</Card.Content>
			</Card.Root>

			<Card.Root>
				<Card.Header>
					<Card.Title>Per-scenario view</Card.Title>
					<Card.Description>
						The same designs, split into one panel per scenario. All panels share the axis ranges of
						the trade-off view above, so a line's height means the same thing in each of them. Tick
						numbers are compact ("-32.1M", "7.9k"); hover any line for its exact values. Click a
						solution above to follow one design across all {scenarios.length} scenarios at once.
					</Card.Description>
				</Card.Header>
				<Card.Content class="space-y-4">
					<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs">
						{#each panelAxisLegend as ax (ax.symbol)}
							<span class="flex items-center gap-1.5">
								<span class="font-medium">{ax.label}</span>
								<span class="text-muted-foreground">{fmt(ax.range[0])} – {fmt(ax.range[1])}</span>
							</span>
						{/each}
					</div>
					<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
						{#each scenarioPanels as panel (panel.scenario)}
							<div class="rounded-md border p-2">
								<p class="mb-1 truncate text-xs font-medium" title={panel.scenario}>
									{panel.number}. {panel.scenario}
								</p>
								{#if panel.rows.length > 0}
									<div style="height: 220px;">
										<ParallelCoordinates
											data={panel.rows}
											dimensions={panelDimensions}
											options={PANEL_OPTIONS}
											showTickLabels={true}
											compactTickLabels={true}
											verticalAxisLabels={true}
											colorByIndex={panelColorByIndex(panel.designIdByRow)}
											lineLabels={panelLineLabels(panel)}
										/>
									</div>
								{:else}
									<p class="text-muted-foreground py-6 text-center text-xs">No data</p>
								{/if}
							</div>
						{/each}
					</div>
				</Card.Content>
			</Card.Root>

			<Card.Root>
				<Card.Header>
					<Card.Title>Wish list</Card.Title>
					<Card.Description>
						Designs you've kept across all iterations of this session. The domain criterion below is
						computed over exactly these.
					</Card.Description>
				</Card.Header>
				<Card.Content>
					<div class="overflow-x-auto">
						<Table.Root>
							<Table.Header>
								<Table.Row>
									<Table.Head>Solution</Table.Head>
									<Table.Head>Design ID</Table.Head>
									<Table.Head>First seen</Table.Head>
									<Table.Head>On wish list</Table.Head>
									<Table.Head></Table.Head>
								</Table.Row>
							</Table.Header>
							<Table.Body>
								{#each designs as d (d.solution.design_id)}
									<Table.Row>
										<Table.Cell>
											<span
												class="mr-1.5 inline-block h-3 w-3 rounded-full align-middle"
												style={`background-color:${designColor(d.solution.design_id)}`}
											></span>
											Solution {d.solution.solution_number}
										</Table.Cell>
										<Table.Cell>{d.solution.design_id}</Table.Cell>
										<Table.Cell>iteration {d.iteration}</Table.Cell>
										<Table.Cell>
											{#if wishList.includes(d.solution.design_id)}
												<Badge>yes</Badge>
											{:else}
												<span class="text-muted-foreground">—</span>
											{/if}
										</Table.Cell>
										<Table.Cell>
											{#if wishList.includes(d.solution.design_id)}
												<Button
													size="sm"
													variant="outline"
													onclick={() => handleWishlist(d.solution.design_id, false)}
												>
													Remove
												</Button>
											{:else}
												<Button size="sm" onclick={() => handleWishlist(d.solution.design_id, true)}>
													Add
												</Button>
											{/if}
										</Table.Cell>
									</Table.Row>
								{/each}
							</Table.Body>
						</Table.Root>
					</div>
				</Card.Content>
			</Card.Root>

			<Card.Root>
				<Card.Header>
					<Card.Title>Domain criterion</Card.Title>
					<Card.Description>
						For each wish-listed design, in how many of the {scenarios.length} scenarios it meets each
						objective's threshold. A design that hits its targets in 8 of 8 scenarios is robust in a
						sense the per-cell aspirations alone don't show. An objective left blank is excluded
						from the criterion rather than counted as passing.
					</Card.Description>
				</Card.Header>
				<Card.Content class="space-y-4">
					<div class="flex flex-wrap items-end gap-3">
						{#each objectives as obj (obj)}
							<div>
								<Label for={`thr-${obj}`} class="text-xs">{objectiveLabels[obj] ?? obj}</Label>
								<Input
									id={`thr-${obj}`}
									type="number"
									class="w-44"
									bind:value={domainThresholds[obj]}
									placeholder="no threshold"
								/>
							</div>
						{/each}
						<Button
							disabled={analysisLoading || wishList.length === 0 || thresholdedObjectives.length === 0}
							onclick={loadAnalysis}
						>
							{analysisLoading ? 'Computing…' : 'Compute domain criterion'}
						</Button>
					</div>

					{#if wishList.length === 0}
						<p class="text-muted-foreground text-xs">
							Add at least one design to the wish list first — the criterion is computed over the
							wish list.
						</p>
					{:else if thresholdedObjectives.length === 0}
						<p class="text-muted-foreground text-xs">
							Set a threshold for at least one objective.
						</p>
					{/if}

					{#if analysisError}
						<div class="rounded-md border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-800">
							{analysisError}
						</div>
					{/if}

					{#if analysis && analysis.domain_criterion.length > 0}
						<div class="overflow-x-auto">
							<Table.Root>
								<Table.Header>
									<Table.Row>
										<Table.Head>Design ID</Table.Head>
										{#each objectives as obj (obj)}
											<Table.Head>{objectiveLabels[obj] ?? obj}</Table.Head>
										{/each}
										<Table.Head>Mean</Table.Head>
									</Table.Row>
								</Table.Header>
								<Table.Body>
									{#each analysis.domain_criterion as row (row.design_id)}
										<Table.Row>
											<Table.Cell class="font-medium">{row.design_id}</Table.Cell>
											{#each objectives as obj (obj)}
												{@const v = row[obj]}
												<Table.Cell>
													{#if typeof v === 'number'}
														{v} / {analysis.scenario_count}
													{:else}
														<span class="text-muted-foreground text-xs">no threshold</span>
													{/if}
												</Table.Cell>
											{/each}
											<Table.Cell>{fmt(row.mean_domain_criterion)}</Table.Cell>
										</Table.Row>
									{/each}
								</Table.Body>
							</Table.Root>
						</div>

						{#if domainChartRows.length > 0 && domainDimensions.length > 0}
							<div>
								<p class="text-muted-foreground mb-2 text-xs">
									One line per wish-listed design. Every axis counts scenarios out of {analysis.scenario_count},
									so <strong>higher is more robust on every axis</strong> — unlike the trade-off view
									above, where each axis carries its objective's own units and direction. A line that
									stays high across all axes holds up everywhere; one that dips on a single axis tells
									you which objective is the weak point. Hover a line for its counts.
								</p>
								<div style="height: 380px;">
									<ParallelCoordinates
										data={domainChartRows}
										dimensions={domainDimensions}
										colorByIndex={domainColorByIndex}
										lineLabels={domainLineLabels}
									/>
								</div>
							</div>
						{/if}
					{:else if analysis}
						<p class="text-muted-foreground text-xs">
							Nothing to report — no wish-listed design had a feasible breakdown for the chosen
							thresholds.
						</p>
					{/if}
				</Card.Content>
			</Card.Root>
		{/if}
	{/if}
</div>
