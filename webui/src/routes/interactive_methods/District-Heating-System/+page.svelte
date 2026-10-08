<script lang="ts">
	/**
	 * JINA (interactive single-scenario) — generic, scenario-robust reference-point matching
	 * over a decision maker's pre-computed candidate pool.
	 *
	 * Unlike the sibling "JINA (interactive two-stage robustness)" method (which builds and solves a
	 * real DESDEO `Problem` live on every iteration), this method never solves anything — it
	 * scores a pre-computed pool of candidate designs (from `the_DM_session.ipynb`) against a
	 * reference point with every configured scalarizer and returns up to `max_solutions` new
	 * (never-before-shown) matched designs. Designs already shown in an earlier round are never
	 * matched again.
	 *
	 * All objective/strategic-variable/scalarizer labels come from the `meta` block the backend
	 * returns for the selected problem — nothing here is hard-coded to district heating.
	 */
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import * as Card from '$lib/components/ui/card';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Table from '$lib/components/ui/table';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Badge } from '$lib/components/ui/badge';
	import ParallelCoordinates from '$lib/components/visualizations/parallel-coordinates/parallel-coordinates.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import { create_session } from '../../methods/sessions/handler';
	import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';
	import {
		getAnalysis,
		getOrInitialize,
		getSessionTree,
		getStrategicDesigns,
		runIteration,
		wishlistAdd,
		wishlistRemove
	} from './handlers';
	import {
		SCALARIZER_PALETTE,
		SCENARIO_PALETTE,
		SOLUTION_COLORS,
		type AnalysisResult,
		type IterateState,
		type ObjectiveMeta,
		type SessionTreeEntry,
		type StrategicDesignsResult,
		type StrategicVarMeta
	} from './types';

	const { data } = $props<{ data: { problems: ProblemInfo[] } }>();
	let problem_list = $derived(data.problems ?? []);
	let problem = $state<ProblemInfo | null>(null);
	let problemId: number | null = $state(null);

	let sessionId: number | null = $state(null);
	let loading = $state(false);
	let errorText: string | null = $state(null);

	let current: IterateState | null = $state(null);

	// Everything below is driven off `current.meta`, fetched fresh from the backend for whichever
	// problem is selected — no objective/strategic-variable/scalarizer/scenario name is hard-coded.
	let OBJ_KEYS = $derived.by(() => current?.meta.objectives.map((o) => o.symbol) ?? []);
	let objMetaBySymbol = $derived.by(() => {
		const map: Record<string, ObjectiveMeta> = {};
		(current?.meta.objectives ?? []).forEach((o) => (map[o.symbol] = o));
		return map;
	});
	function objLabel(sym: string): string {
		return objMetaBySymbol[sym]?.label ?? sym;
	}
	function objDirection(sym: string): 'min' | 'max' {
		return objMetaBySymbol[sym]?.maximize ? 'max' : 'min';
	}
	function regretLabel(sym: string): string {
		return `${objLabel(sym)} regret`;
	}
	function domainLabel(sym: string): string {
		return `${objLabel(sym)} met`;
	}

	let STRAT_KEYS = $derived.by(() => current?.meta.strategic_vars.map((v) => v.symbol) ?? []);
	let strategicMetaBySymbol = $derived.by(() => {
		const map: Record<string, StrategicVarMeta> = {};
		(current?.meta.strategic_vars ?? []).forEach((v) => (map[v.symbol] = v));
		return map;
	});
	function stratLabel(sym: string): string {
		return strategicMetaBySymbol[sym]?.label ?? sym;
	}

	// Scalarizers are always emitted "aasf" (balanced) first, then one "generic_asf" emphasis
	// variant per objective, then GUESS/STOM — a position-indexed palette gives every problem
	// stable, distinct colors with zero per-problem configuration.
	let scalarizerColorByName = $derived.by(() => {
		const map: Record<string, string> = {};
		(current?.meta.scalarizers ?? []).forEach((s, i) => {
			map[s.name] = SCALARIZER_PALETTE[i % SCALARIZER_PALETTE.length];
		});
		return map;
	});
	let scalarizerLabelByName = $derived.by(() => {
		const map: Record<string, string> = {};
		(current?.meta.scalarizers ?? []).forEach((s) => (map[s.name] = s.label));
		return map;
	});

	// Strategic Design Explorer colors designs by which scenario they were originally optimized
	// for — same position-indexed-palette approach as scalarizers, keyed by scenario order.
	let scenarioColorByName = $derived.by(() => {
		const map: Record<string, string> = {};
		(current?.meta.all_scenarios ?? []).forEach((s, i) => {
			map[s] = SCENARIO_PALETTE[i % SCENARIO_PALETTE.length];
		});
		return map;
	});

	let scenarioCount = $derived.by(() => current?.all_scenarios.length ?? 8);

	// Iteration history (back/forward navigation) — sessionTree holds every iterate/wishlist_update
	// state for the session, oldest first; viewedIterationIndex picks which "iterate" entry the
	// Matched solutions / Trade-off view cards display. Wish list, global ideal/nadir, and
	// already_shown_ids always come from `current` (the latest state) regardless of what's viewed.
	let sessionTree: SessionTreeEntry[] = $state([]);
	let viewedIterationIndex = $state(-1);

	let iterateEntries = $derived.by(() => sessionTree.filter((e) => e.kind === 'iterate'));
	let viewedEntry = $derived.by(() => {
		const entries = iterateEntries;
		return entries[viewedIterationIndex] ?? null;
	});

	async function loadSessionTree() {
		if (problemId === null) return;
		try {
			sessionTree = await getSessionTree(problemId, sessionId);
			const n = sessionTree.filter((e) => e.kind === 'iterate').length;
			viewedIterationIndex = n - 1;
		} catch {
			// Non-fatal: iteration history is a convenience; the current state still loaded fine.
		}
	}

	function goToPreviousIteration() {
		if (viewedIterationIndex > 0) viewedIterationIndex -= 1;
	}

	function goToNextIteration() {
		if (viewedIterationIndex < iterateEntries.length - 1) viewedIterationIndex += 1;
	}

	// Reference point input
	let mode: 'percent' | 'raw' = $state('percent');
	let percentValues: Record<string, number> = $state({});
	let rawValues: Record<string, number> = $state({});
	let note = $state('');
	let maxSolutions = $state(6);
	let rawValuesSeeded = false;

	function referencePointFromInputs(): Record<string, number> {
		if (mode === 'raw') {
			return { ...rawValues };
		}
		if (!current) return { ...percentValues };
		const out: Record<string, number> = {};
		for (const obj of OBJ_KEYS) {
			const frac = Math.max(0, Math.min(100, percentValues[obj] ?? 50)) / 100;
			out[obj] = current.global_nadir[obj] + frac * (current.global_ideal[obj] - current.global_nadir[obj]);
		}
		return out;
	}

	// --- Strategic Design Explorer (Vis_strategic_decisions.ipynb equivalent) ---
	// Browses the whole candidate pool — unlike the sibling Robust method's version, this isn't
	// session-scoped (the pool is precomputed once, not discovered incrementally), so it's loaded
	// once and never needs refreshing after an iteration.
	let strategicDesigns: StrategicDesignsResult | null = $state(null);
	let strategicLoading = $state(false);
	let strategicError: string | null = $state(null);
	let selectedDesignId: number | null = $state(null);

	async function loadStrategicDesigns() {
		if (problemId === null) return;
		strategicLoading = true;
		strategicError = null;
		try {
			strategicDesigns = await getStrategicDesigns(problemId);
			const ids = strategicDesigns.designs.map((d) => d.design_id);
			if (selectedDesignId === null || !ids.includes(selectedDesignId)) {
				selectedDesignId = ids.length > 0 ? ids[0] : null;
			}
		} catch (e) {
			strategicDesigns = null;
			strategicError = e instanceof Error ? e.message : 'Failed to load strategic designs.';
		} finally {
			strategicLoading = false;
		}
	}

	async function loadState() {
		if (problemId === null) return;
		loading = true;
		errorText = null;
		try {
			current = await getOrInitialize(problemId, sessionId);
			const objSymbols = current.meta.objectives.map((o) => o.symbol);
			for (const obj of objSymbols) {
				if (percentValues[obj] === undefined) percentValues[obj] = 50;
				if (rawValues[obj] === undefined) rawValues[obj] = 0;
			}
			if (!thresholdsSeeded) {
				domainThresholds = { ...current.meta.default_domain_thresholds };
				thresholdsSeeded = true;
			}
			if (current.state_id !== 0 && !rawValuesSeeded && current.reference_point) {
				for (const obj of objSymbols) {
					if (current.reference_point[obj] !== undefined) rawValues[obj] = current.reference_point[obj];
				}
				rawValuesSeeded = true;
			}
			await loadSessionTree();
			await loadStrategicDesigns();
		} catch (e) {
			errorText = e instanceof Error ? e.message : 'Failed to load state.';
		} finally {
			loading = false;
		}
	}

	async function handleIterate() {
		if (problemId === null) return;
		loading = true;
		errorText = null;
		try {
			current = await runIteration({
				problem_id: problemId,
				session_id: sessionId,
				reference_point: referencePointFromInputs(),
				max_solutions: maxSolutions,
				note: note || null
			});
			await loadSessionTree();
		} catch (e) {
			errorText = e instanceof Error ? e.message : 'Failed to run the iteration.';
		} finally {
			loading = false;
		}
	}

	async function handleAddToWishlist(designId: number) {
		if (problemId === null) return;
		loading = true;
		errorText = null;
		try {
			const res = await wishlistAdd({ problem_id: problemId, session_id: sessionId, design_ids: [designId] });
			if (current) current = { ...current, wish_list: res.wish_list };
		} catch (e) {
			errorText = e instanceof Error ? e.message : 'Failed to add to the wish list.';
		} finally {
			loading = false;
		}
	}

	async function handleRemoveFromWishlist(designId: number) {
		if (problemId === null) return;
		loading = true;
		errorText = null;
		try {
			const res = await wishlistRemove({ problem_id: problemId, session_id: sessionId, design_ids: [designId] });
			if (current) current = { ...current, wish_list: res.wish_list };
		} catch (e) {
			errorText = e instanceof Error ? e.message : 'Failed to remove from the wish list.';
		} finally {
			loading = false;
		}
	}

	// --- Trade-off chart derivation: one row per (solution, scenario), colored per solution ---
	// Sourced from `viewedEntry` (the iteration currently being browsed), not always the latest.
	let chartRows = $derived.by(() => {
		const entry = viewedEntry;
		const keys = OBJ_KEYS;
		if (!entry?.solutions) return [];
		return entry.solutions.flatMap((sol) =>
			sol.rows.map((row) => {
				const out: Record<string, number> = {};
				for (const obj of keys) out[obj] = Number(row[obj]);
				return out;
			})
		);
	});

	let chartColorByIndex = $derived.by(() => {
		const entry = viewedEntry;
		const map: Record<string, string> = {};
		let i = 0;
		(entry?.solutions ?? []).forEach((sol, solIdx) => {
			const color = SOLUTION_COLORS[solIdx % SOLUTION_COLORS.length];
			sol.rows.forEach(() => {
				map[String(i)] = color;
				i += 1;
			});
		});
		return map;
	});

	let chartLineLabels = $derived.by(() => {
		const entry = viewedEntry;
		const map: Record<string, string> = {};
		let i = 0;
		(entry?.solutions ?? []).forEach((sol) => {
			sol.rows.forEach((row) => {
				map[String(i)] =
					`Solution ${sol.solution_number} (design ${sol.design_id}) — ${row.target_operation_scenario}`;
				i += 1;
			});
		});
		return map;
	});

	let chartDimensions = $derived(
		OBJ_KEYS.map((obj) => ({
			symbol: obj,
			name: objLabel(obj),
			min: current ? Math.min(current.global_ideal[obj], current.global_nadir[obj]) : undefined,
			max: current ? Math.max(current.global_ideal[obj], current.global_nadir[obj]) : undefined,
			direction: objDirection(obj)
		}))
	);

	let chartReferenceData = $derived.by(() => {
		const entry = viewedEntry;
		if (!entry?.reference_point || Object.keys(entry.reference_point).length === 0) return undefined;
		return { referencePoint: { values: entry.reference_point, label: 'Reference point' } };
	});

	function solutionColor(index: number): string {
		return SOLUTION_COLORS[index % SOLUTION_COLORS.length];
	}

	function fmt(v: number): string {
		return v.toLocaleString(undefined, { maximumFractionDigits: 1 });
	}

	// --- Strategic Design Explorer chart + detail derivation ---
	let strategicChartRows = $derived.by(() => {
		const sd = strategicDesigns;
		if (!sd) return [];
		const keys = STRAT_KEYS;
		return sd.designs.map((d) => ({
			design_id: d.design_id,
			...Object.fromEntries(keys.map((sym) => [sym, d.strategic_vals[sym]]))
		}));
	});

	let strategicColorByIndex = $derived.by(() => {
		const sd = strategicDesigns;
		const colors = scenarioColorByName;
		const map: Record<string, string> = {};
		(sd?.designs ?? []).forEach((d, i) => {
			map[String(i)] = colors[d.source_design_scenario] ?? SOLUTION_COLORS[i % SOLUTION_COLORS.length];
		});
		return map;
	});

	let strategicChartDimensions = $derived.by(() => {
		const sd = strategicDesigns;
		const ids = (sd?.designs ?? []).map((d) => d.design_id);
		const idMin = ids.length > 0 ? Math.min(...ids) : 0;
		const idMax = ids.length > 0 ? Math.max(...ids) : 1;
		return [
			{ symbol: 'design_id', name: 'Design ID', min: idMin, max: idMax },
			...STRAT_KEYS.map((sym) => ({
				symbol: sym,
				name: stratLabel(sym),
				min: 0,
				max: sd?.axis_max[sym] ?? 1
			}))
		];
	});

	let sourceScenariosPresent = $derived.by(() => {
		const sd = strategicDesigns;
		return [...new Set((sd?.designs ?? []).map((d) => d.source_design_scenario))].sort();
	});

	let selectedDesign = $derived.by(() => {
		const sd = strategicDesigns;
		const id = selectedDesignId;
		if (!sd || id === null) return null;
		return sd.designs.find((d) => d.design_id === id) ?? null;
	});

	let selectedCapacityRows = $derived.by(() => {
		const sd = strategicDesigns;
		const design = selectedDesign;
		if (!sd || !design) return [];
		const metaMap = strategicMetaBySymbol;
		return STRAT_KEYS.map((sym) => {
			const existing = sd.axis_max[sym] ?? 0;
			const added = design.strategic_vals[sym] ?? 0;
			const total = existing + added;
			const changePct = existing !== 0 ? (100 * added) / existing : null;
			const m = metaMap[sym];
			return { sym, component: m?.component ?? sym, unit: m?.unit ?? '', existing, added, total, changePct };
		});
	});

	let selectedBreakdownRows = $derived.by(() => {
		const design = selectedDesign;
		const cur = current;
		if (!design) return [];
		const order = cur?.all_scenarios ?? [];
		const rows = [...design.breakdown];
		if (order.length > 0) {
			rows.sort((a, b) => order.indexOf(String(a.scenario)) - order.indexOf(String(b.scenario)));
		}
		return rows;
	});

	// --- Robustness analysis (stage_2c_analysis.ipynb equivalent, minus the antifragility
	// section, which this page doesn't display — same as the sibling Robust method) ---
	let analysis: AnalysisResult | null = $state(null);
	let analysisLoading = $state(false);
	let analysisError: string | null = $state(null);
	let domainThresholds: Record<string, number> = $state({});
	let thresholdsSeeded = false;

	function designColor(designId: number, ids: number[]): string {
		const idx = ids.indexOf(designId);
		return SOLUTION_COLORS[idx % SOLUTION_COLORS.length];
	}

	async function handleAnalyze() {
		if (problemId === null) return;
		analysisLoading = true;
		analysisError = null;
		try {
			analysis = await getAnalysis({
				problem_id: problemId,
				session_id: sessionId,
				domain_thresholds: { ...domainThresholds },
				// The backend still computes antifragility metrics as part of the same analysis
				// call (this page just doesn't render them), so the per-problem default floor is
				// enough.
				af_absolute_floors: { ...(current?.meta.default_af_absolute_floors ?? {}) }
			});
		} catch (e) {
			analysisError = e instanceof Error ? e.message : 'Failed to run the analysis.';
		} finally {
			analysisLoading = false;
		}
	}

	let regretIds = $derived.by(() => {
		const a = analysis;
		return (a?.max_regret ?? []).map((r) => r.design_id);
	});
	let regretChartRows = $derived.by(() => {
		const a = analysis;
		const keys = OBJ_KEYS;
		return (a?.max_regret ?? []).map((r) => {
			const out: Record<string, number> = { mean_normalized_regret: r.mean_normalized_regret };
			for (const obj of keys) out[obj] = Number(r[obj]);
			return out;
		});
	});
	let regretDimensions = $derived(
		OBJ_KEYS.map((obj) => ({ symbol: obj, name: regretLabel(obj), min: 0, max: 1, direction: 'min' as const }))
	);
	let regretColorByIndex = $derived.by(() => {
		const ids = regretIds;
		const map: Record<string, string> = {};
		ids.forEach((id, i) => (map[String(i)] = designColor(id, ids)));
		return map;
	});

	let domainIds = $derived.by(() => {
		const a = analysis;
		return (a?.domain_criterion ?? []).map((r) => r.design_id);
	});
	let domainChartRows = $derived.by(() => {
		const a = analysis;
		const keys = OBJ_KEYS;
		return (a?.domain_criterion ?? []).map((r) => {
			const out: Record<string, number> = { mean_domain_criterion: r.mean_domain_criterion };
			for (const obj of keys) out[obj] = Number(r[obj]);
			return out;
		});
	});
	let domainDimensions = $derived(
		OBJ_KEYS.map((obj) => ({
			symbol: obj,
			name: domainLabel(obj),
			min: 0,
			max: scenarioCount,
			direction: 'max' as const
		}))
	);
	let domainColorByIndex = $derived.by(() => {
		const ids = domainIds;
		const map: Record<string, string> = {};
		ids.forEach((id, i) => (map[String(i)] = designColor(id, ids)));
		return map;
	});

	// Starts a brand-new interactive session (shared with the sibling Robust method, since both
	// key their state off the same session id) and reloads this page against it — nothing from
	// the old session is deleted, it's just no longer selected; the DM can still get back to it
	// from /methods/sessions.
	async function handleNewSession() {
		if (problemId === null) return;
		loading = true;
		errorText = null;
		try {
			const created = await create_session(null);
			if (!created || created.id === null) throw new Error('Failed to create a new session.');
			methodSelection.setSession(created.id, created.info ?? null);
			sessionId = created.id;
			current = null;
			sessionTree = [];
			viewedIterationIndex = -1;
			analysis = null;
			rawValuesSeeded = false;
			await loadState();
		} catch (e) {
			errorText = e instanceof Error ? e.message : 'Failed to start a new session.';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		sessionId = $methodSelection.selectedSessionId;
		problemId = $methodSelection.selectedProblemId;
		if (problemId !== null) {
			problem = problem_list.find((p: ProblemInfo) => String(p.id) === String(problemId)) ?? null;
			loadState();
		}
	});
</script>

<svelte:head>
	<title>JINA (interactive single-scenario) | DESDEO</title>
	<meta
		name="description"
		content="Scenario-robust reference-point matching over any problem's pre-computed candidate pool."
	/>
</svelte:head>

<div class="container mx-auto max-w-6xl space-y-6 px-4 py-8">
	<div class="flex items-start justify-between gap-4">
		<div>
			<h1 class="text-3xl font-bold tracking-tight">JINA (interactive single-scenario)</h1>
			<p class="text-muted-foreground mt-1 text-sm italic">
				JINA: Joint Infrastructure Network Adaptation
			</p>
			<p class="text-muted-foreground mt-1">
				Set a reference point below to find new candidate designs matched across
				{scenarioCount} disruption scenarios. Designs already shown in an earlier round are never
				matched again.
			</p>
			{#if problem}
				<p class="text-muted-foreground mt-2 text-sm">
					Problem: <strong>{problem.name}</strong>
					<a href="/methods/initialize" class="ml-2 underline">Change</a>
				</p>
			{/if}
		</div>
		{#if problemId !== null}
			<Button variant="outline" size="sm" disabled={loading} onclick={handleNewSession} class="shrink-0">
				New session
			</Button>
		{/if}
	</div>

	{#if problemId === null}
		<Card.Root>
			<Card.Header>
				<Card.Title>Select a problem first</Card.Title>
				<Card.Description>
					This method needs a DESDEO problem with an attached candidate-pool. Pick one from the
					methods page before starting a session here.
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

		{#if current}
			<Card.Root>
				<Card.Header>
					<Card.Title>Set reference point</Card.Title>
					<Card.Description>
						One aspiration value per objective. Use percent-of-range for a quick start, or raw
						values once you know the numbers you want.
					</Card.Description>
				</Card.Header>
				<Card.Content>
					<Tabs.Root value={mode} onValueChange={(v) => (mode = v as 'percent' | 'raw')}>
						<Tabs.List>
							<Tabs.Trigger value="percent">Percent of range</Tabs.Trigger>
							<Tabs.Trigger value="raw">Raw values</Tabs.Trigger>
						</Tabs.List>

						<Tabs.Content value="percent" class="mt-4">
							<div class="grid grid-cols-2 gap-4 md:grid-cols-4">
								{#each OBJ_KEYS as obj}
									<div>
										<Label for={`pct-${obj}`}>{objLabel(obj)}</Label>
										<Input
											id={`pct-${obj}`}
											type="number"
											min="0"
											max="100"
											bind:value={percentValues[obj]}
										/>
										<p class="text-muted-foreground mt-1 text-xs">
											100 = ideal ({fmt(current.global_ideal[obj])}), 0 = nadir ({fmt(
												current.global_nadir[obj]
											)})
										</p>
									</div>
								{/each}
							</div>
						</Tabs.Content>

						<Tabs.Content value="raw" class="mt-4">
							<div class="grid grid-cols-2 gap-4 md:grid-cols-4">
								{#each OBJ_KEYS as obj}
									<div>
										<Label for={`raw-${obj}`}>{objLabel(obj)}</Label>
										<Input id={`raw-${obj}`} type="number" bind:value={rawValues[obj]} />
									</div>
								{/each}
							</div>
						</Tabs.Content>
					</Tabs.Root>

					<div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
						<div>
							<Label for="max-solutions">Max solutions this round</Label>
							<Input
								id="max-solutions"
								type="number"
								min="1"
								max={current.meta.scalarizers.length}
								bind:value={maxSolutions}
							/>
						</div>
						<div class="md:col-span-2">
							<Label for="note">Note (optional)</Label>
							<Input id="note" type="text" bind:value={note} placeholder="e.g. iteration 2" />
						</div>
					</div>

					<Button class="mt-4" disabled={loading} onclick={handleIterate}>
						{loading ? 'Running…' : 'Run iteration'}
					</Button>
				</Card.Content>
			</Card.Root>
		{:else}
			<Card.Root>
				<Card.Content class="text-muted-foreground py-6 text-sm">
					{loading ? 'Loading the candidate pool for this problem…' : 'No data yet.'}
				</Card.Content>
			</Card.Root>
		{/if}

		{#if current && viewedEntry?.solutions && viewedEntry.solutions.length > 0}
			<Card.Root>
				<Card.Header>
					<Card.Title>Matched solutions</Card.Title>
					<Card.Description>
						{viewedEntry.solutions.length} distinct design(s) matched this round, from
						{current.meta.scalarizers.length} scalarizers.
						{current.already_shown_ids.length} design(s) shown across the whole session so far.
					</Card.Description>
				</Card.Header>
				<Card.Content>
					<div class="mb-4 flex items-center gap-2">
						<Button size="sm" variant="outline" disabled={viewedIterationIndex <= 0} onclick={goToPreviousIteration}>
							◀ Previous
						</Button>
						<span class="text-sm">
							Iteration {viewedIterationIndex + 1} of {iterateEntries.length}
							{#if viewedEntry?.note}
								— "{viewedEntry.note}"
							{/if}
						</span>
						<Button
							size="sm"
							variant="outline"
							disabled={viewedIterationIndex >= iterateEntries.length - 1}
							onclick={goToNextIteration}
						>
							Next ▶
						</Button>
					</div>
					<div class="overflow-x-auto">
					<Table.Root>
						<Table.Header>
							<Table.Row>
								<Table.Head>Solution</Table.Head>
								<Table.Head>Design ID</Table.Head>
								<Table.Head>Matched by</Table.Head>
								{#each OBJ_KEYS as obj}
									<Table.Head>{objLabel(obj)} (best–worst)</Table.Head>
								{/each}
								<Table.Head></Table.Head>
							</Table.Row>
						</Table.Header>
						<Table.Body>
							{#each viewedEntry.solutions as sol, i (sol.design_id)}
								<Table.Row>
									<Table.Cell>
										<span
											class="inline-block h-3 w-3 rounded-full align-middle"
											style={`background-color:${solutionColor(i)}`}
										></span>
										Solution {sol.solution_number}
									</Table.Cell>
									<Table.Cell>{sol.design_id}</Table.Cell>
									<Table.Cell>
										<div class="flex flex-wrap gap-1">
											{#each sol.matched_by as name}
												<Badge variant="secondary">{scalarizerLabelByName[name] ?? name}</Badge>
											{/each}
										</div>
									</Table.Cell>
									{#each OBJ_KEYS as obj}
										<Table.Cell>{fmt(sol.best_case[obj])} – {fmt(sol.worst_case[obj])}</Table.Cell>
									{/each}
									<Table.Cell>
										{#if current.wish_list.includes(sol.design_id)}
											<Button
												size="sm"
												variant="outline"
												disabled={loading}
												onclick={() => handleRemoveFromWishlist(sol.design_id)}
											>
												Remove from wish list
											</Button>
										{:else}
											<Button size="sm" disabled={loading} onclick={() => handleAddToWishlist(sol.design_id)}>
												Add to wish list
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
					<Card.Title>Trade-off view</Card.Title>
					<Card.Description>
						Each line is one (solution, scenario) pair — up to {scenarioCount} lines per matched
						design, showing its full performance envelope across all disruption scenarios. Lines
						sharing a color belong to the same solution.
					</Card.Description>
				</Card.Header>
				<Card.Content>
					<div style="height: 420px;">
						<ParallelCoordinates
							data={chartRows}
							dimensions={chartDimensions}
							referenceData={chartReferenceData}
							colorByIndex={chartColorByIndex}
							lineLabels={chartLineLabels}
						/>
					</div>
				</Card.Content>
			</Card.Root>
		{/if}

		{#if strategicDesigns && strategicDesigns.designs.length > 0}
			<Card.Root>
				<Card.Header>
					<Card.Title>Strategic Design Explorer</Card.Title>
					<Card.Description>
						Browse every design in the candidate pool ({strategicDesigns.designs.length}) —
						first-stage capacities and full performance across scenarios. Lines are colored by which
						scenario that design was originally optimized for. Drag on the Design ID axis to narrow
						the range.
					</Card.Description>
				</Card.Header>
				<Card.Content class="space-y-4">
					<div class="flex flex-wrap gap-3 text-xs">
						{#each sourceScenariosPresent as sc}
							<span class="flex items-center gap-1.5">
								<span
									class="inline-block h-3 w-3 rounded-full"
									style={`background-color:${scenarioColorByName[sc] ?? '#888'}`}
								></span>
								{sc}
							</span>
						{/each}
					</div>
					<div style="height: 420px;">
						<ParallelCoordinates
							data={strategicChartRows}
							dimensions={strategicChartDimensions}
							colorByIndex={strategicColorByIndex}
						/>
					</div>

					<div class="border-t pt-4">
						<Label for="design-id-select">Design ID</Label>
						<select
							id="design-id-select"
							class="border-input mt-1 block w-40 rounded-md border bg-transparent px-3 py-1.5 text-sm shadow-xs"
							bind:value={selectedDesignId}
						>
							{#each strategicDesigns.designs as d}
								<option value={d.design_id}>Design {d.design_id}</option>
							{/each}
						</select>

						{#if selectedDesign}
							<p class="text-muted-foreground mt-2 text-xs">
								Source: <strong>{selectedDesign.source_design_scenario}</strong> · Ref ID {selectedDesign.reference_id}
								· <strong>{scalarizerLabelByName[selectedDesign.scalarizer] ?? selectedDesign.scalarizer}</strong>
							</p>

							<div class="mt-4 overflow-x-auto">
								<p class="mb-2 text-sm font-medium">Capacities and changes relative to the existing system</p>
								<Table.Root>
									<Table.Header>
										<Table.Row>
											<Table.Head>Component</Table.Head>
											<Table.Head>Unit</Table.Head>
											<Table.Head>Existing capacity</Table.Head>
											<Table.Head>New capacity added</Table.Head>
											<Table.Head>Total capacity</Table.Head>
											<Table.Head>Change from existing</Table.Head>
										</Table.Row>
									</Table.Header>
									<Table.Body>
										{#each selectedCapacityRows as row}
											<Table.Row>
												<Table.Cell>{row.component}</Table.Cell>
												<Table.Cell>{row.unit}</Table.Cell>
												<Table.Cell>{fmt(row.existing)}</Table.Cell>
												<Table.Cell>{fmt(row.added)}</Table.Cell>
												<Table.Cell>{fmt(row.total)}</Table.Cell>
												<Table.Cell>
													{row.changePct === null ? '—' : `${row.changePct >= 0 ? '+' : ''}${row.changePct.toFixed(1)}%`}
												</Table.Cell>
											</Table.Row>
										{/each}
									</Table.Body>
								</Table.Root>
							</div>

							<div class="mt-4 overflow-x-auto">
								<p class="mb-2 text-sm font-medium">Performance across all scenarios</p>
								<Table.Root>
									<Table.Header>
										<Table.Row>
											<Table.Head>Scenario</Table.Head>
											{#each OBJ_KEYS as obj}
												<Table.Head>{objLabel(obj)}</Table.Head>
											{/each}
										</Table.Row>
									</Table.Header>
									<Table.Body>
										{#each selectedBreakdownRows as row}
											<Table.Row>
												<Table.Cell>{row.scenario}</Table.Cell>
												{#each OBJ_KEYS as obj}
													<Table.Cell>{fmt(Number(row[obj]))}</Table.Cell>
												{/each}
											</Table.Row>
										{/each}
									</Table.Body>
								</Table.Root>
							</div>
						{/if}
					</div>
				</Card.Content>
			</Card.Root>
		{:else if strategicLoading}
			<Card.Root>
				<Card.Content class="py-6 text-sm text-muted-foreground">Loading strategic designs…</Card.Content>
			</Card.Root>
		{:else if strategicError}
			<div class="rounded-md border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-800">
				{strategicError}
			</div>
		{/if}

		<Card.Root>
			<Card.Header>
				<Card.Title>Wish list</Card.Title>
				<Card.Description>
					Designs you've selected across all iterations of this session.
				</Card.Description>
			</Card.Header>
			<Card.Content>
				{#if current && current.wish_list.length > 0}
					<div class="flex flex-wrap gap-2">
						{#each current.wish_list as designId}
							<Badge variant="outline" class="flex items-center gap-2 py-1.5">
								Design {designId}
								<button
									class="text-muted-foreground hover:text-foreground"
									disabled={loading}
									onclick={() => handleRemoveFromWishlist(designId)}
									aria-label={`Remove design ${designId} from wish list`}
								>
									×
								</button>
							</Badge>
						{/each}
					</div>
					<div class="mt-6">
						<p class="text-sm font-medium">Robustness thresholds</p>
						<p class="text-muted-foreground mb-3 text-xs">
							Set these to match your own robustness criteria before analyzing, they are not
							derived from the data. Domain criterion counts a design as meeting the threshold in a
							scenario when its objective value is at or better than this.
						</p>
						<div class="grid grid-cols-2 gap-4 md:grid-cols-4">
							{#each OBJ_KEYS as obj}
								<div>
									<Label for={`domain-thr-${obj}`}>{objLabel(obj)} - domain threshold</Label>
									<Input id={`domain-thr-${obj}`} type="number" bind:value={domainThresholds[obj]} />
								</div>
							{/each}
						</div>
					</div>

					<Button class="mt-4" disabled={analysisLoading} onclick={handleAnalyze}>
						{analysisLoading ? 'Analyzing…' : 'Analyze wish list'}
					</Button>
				{:else}
					<p class="text-muted-foreground text-sm">
						No designs wish-listed yet. Run an iteration and add designs you like above.
					</p>
				{/if}
			</Card.Content>
		</Card.Root>

		{#if analysisError}
			<div class="rounded-md border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-800">
				{analysisError}
			</div>
		{/if}

		{#if analysis}
			<Card.Root>
				<Card.Header>
					<Card.Title>Max regret</Card.Title>
					<Card.Description>
						Computed across the full candidate pool, shown for wish-listed designs only. 0 = this
						design was the best achiever in that scenario/objective; 1 = the worst. Lower is more
						robust.
					</Card.Description>
				</Card.Header>
				<Card.Content class="space-y-4">
					<div class="overflow-x-auto">
						<Table.Root>
							<Table.Header>
								<Table.Row>
									<Table.Head>Design</Table.Head>
									{#each OBJ_KEYS as obj}
										<Table.Head>{regretLabel(obj)}</Table.Head>
									{/each}
									<Table.Head>Mean regret</Table.Head>
								</Table.Row>
							</Table.Header>
							<Table.Body>
								{#each analysis.max_regret as row (row.design_id)}
									<Table.Row>
										<Table.Cell>
											<span
												class="inline-block h-3 w-3 rounded-full align-middle"
												style={`background-color:${designColor(row.design_id, regretIds)}`}
											></span>
											Design {row.design_id}
										</Table.Cell>
										{#each OBJ_KEYS as obj}
											<Table.Cell>{Number(row[obj]).toFixed(3)}</Table.Cell>
										{/each}
										<Table.Cell>{row.mean_normalized_regret.toFixed(3)}</Table.Cell>
									</Table.Row>
								{/each}
							</Table.Body>
						</Table.Root>
					</div>
					<div style="height: 380px;">
						<ParallelCoordinates
							data={regretChartRows}
							dimensions={regretDimensions}
							colorByIndex={regretColorByIndex}
						/>
					</div>
				</Card.Content>
			</Card.Root>

			<Card.Root>
				<Card.Header>
					<Card.Title>Domain criterion</Card.Title>
					<Card.Description>
						Count of scenarios (out of {scenarioCount}) in which each wish-listed design meets its
						domain-criterion threshold. Higher is more robust.
					</Card.Description>
				</Card.Header>
				<Card.Content class="space-y-4">
					<div class="overflow-x-auto">
						<Table.Root>
							<Table.Header>
								<Table.Row>
									<Table.Head>Design</Table.Head>
									{#each OBJ_KEYS as obj}
										<Table.Head>{domainLabel(obj)}</Table.Head>
									{/each}
									<Table.Head>Mean</Table.Head>
								</Table.Row>
							</Table.Header>
							<Table.Body>
								{#each analysis.domain_criterion as row (row.design_id)}
									<Table.Row>
										<Table.Cell>
											<span
												class="inline-block h-3 w-3 rounded-full align-middle"
												style={`background-color:${designColor(row.design_id, domainIds)}`}
											></span>
											Design {row.design_id}
										</Table.Cell>
										{#each OBJ_KEYS as obj}
											<Table.Cell>{row[obj]} / {scenarioCount}</Table.Cell>
										{/each}
										<Table.Cell>{row.mean_domain_criterion.toFixed(2)}</Table.Cell>
									</Table.Row>
								{/each}
							</Table.Body>
						</Table.Root>
					</div>
					<div style="height: 380px;">
						<ParallelCoordinates
							data={domainChartRows}
							dimensions={domainDimensions}
							colorByIndex={domainColorByIndex}
						/>
					</div>
				</Card.Content>
			</Card.Root>
		{/if}
	{/if}
</div>
