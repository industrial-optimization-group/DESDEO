<script lang="ts">
	/**
	 * JINA (interactive two-stage robustness) — generic, live-solving reference-point matching against
	 * any problem that has an attached scenario model.
	 *
	 * Unlike the sibling "JINA (interactive single-scenario)" method (which matches against a
	 * pre-computed candidate pool, never solving anything), this method builds a real DESDEO
	 * `Problem`, combines it across every scenario into one worst-case robust problem, and solves
	 * it live with Gurobi on every iteration — one ASF scalarizer variant per objective plus a
	 * balanced one, deduplicated by first-stage design. Because every round re-solves live (there's
	 * no fixed pool to remove already-shown rows from), a design can resurface in a later
	 * iteration — it's flagged as a repeat rather than excluded. Each iteration takes real time
	 * (order of a minute), so the loading state below says so explicitly.
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
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors';
	import { methodSelection } from '../../../stores/methodSelection';
	import { create_session } from '../../methods/sessions/handler';
	import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';
	import {
		getAnalysis,
		getCombinedScenarioAnalysis,
		getOrInitialize,
		getSessionTree,
		getStrategicDesigns,
		runIteration,
		wishlistAdd,
		wishlistRemove
	} from './handlers';
	import {
		SCALARIZER_PALETTE,
		SOLUTION_COLORS,
		type AnalysisResult,
		type CombinedScenarioResult,
		type IterateState,
		type ObjectiveMeta,
		type SessionTreeEntry,
		type StrategicDesign,
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
	// problem is selected — no objective/strategic-variable/scalarizer name is hard-coded.
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

	// Short names for parallel-coordinates axes. An axis gets one narrow column of room, so the
	// full metadata label ("Operational Cost (EUR)") either overlaps its neighbours or has to be
	// dropped altogether — every plot on this page ran into that. Tables, legends and form fields
	// keep `objLabel` and stay fully spelled out; only chart axes use these.
	//
	// Keyed on the objective's metadata *name* rather than its symbol: another problem is free to
	// reuse a symbol like "obj1" for something unrelated, and matching on the name means it can't
	// inherit the wrong short label. Anything unlisted falls back to the full label, so this stays
	// an override rather than something a problem has to supply.
	const SHORT_AXIS_LABELS: Record<string, string> = {
		'Operational Cost': 'Net op cost',
		'Investment Cost': 'Inv cost',
		'CO2 Emissions': 'CO2',
		'Unmet Heat': 'Unmet'
	};

	function objShortLabel(sym: string): string {
		const metaName = objMetaBySymbol[sym]?.name;
		return (metaName ? SHORT_AXIS_LABELS[metaName] : undefined) ?? objLabel(sym);
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

	// Scalarizers are always emitted "balanced" first, then one "emphasize" variant per objective
	// in objective order, so a position-indexed palette gives every problem stable, distinct colors.
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

	// Iteration history (back/forward navigation) — sessionTree holds every iterate/wishlist_update
	// state for the session, oldest first; viewedIterationIndex picks which "iterate" entry the
	// Matched solutions / Trade-off view cards display. Wish list, global ideal/nadir always come
	// from `current` (the latest state) regardless of what's viewed.
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
	let mode: 'percent' | 'raw' | 'delta' = $state('percent');
	let percentValues: Record<string, number> = $state({});
	let rawValues: Record<string, number> = $state({});
	// Third mode: how far to move each objective's aspiration *relative to the previous
	// iteration*, in percentage points of the same 0 = nadir … 100 = ideal scale the percent mode
	// uses. +10 means "ten points closer to the ideal than last round", -5 the reverse. A DM
	// steering a search usually knows "a bit more of this, less of that" well before they know the
	// number they actually want, and this is the only mode anchored on the last round rather than
	// on the range as a whole.
	let deltaValues: Record<string, number> = $state({});
	let note = $state('');
	// Caps how many distinct designs are shown/highlighted this round — every scalarizer variant
	// still solves live regardless, so this doesn't change iteration time; it only trims what's
	// displayed (every discovered design still lands in the Strategic Design Explorer either
	// way). Defaults to showing all of them; re-seeded once meta.scalarizers.length is known.
	let maxSolutions: number = $state(0);
	let maxSolutionsSeeded = false;
	let rawValuesSeeded = false;

	// Where a raw objective value sits on the 0 = nadir … 100 = ideal scale. Null when it can't be
	// placed: no value, or a degenerate range where ideal and nadir coincide.
	function percentOfRange(obj: string, value: number | undefined): number | null {
		if (value === undefined || !current) return null;
		const nadir = current.global_nadir[obj];
		const ideal = current.global_ideal[obj];
		if (nadir === undefined || ideal === undefined || ideal === nadir) return null;
		return (100 * (value - nadir)) / (ideal - nadir);
	}

	function rawFromPercent(obj: string, pct: number): number {
		if (!current) return 0;
		const nadir = current.global_nadir[obj];
		const ideal = current.global_ideal[obj];
		return nadir + (Math.max(0, Math.min(100, pct)) / 100) * (ideal - nadir);
	}

	// Anchor for the change mode: the reference point of the most recent iteration, as a position
	// on the range. Before the first iteration there is nothing to move relative to, so changes
	// apply from the midpoint instead — stated in the UI rather than left to be inferred.
	const DELTA_FALLBACK_BASE = 50;

	let previousPercent = $derived.by(() => {
		const out: Record<string, number | null> = {};
		for (const obj of OBJ_KEYS) out[obj] = percentOfRange(obj, current?.reference_point?.[obj]);
		return out;
	});

	let hasPreviousReferencePoint = $derived.by(
		() => !!current && current.state_id !== 0 && OBJ_KEYS.some((obj) => previousPercent[obj] !== null)
	);

	// Anchor plus the requested change, clamped back into the range so a large step can't push an
	// aspiration past the ideal (or below the nadir) and silently become unreachable.
	let deltaResultPercent = $derived.by(() => {
		const out: Record<string, number> = {};
		for (const obj of OBJ_KEYS) {
			const base = previousPercent[obj] ?? DELTA_FALLBACK_BASE;
			out[obj] = Math.max(0, Math.min(100, base + (deltaValues[obj] ?? 0)));
		}
		return out;
	});

	function referencePointFromInputs(): Record<string, number> {
		if (mode === 'raw') {
			return { ...rawValues };
		}
		if (!current) return { ...percentValues };
		const out: Record<string, number> = {};
		if (mode === 'delta') {
			for (const obj of OBJ_KEYS) out[obj] = rawFromPercent(obj, deltaResultPercent[obj]);
			return out;
		}
		for (const obj of OBJ_KEYS) {
			const frac = Math.max(0, Math.min(100, percentValues[obj] ?? 50)) / 100;
			out[obj] = current.global_nadir[obj] + frac * (current.global_ideal[obj] - current.global_nadir[obj]);
		}
		return out;
	}

	// --- Strategic Design Explorer (multi_scenario_strategic_decisions.ipynb equivalent) ---
	// Browses every design discovered this session — capacities and cross-scenario performance.
	// Purely a read of already-solved designs, so it's refreshed alongside the session tree
	// rather than requiring its own solve.
	// The card itself sits at the very end of the page: `loadStrategicDesigns` also feeds the
	// compound-disruption stress test and the Strategic decisions picker, both of which read
	// `strategicDesigns` and drive `selectedDesignId`, so the data loads regardless of where
	// the browsing card is placed.

	let strategicDesigns: StrategicDesignsResult | null = $state(null);
	let strategicLoading = $state(false);
	let strategicError: string | null = $state(null);
	let selectedDesignId: number | null = $state(null);

	async function loadStrategicDesigns() {
		if (problemId === null) return;
		strategicLoading = true;
		strategicError = null;
		try {
			strategicDesigns = await getStrategicDesigns(problemId, sessionId);
			const ids = strategicDesigns.designs.map((d) => d.design_id);
			if (selectedDesignId === null || !ids.includes(selectedDesignId)) {
				selectedDesignId = ids.length > 0 ? ids[ids.length - 1] : null;
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
				if (deltaValues[obj] === undefined) deltaValues[obj] = 0;
			}
			if (!domainThresholdsSeeded) {
				domainThresholds = { ...current.meta.default_domain_thresholds };
				domainThresholdsSeeded = true;
			}
			if (!maxSolutionsSeeded) {
				maxSolutions = current.meta.scalarizers.length;
				maxSolutionsSeeded = true;
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
				note: note || null,
				max_solutions: maxSolutions > 0 ? maxSolutions : null
			});
			// A change is stated relative to the round it was entered in, so once it has been
			// applied it must go back to zero — leaving it would silently re-apply the same step
			// against the new anchor on the next iterate.
			for (const obj of OBJ_KEYS) deltaValues[obj] = 0;
			await loadSessionTree();
			await loadStrategicDesigns();
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

	// Which matched solution is currently focused, shared by the trade-off chart and the
	// per-scenario panels below (see the "Per-scenario small multiples" block). null = none.
	let selectedSolutionIdx: number | null = $state(null);
	let scenarioPanelLayout: 'grid' | 'row' = $state('grid');

	// Color used for every line that isn't the focused solution, once one is focused.
	const MUTED_LINE_COLOR = '#d4d4d8';

	// --- Trade-off chart derivation: one row per (solution, scenario), colored per solution ---
	// Sourced from `viewedEntry` (the iteration currently being browsed), not always the latest.
	// `scenarioOrder` is the fixed all_scenarios ordering (session-wide, not per-iteration) used
	// to turn each row's scenario name into a 1-based index for the chart's ordinal Scenario axis.
	let scenarioOrder = $derived(current?.all_scenarios ?? []);

	let chartRows = $derived.by(() => {
		const entry = viewedEntry;
		const keys = OBJ_KEYS;
		const order = scenarioOrder;
		if (!entry?.solutions) return [];
		return entry.solutions.flatMap((sol) =>
			sol.breakdown.map((row) => {
				const out: Record<string, number> = {};
				for (const obj of keys) out[obj] = Number(row[obj]);
				const idx = order.indexOf(String(row.scenario));
				out['scenario_idx'] = idx >= 0 ? idx + 1 : 0;
				return out;
			})
		);
	});

	// Row index -> index of the solution that row belongs to. The chart's rows are (solution,
	// scenario) pairs, so this is what turns a click on any single line back into "which design".
	let chartRowSolutionIdx = $derived.by(() => {
		const out: number[] = [];
		(viewedEntry?.solutions ?? []).forEach((sol, solIdx) => {
			sol.breakdown.forEach(() => out.push(solIdx));
		});
		return out;
	});

	let chartColorByIndex = $derived.by(() => {
		const map: Record<string, string> = {};
		const sel = selectedSolutionIdx;
		chartRowSolutionIdx.forEach((solIdx, row) => {
			map[String(row)] = sel === null || sel === solIdx ? solutionColor(solIdx) : MUTED_LINE_COLOR;
		});
		return map;
	});

	// Every row of the selected solution, so all of its scenario lines are drawn thick, opaque and
	// on top at once (the component's multi-selection mode) rather than just the one clicked.
	let chartSelectedRows = $derived.by(() => {
		const sel = selectedSolutionIdx;
		if (sel === null) return null;
		const rows: number[] = [];
		chartRowSolutionIdx.forEach((solIdx, row) => {
			if (solIdx === sel) rows.push(row);
		});
		return rows;
	});

	let chartLineLabels = $derived.by(() => {
		const entry = viewedEntry;
		const map: Record<string, string> = {};
		let i = 0;
		(entry?.solutions ?? []).forEach((sol) => {
			sol.breakdown.forEach((row) => {
				map[String(i)] = `Solution ${sol.solution_number} (design ${sol.design_id}) — ${row.scenario}`;
				i += 1;
			});
		});
		return map;
	});

	// Per-objective axis range spanning the *actually plotted* values (not the full worst-case
	// ideal-nadir span, which is far wider than what's on screen for any single iteration) — port
	// of `plot_axis_ranges` from `multi_scenario_DM_session_new.ipynb`: min/max over every plotted
	// (solution, scenario) value plus the reference point, with a small padding so extreme lines
	// don't sit flush on the frame.
	function axisRanges(
		rows: Record<string, number>[],
		refPoint: Record<string, number> | null | undefined,
		keys: string[]
	) {
		const padFrac = 0.02;
		const ranges: Record<string, [number, number]> = {};
		for (const obj of keys) {
			const vals = rows.map((r) => r[obj]);
			if (refPoint && refPoint[obj] !== undefined) vals.push(refPoint[obj]);
			if (vals.length === 0) {
				ranges[obj] = [0, 1];
				continue;
			}
			const lo = Math.min(...vals);
			const hi = Math.max(...vals);
			const pad = hi !== lo ? (hi - lo) * padFrac : Math.abs(lo) * 0.01 || 1.0;
			ranges[obj] = [lo - pad, hi + pad];
		}
		return ranges;
	}

	let chartAxisRanges = $derived.by(() => axisRanges(chartRows, viewedEntry?.reference_point, OBJ_KEYS));

	let chartDimensions = $derived([
		...OBJ_KEYS.map((obj) => ({
			symbol: obj,
			name: objShortLabel(obj),
			min: chartAxisRanges[obj]?.[0] ?? 0,
			max: chartAxisRanges[obj]?.[1] ?? 1,
			direction: objDirection(obj)
		})),
		// Rightmost axis: which scenario each line's row belongs to. Since it's an ordinary
		// (ordinal) axis on the same brushable component as every other dimension, dragging on
		// it filters the chart down to lines from just that scenario — same drag-to-filter
		// interaction already used for the Design ID axis in the Strategic Design Explorer below.
		...(scenarioOrder.length > 0
			? [
					{
						symbol: 'scenario_idx',
						name: 'Scenario',
						min: 1,
						max: scenarioOrder.length,
						categories: scenarioOrder
					}
				]
			: [])
	]);

	let chartReferenceData = $derived.by(() => {
		const entry = viewedEntry;
		if (!entry?.reference_point || Object.keys(entry.reference_point).length === 0) return undefined;
		return { referencePoint: { values: entry.reference_point, label: 'Reference point' } };
	});

	// --- Per-scenario small multiples ----------------------------------------------------------
	// The trade-off chart above overlays every (solution, scenario) row on one set of axes, which
	// answers "what is the worst-case envelope" but not "what does *this* design do in *that*
	// scenario" — the lines of different designs are impossible to follow once they cross. These
	// panels split the exact same rows one panel per scenario: each panel holds one line per
	// matched solution, and every panel is drawn on the shared `chartAxisRanges` scales, so a
	// line's height means the same thing in all of them. Selecting a solution anywhere (a line in
	// any panel, a line in the trade-off chart, or a chip in the legend) highlights that design in
	// every panel at once and mutes the rest.
	// A solution index only identifies a design *within one iteration's* solution list, so the
	// selection cannot survive stepping through the iteration history — it would silently start
	// pointing at an unrelated design.
	let lastSelectionIteration = -2;
	$effect(() => {
		if (viewedIterationIndex !== lastSelectionIteration) {
			lastSelectionIteration = viewedIterationIndex;
			selectedSolutionIdx = null;
		}
	});

	function toggleSolutionSelection(solIdx: number | null) {
		selectedSolutionIdx = solIdx === null || selectedSolutionIdx === solIdx ? null : solIdx;
	}

	// Same axes as the trade-off chart minus its Scenario axis (each panel *is* one scenario),
	// and deliberately the same min/max, which is what makes the panels comparable to each other.
	let panelDimensions = $derived(
		OBJ_KEYS.map((obj) => ({
			symbol: obj,
			name: objShortLabel(obj),
			min: chartAxisRanges[obj]?.[0] ?? 0,
			max: chartAxisRanges[obj]?.[1] ?? 1,
			direction: objDirection(obj)
		}))
	);

	// One entry per scenario in the session-wide `all_scenarios` order. `solIdxByRow` maps a
	// panel's row index back to the solution it came from: a solution with no breakdown row for
	// this scenario is simply absent from the panel, so row index and solution index diverge.
	let scenarioPanels = $derived.by(() => {
		const sols = viewedEntry?.solutions ?? [];
		const keys = OBJ_KEYS;
		// Annotated because `current` types as `never` here (a pre-existing error on the
		// `scenarioOrder` declaration above), which would otherwise make these implicitly `any`.
		return scenarioOrder.map((scenario: string, sIdx: number) => {
			const rows: Record<string, number>[] = [];
			const solIdxByRow: number[] = [];
			sols.forEach((sol, solIdx) => {
				const br = sol.breakdown.find((r) => String(r.scenario) === scenario);
				if (!br) return;
				const values: Record<string, number> = {};
				for (const obj of keys) values[obj] = Number(br[obj]);
				rows.push(values);
				solIdxByRow.push(solIdx);
			});
			return { scenario, number: sIdx + 1, rows, solIdxByRow };
		});
	});

	function panelColorByIndex(solIdxByRow: number[], sel: number | null): Record<string, string> {
		const map: Record<string, string> = {};
		solIdxByRow.forEach((solIdx, row) => {
			map[String(row)] = sel === null || sel === solIdx ? solutionColor(solIdx) : MUTED_LINE_COLOR;
		});
		return map;
	}

	// Multi-selection mode (an array, even of one) rather than `selectedIndex`, so the panel never
	// mutates its own selection prop and every panel stays driven purely by `selectedSolutionIdx`.
	function panelSelectedRows(solIdxByRow: number[], sel: number | null): number[] | null {
		if (sel === null) return null;
		const row = solIdxByRow.indexOf(sel);
		return row >= 0 ? [row] : [];
	}

	// The tooltip is rendered as HTML by the chart component, so anything interpolated into a label
	// has to be escaped. Objective names come from problem metadata, i.e. not from this file.
	function escapeHtml(text: string): string {
		return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
	}

	// Hover label for one panel line. Carries the actual numbers, because the panels suppress tick
	// text (`showTickLabels={false}`) to stay legible at grid width — without them a line's height
	// could only be eyeballed against the shared range legend, so the values were effectively
	// unreadable unless you first clicked the solution to populate the table underneath.
	function panelLineLabels(panel: {
		rows: Record<string, number>[];
		solIdxByRow: number[];
	}): Record<string, string> {
		const sols = viewedEntry?.solutions ?? [];
		const map: Record<string, string> = {};
		panel.solIdxByRow.forEach((solIdx, row) => {
			const sol = sols[solIdx];
			if (!sol) return;
			const values = OBJ_KEYS.map((obj) => {
				const v = panel.rows[row]?.[obj];
				return `${escapeHtml(objShortLabel(obj))}: ${typeof v === 'number' && Number.isFinite(v) ? fmt(v) : '—'}`;
			}).join('<br>');
			map[String(row)] =
				`<strong>Solution ${sol.solution_number}</strong> (design ${sol.design_id})<br>${values}`;
		});
		return map;
	}

	// Axis names are drawn rotated along each axis (`verticalAxisLabels`) — horizontal ones
	// overlap their neighbours at panel width. Tick numbers are on but compact
	// (`compactTickLabels`): full thousands-separated values do not fit between two axes here, so
	// they are drawn as "-32.1M" / "7.9k" at a smaller size with a white halo. The legend under
	// the header still carries each axis's unit and full range for all eight panels at once.
	const PANEL_OPTIONS = {
		showAxisLabels: true,
		highlightOnHover: true,
		strokeWidth: 2,
		opacity: 0.7,
		enableBrushing: false
	};

	let panelAxisLegend = $derived(
		OBJ_KEYS.map((obj, i) => ({
			symbol: obj,
			label: objLabel(obj),
			color: COLOR_PALETTE[i % COLOR_PALETTE.length],
			range: chartAxisRanges[obj] ?? [0, 1]
		}))
	);

	let selectedSolution = $derived.by(() =>
		selectedSolutionIdx === null ? null : (viewedEntry?.solutions?.[selectedSolutionIdx] ?? null)
	);

	function solutionColor(index: number): string {
		return SOLUTION_COLORS[index % SOLUTION_COLORS.length];
	}

	function fmt(v: number): string {
		return v.toLocaleString(undefined, { maximumFractionDigits: 1 });
	}

	// --- Strategic decisions of the matched solutions ------------------------------------------
	// What the (hidden) Strategic Design Explorer was really needed for: which of the solutions on
	// screen builds what. Scoped to the matched solutions of the viewed iteration rather than every
	// design ever discovered, and driven by its own design picker.
	let strategicCardDesignId: number | null = $state(null);

	// Each matched solution paired with the strategic design it came from. `design` is null only
	// while the session-wide design list is still loading.
	let strategicDesignOptions = $derived.by(() => {
		const sols = viewedEntry?.solutions ?? [];
		const byId = new Map((strategicDesigns?.designs ?? []).map((d) => [d.design_id, d]));
		return sols.map((sol, solIdx) => ({
			solIdx,
			designId: sol.design_id,
			solutionNumber: sol.solution_number,
			design: byId.get(sol.design_id) ?? null
		}));
	});

	// The card follows whichever solution is focused in the charts above; picking a different
	// design in the card's own selector overrides that until the focus changes again. The last
	// synced focus is tracked explicitly rather than read back out of `strategicCardDesignId`, so
	// a manual pick can never feed back in and undo itself.
	let lastSyncedFocus: number | null | undefined = undefined;
	$effect(() => {
		const focused = selectedSolutionIdx;
		const opts = strategicDesignOptions;
		if (focused !== lastSyncedFocus) {
			lastSyncedFocus = focused;
			if (focused !== null && opts[focused]) {
				strategicCardDesignId = opts[focused].designId;
				return;
			}
		}
		// Fall back to the first solution whenever the current pick isn't on offer any more
		// (new iteration, different match set).
		if (opts.length > 0 && !opts.some((o) => o.designId === strategicCardDesignId)) {
			strategicCardDesignId = opts[0].designId;
		}
	});

	let strategicCardDesign = $derived.by(() => {
		const id = strategicCardDesignId;
		if (id === null) return null;
		return strategicDesigns?.designs.find((d) => d.design_id === id) ?? null;
	});

	let strategicCardCapacityRows = $derived(capacityRowsFor(strategicCardDesign));

	// The solution number that goes with the design the card is showing, for its heading.
	let strategicCardSolution = $derived.by(
		() => strategicDesignOptions.find((o) => o.designId === strategicCardDesignId) ?? null
	);

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
		const colors = scalarizerColorByName;
		const map: Record<string, string> = {};
		(sd?.designs ?? []).forEach((d, i) => {
			map[String(i)] = colors[d.scalarizer] ?? SOLUTION_COLORS[i % SOLUTION_COLORS.length];
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

	let scalarizersPresent = $derived.by(() => {
		const sd = strategicDesigns;
		return [...new Set((sd?.designs ?? []).map((d) => d.scalarizer))].sort();
	});

	let selectedDesign = $derived.by(() => {
		const sd = strategicDesigns;
		const id = selectedDesignId;
		if (!sd || id === null) return null;
		return sd.designs.find((d) => d.design_id === id) ?? null;
	});

	// One row per strategic variable for a given design: what already exists, what this design
	// builds on top of it, and the resulting total. `changePct` is the added capacity as a
	// percentage of the existing one, and is null where nothing exists to compare against
	// (a component built from zero has no meaningful percentage increase).
	function capacityRowsFor(design: StrategicDesign | null) {
		const sd = strategicDesigns;
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
	}

	let selectedCapacityRows = $derived(capacityRowsFor(selectedDesign));

	let selectedRobustRows = $derived.by(() => {
		const design = selectedDesign;
		const cur = current;
		if (!design || !cur) return [];
		return OBJ_KEYS.map((obj) => ({
			obj,
			label: objLabel(obj),
			worstCase: design.robust_vals[obj],
			ideal: cur.global_ideal[obj],
			nadir: cur.global_nadir[obj]
		}));
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

	// --- Robustness analysis (multi_scenario_stage2c_analysis.ipynb equivalent, minus the
	// antifragility section, which this page doesn't display) ---
	let analysis: AnalysisResult | null = $state(null);
	let analysisLoading = $state(false);
	let analysisError: string | null = $state(null);
	let domainThresholds: Record<string, number> = $state({});
	let domainThresholdsSeeded = false;

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
		OBJ_KEYS.map((obj) => ({
			symbol: obj,
			name: `${objShortLabel(obj)} regret`,
			min: 0,
			max: 1,
			direction: 'min' as const
		}))
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
	let scenarioCount = $derived.by(() => current?.all_scenarios.length ?? 8);
	let domainDimensions = $derived(
		OBJ_KEYS.map((obj) => ({
			symbol: obj,
			name: `${objShortLabel(obj)} met`,
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

	// --- Compound-disruption stress test (multi_scenario_combined_scenarios_analysis.ipynb) ---
	// Tests wish-listed designs (falling back to all discovered designs if the wish list is
	// empty) against all pairwise combinations of the non-baseline scenarios — a much harder
	// question than the single-disruption robustness above. Solves live; opt-in via a button
	// rather than auto-run, since it's substantially slower than a normal iteration. Only shown
	// for problems whose metadata configures a compound-scenario hook (see
	// `desdeo.api.routers.jina_compound`) — a generic problem with none configured just doesn't
	// get this card.
	let combinedScenario: CombinedScenarioResult | null = $state(null);
	let combinedScenarioLoading = $state(false);
	let combinedScenarioError: string | null = $state(null);

	// Each (design, combined scenario) pair is re-evaluated by solving one ASF against this
	// reference point, so every row of the results is the objective vector of a single achievable
	// operating plan — not the pair's ideal point, which is what independently re-optimizing each
	// objective returns and which no operating plan ever achieves.
	//
	// Deliberately its own state rather than reusing the iterate form's: this reference point says
	// how the DM wants a *fixed* design operated under a compound disruption, which is a different
	// question from what they were asking the search for, and silently inheriting the other form's
	// value would hide that. It starts unset and the run is blocked until it is filled in — the
	// answer has no meaning without the aspiration it is achieving.
	let comboRefMode: 'percent' | 'raw' = $state('percent');
	let comboRefPercent: Record<string, number | null> = $state({});
	let comboRefRaw: Record<string, number | null> = $state({});

	// Null until every objective has a value — that null is what blocks the run. Percent mode also
	// needs `current` for the ideal/nadir range to convert against, so it stays null without it
	// rather than silently converting against a zero range.
	let comboReferencePoint = $derived.by(() => {
		const raw = comboRefMode === 'raw';
		if (!raw && !current) return null;
		const src = raw ? comboRefRaw : comboRefPercent;
		const out: Record<string, number> = {};
		for (const obj of OBJ_KEYS) {
			const v = src[obj];
			if (v === null || v === undefined || !Number.isFinite(v)) return null;
			out[obj] = raw ? v : rawFromPercent(obj, v);
		}
		return out;
	});

	let comboRefReady = $derived(comboReferencePoint !== null);

	async function handleRunCombinedScenarioAnalysis() {
		if (problemId === null) return;
		const referencePoint = comboReferencePoint;
		if (referencePoint === null) {
			combinedScenarioError =
				'Set a reference point for every objective before running the stress test.';
			return;
		}
		combinedScenarioLoading = true;
		combinedScenarioError = null;
		try {
			combinedScenario = await getCombinedScenarioAnalysis({
				problem_id: problemId,
				session_id: sessionId,
				reference_point: referencePoint
			});
		} catch (e) {
			combinedScenarioError =
				e instanceof Error ? e.message : 'Failed to run the compound-disruption analysis.';
		} finally {
			combinedScenarioLoading = false;
		}
	}

	let comboDesignIds = $derived.by(() => combinedScenario?.candidate_ids ?? []);

	function comboDesignColor(designId: number): string {
		const idx = comboDesignIds.indexOf(designId);
		return SOLUTION_COLORS[idx % SOLUTION_COLORS.length];
	}

	function comboValue(designId: number, comboName: string, obj: string): number | null {
		const cs = combinedScenario;
		if (!cs) return null;
		const row = cs.rows.find(
			(r) => r.design_id === designId && r.combined_scenario === comboName && r.status === 'ok'
		);
		return row ? Number(row[obj]) : null;
	}

	// --- Single-vs-combined disruption comparison (multi_scenario_combined_scenarios_analysis_new.ipynb's
	// triplet_pc) — for the design selected in the Strategic Design Explorer, an interactive pick
	// of any two disruptions shows three parallel-coordinates lines: each alone, and combined.
	// Reuses `combinedScenario.reference_rows`/`rows` from the compound-disruption stress test
	// above, so this section only appears once that's been run.
	function referenceValue(designId: number, name: string, obj: string): number | null {
		const cs = combinedScenario;
		if (!cs) return null;
		const row = cs.reference_rows.find(
			(r) => r.design_id === designId && r.combined_scenario === name && r.status === 'ok'
		);
		return row ? Number(row[obj]) : null;
	}

	let singleDisruptionNames = $derived.by(() => {
		const names = new Set<string>();
		(combinedScenario?.reference_rows ?? []).forEach((r) => {
			if (r.combined_scenario !== 'baseline') names.add(String(r.combined_scenario));
		});
		return [...names];
	});

	let tripletA: string | null = $state(null);
	let tripletB: string | null = $state(null);

	// Seed the picker once real disruption names are available (only known after the compound
	// stress test runs) — can't set a static initial value up front.
	$effect(() => {
		const names = singleDisruptionNames;
		if (tripletA === null && names.length > 0) tripletA = names[0];
		if (tripletB === null && names.length > 1) tripletB = names[1];
	});

	function comboNameFor(a: string | null, b: string | null): string | null {
		const pc = combinedScenario?.pair_components;
		if (!a || !b || a === b || !pc) return null;
		for (const [name, pair] of Object.entries(pc)) {
			const [x, y] = pair;
			if ((x === a && y === b) || (x === b && y === a)) return name;
		}
		return null;
	}

	// The compound-disruption stress test only tests its candidate designs (the wish list, or an
	// explicit design_ids request) — not every design ever discovered. If the design currently
	// selected in the Strategic Design Explorer wasn't one of them, every pair will genuinely have
	// no data (not "infeasible" — never solved at all), so this needs its own message rather than
	// looking like a solve failure.
	let selectedDesignTested = $derived.by(() => {
		const design = selectedDesign;
		const cs = combinedScenario;
		if (!design || !cs) return false;
		return cs.candidate_ids.includes(design.design_id);
	});

	let tripletLines = $derived.by(() => {
		const design = selectedDesign;
		const a = tripletA;
		const b = tripletB;
		const keys = superaddObjKeys;
		if (!design || keys.length === 0) return [];

		function lineFor(label: string, color: string, lookup: (obj: string) => number | null) {
			const values: Record<string, number> = {};
			for (const obj of keys) {
				const v = lookup(obj);
				if (v === null) return null;
				values[obj] = v;
			}
			return { label, color, values };
		}

		const lines: { label: string; color: string; values: Record<string, number> }[] = [];
		if (a) {
			const line = lineFor(`A: ${a}`, '#4c78a8', (obj) => referenceValue(design.design_id, a, obj));
			if (line) lines.push(line);
		}
		if (b) {
			const line = lineFor(`B: ${b}`, '#e6a817', (obj) => referenceValue(design.design_id, b, obj));
			if (line) lines.push(line);
		}
		const comboName = comboNameFor(a, b);
		if (comboName) {
			const line = lineFor(`${a} + ${b}`, '#c0392b', (obj) => comboValue(design.design_id, comboName, obj));
			if (line) lines.push(line);
		}
		return lines;
	});

	let tripletChartRows = $derived(tripletLines.map((l) => l.values));
	let tripletColorByIndex = $derived.by(() => {
		const map: Record<string, string> = {};
		tripletLines.forEach((l, i) => (map[String(i)] = l.color));
		return map;
	});
	let tripletLineLabels = $derived.by(() => {
		const map: Record<string, string> = {};
		tripletLines.forEach((l, i) => (map[String(i)] = l.label));
		return map;
	});
	let tripletDimensions = $derived.by(() => {
		return superaddObjKeys.map((obj) => {
			const vals = tripletLines.map((l) => l.values[obj]).filter((v): v is number => v !== undefined);
			const lo = vals.length > 0 ? Math.min(...vals) : 0;
			const hi = vals.length > 0 ? Math.max(...vals) : 1;
			const pad = hi !== lo ? (hi - lo) * 0.05 : Math.abs(lo) * 0.01 || 1;
			return {
				symbol: obj,
				name: objShortLabel(obj),
				min: lo - pad,
				max: hi + pad,
				direction: objDirection(obj)
			};
		});
	});

	// Feasibility is per (design, combo) pair, not per objective — the same count applies to
	// every one of the objective heatmaps below, since infeasibility means the LP itself had no
	// solution, not that one particular objective failed.
	let comboInfeasibleByDesign = $derived.by(() => {
		const cs = combinedScenario;
		const map: Record<number, number> = {};
		if (!cs) return map;
		for (const id of cs.candidate_ids) {
			map[id] = cs.rows.filter((r) => r.design_id === id && r.status !== 'ok').length;
		}
		return map;
	});

	let comboInfeasibleByCombo = $derived.by(() => {
		const cs = combinedScenario;
		const map: Record<string, number> = {};
		if (!cs) return map;
		for (const name of cs.combo_names) {
			map[name] = cs.rows.filter((r) => r.combined_scenario === name && r.status !== 'ok').length;
		}
		return map;
	});

	let comboTotalInfeasible = $derived.by(
		() => combinedScenario?.rows.filter((r) => r.status !== 'ok').length ?? 0
	);
	let comboTotalPairs = $derived.by(() => combinedScenario?.rows.length ?? 0);

	let comboHeatRanges = $derived.by(() => {
		const cs = combinedScenario;
		const ranges: Record<string, [number, number]> = {};
		for (const obj of OBJ_KEYS) {
			const vals = (cs?.rows ?? []).filter((r) => r.status === 'ok').map((r) => Number(r[obj]));
			ranges[obj] = vals.length > 0 ? [Math.min(...vals), Math.max(...vals)] : [0, 1];
		}
		return ranges;
	});

	// Compact number formatting for the heatmap cells — with many columns, full comma-grouped
	// numbers (e.g. "-79,638,427.5") would make the table unreadably wide, so large magnitudes
	// are abbreviated with a K/M suffix. Still uses comboHeatRanges (not colors) to decide
	// nothing — this is purely a display shorthand, the underlying value is unchanged.
	function fmtCompact(v: number): string {
		const abs = Math.abs(v);
		if (abs >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
		if (abs >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
		return v.toLocaleString(undefined, { maximumFractionDigits: 1 });
	}

	// --- Super-additivity heatmap (multi_scenario_combined_scenarios_analysis_new.ipynb) ---
	// super_add = combined − (baseline + ΔA + ΔB) = combined + baseline − A_alone − B_alone: how
	// far a combined scenario's outcome runs beyond the sum of its two single-disruption effects.
	// Positive (red) = the pair synergizes worse than expected; negative (blue) = the disruptions
	// overlap/saturate. Cell text is still the raw compound value (same as the table above) —
	// only the cell color encodes super-additivity, kept as a separate table so the two readings
	// (level vs. interaction) don't get conflated in one number.
	function comboSuperaddValue(designId: number, comboName: string, obj: string): number | null {
		const cs = combinedScenario;
		if (!cs) return null;
		const row = cs.rows.find(
			(r) => r.design_id === designId && r.combined_scenario === comboName && r.status === 'ok'
		);
		const v = row?.[`${obj}_superadd`];
		return typeof v === 'number' ? v : null;
	}

	// Super-additivity is meaningless (always exactly 0) for an objective that doesn't vary by
	// scenario — combined/baseline/A-alone/B-alone are all identical for a first-stage-only cost,
	// so there's no interaction to show. Skip those objectives here (only here — the main
	// performance table above still shows every objective), rather than hard-coding which one,
	// so this generalizes to any problem's own shared-vs-varying split.
	let superaddObjKeys = $derived(OBJ_KEYS.filter((obj) => objMetaBySymbol[obj]?.varies_by_scenario));

	let comboSuperaddRanges = $derived.by(() => {
		const cs = combinedScenario;
		const ranges: Record<string, number> = {};
		for (const obj of superaddObjKeys) {
			const vals = (cs?.rows ?? [])
				.map((r) => r[`${obj}_superadd`])
				.filter((v): v is number => typeof v === 'number')
				.map((v) => Math.abs(v));
			ranges[obj] = vals.length > 0 ? Math.max(...vals) : 1;
		}
		return ranges;
	});

	// Diverging blue (sub-additive) -> white (0) -> red (super-additive) scale, symmetric around
	// 0 at each objective's own max-magnitude — no external color-scale library needed for a
	// simple two-hue diverging map.
	function superaddColor(sa: number | null, maxAbs: number): string {
		if (sa === null || maxAbs === 0) return '#eee';
		const t = Math.max(-1, Math.min(1, sa / maxAbs));
		if (t >= 0) {
			const c = Math.round(255 * (1 - t));
			return `rgb(255,${c},${c})`;
		}
		const c = Math.round(255 * (1 + t));
		return `rgb(${c},${c},255)`;
	}

	// Numbered so it can be a compact axis on the chart (see comboChartDimensions) — the actual
	// name is still shown via the hover label and the key list under the chart, same pattern as
	// the "Scenario # key" in multi_scenario_DM_session_new.ipynb's own trade-off plot.
	let comboNumberByName = $derived.by(() => {
		const cs = combinedScenario;
		const map: Record<string, number> = {};
		(cs?.combo_names ?? []).forEach((name, i) => (map[name] = i + 1));
		return map;
	});

	let comboChartRows = $derived.by(() => {
		const cs = combinedScenario;
		if (!cs) return [];
		const numberByName = comboNumberByName;
		const keys = OBJ_KEYS;
		return cs.rows
			.filter((r) => r.status === 'ok')
			.map((r) => {
				const out: Record<string, number> = { combo_num: numberByName[r.combined_scenario] ?? 0 };
				for (const obj of keys) out[obj] = Number(r[obj]);
				return out;
			});
	});

	let comboColorByIndex = $derived.by(() => {
		const cs = combinedScenario;
		const map: Record<string, string> = {};
		if (!cs) return map;
		const okRows = cs.rows.filter((r) => r.status === 'ok');
		okRows.forEach((r, i) => {
			map[String(i)] = comboDesignColor(r.design_id);
		});
		return map;
	});

	let comboChartLineLabels = $derived.by(() => {
		const cs = combinedScenario;
		const map: Record<string, string> = {};
		if (!cs) return map;
		const okRows = cs.rows.filter((r) => r.status === 'ok');
		const solNumOf = (id: number) => cs.summary.find((s) => s.design_id === id)?.solution_number ?? id;
		okRows.forEach((r, i) => {
			map[String(i)] = `Solution ${solNumOf(r.design_id)} (design ${r.design_id}) — ${r.combined_scenario}`;
		});
		return map;
	});

	let comboChartDimensions = $derived.by(() => {
		const ranges = comboHeatRanges;
		const cs = combinedScenario;
		return [
			...OBJ_KEYS.map((obj) => ({
				symbol: obj,
				name: objShortLabel(obj),
				min: ranges[obj]?.[0] ?? 0,
				max: ranges[obj]?.[1] ?? 1,
				direction: objDirection(obj)
			})),
			{ symbol: 'combo_num', name: 'Combined scenario #', min: 1, max: cs?.combo_names.length ?? 1 }
		];
	});

	// Only used for the pre-run copy in the card description (before combinedScenario has any
	// real combo_names to count) — an estimate from the scenario count, not authoritative.
	let nonBaselineCount = $derived(Math.max(scenarioCount - 1, 0));
	let comboCountEstimate = $derived(nonBaselineCount > 1 ? (nonBaselineCount * (nonBaselineCount - 1)) / 2 : 0);

	// Starts a brand-new interactive session (shared with the sibling District Heating System
	// method, since both key their state off the same session id) and reloads this page against
	// it — nothing from the old session is deleted, it's just no longer selected; the DM can
	// still get back to it from /methods/sessions.
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
			strategicDesigns = null;
			selectedDesignId = null;
			analysis = null;
			combinedScenario = null;
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
	<title>JINA (interactive two-stage robustness) | DESDEO</title>
	<meta
		name="description"
		content="Multi-scenario, live-solving robust reference-point matching against any problem with an attached scenario model."
	/>
</svelte:head>

<div class="container mx-auto max-w-6xl space-y-6 px-4 py-8">
	<div class="flex items-start justify-between gap-4">
		<div>
			<h1 class="text-3xl font-bold tracking-tight">JINA (interactive two-stage robustness)</h1>
			<p class="text-muted-foreground mt-1 text-sm italic">
				JINA: Joint Infrastructure Network Adaptation
			</p>
			<p class="text-muted-foreground mt-1">
				Set a reference point for the worst-case (robust) objectives below. Each iteration
				<strong>solves live with Gurobi</strong> across all {scenarioCount} scenarios — this can take
				around a minute. Because there's no fixed pool to draw from, a design can resurface in a
				later round; it's flagged as a repeat rather than hidden.
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
					This method needs a DESDEO problem with an attached scenario model. Pick one from the
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
						One worst-case aspiration value per objective. Use percent-of-range for a quick start,
						raw values once you know the numbers you want, or change-from-previous to nudge last
						round's aspirations up or down. Always solves all
						{current.meta.scalarizers.length} scalarizer variants (balanced + one per objective).
					</Card.Description>
				</Card.Header>
				<Card.Content>
					<Tabs.Root value={mode} onValueChange={(v) => (mode = v as 'percent' | 'raw' | 'delta')}>
						<Tabs.List>
							<Tabs.Trigger value="percent">Percent of range</Tabs.Trigger>
							<Tabs.Trigger value="raw">Raw values</Tabs.Trigger>
							<Tabs.Trigger value="delta">Change from previous</Tabs.Trigger>
						</Tabs.List>

						<Tabs.Content value="percent" class="mt-4">
							<div class="grid grid-cols-2 gap-4 md:grid-cols-4">
								{#each OBJ_KEYS as obj}
									<div>
										<Label for={`pct-${obj}`}>{objLabel(obj)} (worst case)</Label>
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
										<Label for={`raw-${obj}`}>{objLabel(obj)} (worst case)</Label>
										<Input id={`raw-${obj}`} type="number" bind:value={rawValues[obj]} />
										<!-- The bounds a raw value has to be typed between. Only the percent tab
										     used to show them, which is backwards: there the scale is self-evident
										     from 0-100, and it is raw entry that needs the numbers on screen. -->
										<p class="text-muted-foreground mt-1 text-xs">
											ideal {fmt(current.global_ideal[obj])} · nadir {fmt(current.global_nadir[obj])}
										</p>
									</div>
								{/each}
							</div>
						</Tabs.Content>

						<!-- Change mode: the inputs are steps in percentage points on the same 0-100 scale
						     as the percent tab, applied to the previous iteration's reference point. Each
						     field shows the arithmetic it produces, so the DM never has to hold the anchor
						     in their head. -->
						<Tabs.Content value="delta" class="mt-4">
							<p class="text-muted-foreground mb-3 text-xs">
								{#if hasPreviousReferencePoint}
									Enter how far to move each aspiration compared with the previous iteration, in
									percentage points of the 0 = nadir … 100 = ideal range. +10 asks for ten points
									closer to the ideal, -10 concedes ten. Resets to 0 after each iteration.
								{:else}
									No previous iteration to move from yet, so changes apply from the midpoint of
									the range (50). Once you have iterated once, this anchors on the reference
									point you actually used.
								{/if}
							</p>
							<div class="grid grid-cols-2 gap-4 md:grid-cols-4">
								{#each OBJ_KEYS as obj}
									{@const base = previousPercent[obj] ?? DELTA_FALLBACK_BASE}
									{@const result = deltaResultPercent[obj]}
									<div>
										<Label for={`delta-${obj}`}>{objLabel(obj)} (worst case)</Label>
										<Input
											id={`delta-${obj}`}
											type="number"
											step="1"
											bind:value={deltaValues[obj]}
										/>
										<p class="text-muted-foreground mt-1 text-xs">
											{base.toFixed(0)}% → {result.toFixed(0)}% of range ({fmt(
												rawFromPercent(obj, result)
											)})
										</p>
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
								max={current?.meta.scalarizers.length ?? 5}
								bind:value={maxSolutions}
							/>
						</div>
						<div class="md:col-span-2">
							<Label for="note">Note (optional)</Label>
							<Input id="note" type="text" bind:value={note} placeholder="e.g. iteration 2" />
						</div>
					</div>

					<Button class="mt-4" disabled={loading} onclick={handleIterate}>
						{loading ? 'Solving live (this can take about a minute)…' : 'Run iteration'}
					</Button>
				</Card.Content>
			</Card.Root>
		{:else}
			<Card.Root>
				<Card.Content class="text-muted-foreground py-6 text-sm">
					{loading
						? 'Building the scenario context for this problem — this can take a while the first time.'
						: 'No data yet.'}
				</Card.Content>
			</Card.Root>
		{/if}

		{#if current && viewedEntry?.solutions && viewedEntry.solutions.length > 0}
			<Card.Root>
				<Card.Header>
					<Card.Title>Matched solutions</Card.Title>
					<Card.Description>
						{viewedEntry.solutions.length} distinct design(s) from {current.meta.scalarizers.length}
						scalarizer variants this round (fewer means some variants converged on the same design).
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
								<Table.Head></Table.Head>
							</Table.Row>
						</Table.Header>
						<Table.Body>
							{#each viewedEntry.solutions as sol, i (sol.design_id)}
								<Table.Row>
									<Table.Cell>
										<!-- Doubles as the focus control for both charts below: same selection
										     the trade-off lines and the per-scenario panels react to. -->
										<button
											type="button"
											class="hover:underline"
											class:font-semibold={selectedSolutionIdx === i}
											title="Focus this solution in the charts below"
											onclick={() => toggleSolutionSelection(i)}
										>
											<span
												class="inline-block h-3 w-3 rounded-full align-middle"
												style={`background-color:${solutionColor(i)}`}
											></span>
											Solution {sol.solution_number}
										</button>
										{#if sol.repeat}
											<Badge variant="outline" class="ml-1">repeat</Badge>
										{/if}
									</Table.Cell>
									<Table.Cell>{sol.design_id}</Table.Cell>
									<Table.Cell>
										<div class="flex flex-wrap gap-1">
											{#each sol.matched_by as name}
												<Badge variant="secondary">{name}</Badge>
											{/each}
										</div>
									</Table.Cell>
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
						design, showing its full worst-case performance envelope across all scenarios. Lines
						sharing a color belong to the same solution. Drag on the Scenario axis (right) to
						narrow the view to a single scenario and see how each candidate performs there.
						Click a line to focus that solution here and in the per-scenario panels below.
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
							multipleSelectedIndexes={chartSelectedRows}
							onLineSelect={(row) =>
								toggleSolutionSelection(row === null ? null : (chartRowSolutionIdx[row] ?? null))}
						/>
					</div>
				</Card.Content>
			</Card.Root>

			<Card.Root>
				<Card.Header>
					<Card.Title>Per-scenario view</Card.Title>
					<Card.Description>
						The same matched solutions, split into one panel per scenario — each panel shows how
						every candidate performs in that scenario alone. All panels share the axis ranges of
						the trade-off view above, so a line's height means the same thing in each of them.
						The dashed line is this iteration's reference point, drawn on every panel at the same
						height as in the trade-off view, so you can read each scenario's outcome against
						what you asked for — bearing in mind you asked for it as a <em>worst case</em> across
						scenarios, which most individual scenarios should beat.
						<strong>Hover any line to read its exact values.</strong> Click a line, or a solution
						below, to follow one design across all {scenarioOrder.length} scenarios at once.
					</Card.Description>
				</Card.Header>
				<Card.Content class="space-y-4">
					<div class="flex flex-wrap items-center gap-2">
						{#each viewedEntry.solutions as sol, i (sol.design_id)}
							<button
								type="button"
								class="hover:bg-accent flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs"
								class:opacity-40={selectedSolutionIdx !== null && selectedSolutionIdx !== i}
								class:border-foreground={selectedSolutionIdx === i}
								onclick={() => toggleSolutionSelection(i)}
							>
								<span
									class="inline-block h-3 w-3 rounded-full"
									style={`background-color:${solutionColor(i)}`}
								></span>
								Solution {sol.solution_number}
							</button>
						{/each}
						{#if selectedSolutionIdx !== null}
							<Button size="sm" variant="ghost" onclick={() => (selectedSolutionIdx = null)}>
								Clear
							</Button>
						{/if}
						<div class="ml-auto flex items-center gap-1">
							<Button
								size="sm"
								variant={scenarioPanelLayout === 'grid' ? 'default' : 'outline'}
								onclick={() => (scenarioPanelLayout = 'grid')}
							>
								Grid
							</Button>
							<Button
								size="sm"
								variant={scenarioPanelLayout === 'row' ? 'default' : 'outline'}
								onclick={() => (scenarioPanelLayout = 'row')}
							>
								One row
							</Button>
						</div>
					</div>

					<!-- Shared axis key: the panels themselves are too narrow to carry axis names and
					     tick numbers, and every panel uses these same ranges. -->
					<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs">
						{#each panelAxisLegend as ax (ax.symbol)}
							<span class="flex items-center gap-1.5">
								<span
									class="inline-block h-3 w-3 rounded-sm border border-neutral-700"
									style={`background-color:${ax.color}`}
								></span>
								<span class="font-medium">{ax.label}</span>
								<span class="text-muted-foreground">{fmt(ax.range[0])} – {fmt(ax.range[1])}</span>
							</span>
						{/each}
					</div>

					<div
						class={scenarioPanelLayout === 'grid'
							? 'grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4'
							: 'flex gap-3 overflow-x-auto pb-2'}
					>
						{#each scenarioPanels as panel (panel.scenario)}
							<div
								class="rounded-md border p-2 {scenarioPanelLayout === 'row'
									? 'w-72 shrink-0'
									: ''}"
							>
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
											referenceData={chartReferenceData}
											colorByIndex={panelColorByIndex(panel.solIdxByRow, selectedSolutionIdx)}
											multipleSelectedIndexes={panelSelectedRows(
												panel.solIdxByRow,
												selectedSolutionIdx
											)}
											lineLabels={panelLineLabels(panel)}
											onLineSelect={(row) =>
												toggleSolutionSelection(
													row === null ? null : (panel.solIdxByRow[row] ?? null)
												)}
										/>
									</div>
								{:else}
									<p class="text-muted-foreground py-16 text-center text-xs">
										No result in this scenario
									</p>
								{/if}
							</div>
						{/each}
					</div>

					{#if selectedSolution}
						<div class="border-t pt-4">
							<p class="mb-2 text-sm font-medium">
								<span
									class="mr-1 inline-block h-3 w-3 rounded-full align-middle"
									style={`background-color:${solutionColor(selectedSolutionIdx ?? 0)}`}
								></span>
								Solution {selectedSolution.solution_number} (design {selectedSolution.design_id})
								scenario by scenario
							</p>
							<div class="overflow-x-auto">
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
										{#each scenarioPanels as panel (panel.scenario)}
											{@const row = panel.solIdxByRow.indexOf(selectedSolutionIdx ?? -1)}
											<Table.Row>
												<Table.Cell>{panel.number}. {panel.scenario}</Table.Cell>
												{#each OBJ_KEYS as obj}
													<Table.Cell>
														{row >= 0 ? fmt(panel.rows[row][obj]) : '—'}
													</Table.Cell>
												{/each}
											</Table.Row>
										{/each}
									</Table.Body>
								</Table.Root>
							</div>
						</div>
					{/if}
				</Card.Content>
			</Card.Root>
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
							Set these to match your own robustness criteria before analyzing, they are not derived
							from the data. Domain criterion counts a design as meeting the threshold in a scenario
							when its objective value is at or better than this. Max regret is normalized against
							this session's discovered designs; domain criterion uses this session's designs only.
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
						Computed across the discovered design pool, shown for wish-listed designs only. 0 =
						this design was the best achiever in that scenario/objective; 1 = the worst. Lower is
						more robust.
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

		{#if current?.meta.supports_compound_scenarios}
			<Card.Root>
				<Card.Header>
					<Card.Title>Compound-disruption stress test</Card.Title>
					<Card.Description>
						Everything above tests one scenario at a time. This asks a harder question: how does
						a candidate design perform when <strong>two disruptions hit at once</strong>? Tests the
						wish list (or every discovered design, if the wish list is empty) against all
						{comboCountEstimate} pairwise combinations of the {nonBaselineCount} non-baseline
						scenarios, capacities fixed, and the operational decisions re-optimized as a single
						plan against the reference point you give below. This is much slower than a normal
						iteration — it solves candidates × {comboCountEstimate} problems live and can take
						several minutes.
					</Card.Description>
				</Card.Header>
				<Card.Content class="space-y-4">
					<!-- Required, and deliberately not prefilled from the iterate form above: this
					     reference point says how a *fixed* design should be operated when two disruptions
					     hit, which is a different question from what the search was asked for. Each
					     (design, combined scenario) pair is then one ASF solve, so every reported row is
					     an operating plan that actually exists — rather than the pair's ideal point, whose
					     objectives each come from a different plan. -->
					<div class="rounded-md border p-4">
						<p class="mb-1 text-sm font-medium">Reference point for the re-evaluation</p>
						<p class="text-muted-foreground mb-3 text-xs">
							Required — the stress test reports how each design performs when operated toward
							these aspiration levels, so there is no meaningful default. Every objective must
							be filled in.
						</p>

						<Tabs.Root
							value={comboRefMode}
							onValueChange={(v) => (comboRefMode = v as 'percent' | 'raw')}
						>
							<Tabs.List>
								<Tabs.Trigger value="percent" disabled={!current}>Percent of range</Tabs.Trigger>
								<Tabs.Trigger value="raw">Raw values</Tabs.Trigger>
							</Tabs.List>

							<Tabs.Content value="percent" class="mt-4">
								{#if current}
									<div class="grid grid-cols-2 gap-4 md:grid-cols-4">
										{#each OBJ_KEYS as obj (obj)}
											<div>
												<Label for={`combo-pct-${obj}`}>{objLabel(obj)}</Label>
												<Input
													id={`combo-pct-${obj}`}
													type="number"
													min="0"
													max="100"
													placeholder="0-100"
													bind:value={comboRefPercent[obj]}
												/>
												<p class="text-muted-foreground mt-1 text-xs">
													100 = ideal ({fmt(current.global_ideal[obj])}), 0 = nadir ({fmt(
														current.global_nadir[obj]
													)})
												</p>
											</div>
										{/each}
									</div>
								{:else}
									<p class="text-muted-foreground text-xs">
										The ideal-nadir range isn't loaded yet — use raw values, or run an iteration
										first.
									</p>
								{/if}
							</Tabs.Content>

							<Tabs.Content value="raw" class="mt-4">
								<div class="grid grid-cols-2 gap-4 md:grid-cols-4">
									{#each OBJ_KEYS as obj (obj)}
										<div>
											<Label for={`combo-raw-${obj}`}>{objLabel(obj)}</Label>
											<Input
												id={`combo-raw-${obj}`}
												type="number"
												placeholder="raw units"
												bind:value={comboRefRaw[obj]}
											/>
											<!-- The worst-case bounds a raw value has to be typed between. Guarded,
											     unlike the iterate form's, because raw entry here is available before
											     an iteration has been run and `current` can still be null. -->
											{#if current}
												<p class="text-muted-foreground mt-1 text-xs">
													ideal {fmt(current.global_ideal[obj])} · nadir {fmt(
														current.global_nadir[obj]
													)}
												</p>
											{/if}
										</div>
									{/each}
								</div>
							</Tabs.Content>
						</Tabs.Root>
					</div>

					<Button
						disabled={combinedScenarioLoading || !comboRefReady}
						onclick={handleRunCombinedScenarioAnalysis}
					>
						{combinedScenarioLoading
							? 'Solving live (this can take several minutes)…'
							: 'Run compound-disruption stress test'}
					</Button>
					{#if !comboRefReady && !combinedScenarioLoading}
						<p class="text-muted-foreground text-xs">
							Fill in a reference point for all {OBJ_KEYS.length} objectives to enable the run.
						</p>
					{/if}

					{#if combinedScenarioError}
						<div class="rounded-md border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-800">
							{combinedScenarioError}
						</div>
					{/if}

					{#if combinedScenario}
						<div class="overflow-x-auto">
							<p class="mb-2 text-sm font-medium">
								Worst compound-disruption case vs. single-disruption worst case
							</p>
							<p class="text-muted-foreground mb-3 text-xs">
								A large gap means compound disruptions expose real additional risk that
								single-disruption robustness testing misses entirely.
							</p>
							<Table.Root>
								<Table.Header>
									<Table.Row>
										<Table.Head>Design</Table.Head>
										{#each OBJ_KEYS as obj}
											<Table.Head>{objLabel(obj)}: single / compound / gap</Table.Head>
										{/each}
									</Table.Row>
								</Table.Header>
								<Table.Body>
									{#each combinedScenario.summary as row (row.design_id)}
										<Table.Row>
											<Table.Cell>
												<span
													class="inline-block h-3 w-3 rounded-full align-middle"
													style={`background-color:${comboDesignColor(row.design_id)}`}
												></span>
												Solution {row.solution_number} (design {row.design_id})
											</Table.Cell>
											{#each OBJ_KEYS as obj}
												{@const combo = row[`${obj}_combo_worst`]}
												{@const single = row[`${obj}_single_robust`]}
												{@const gap = row[`${obj}_gap`]}
												{@const worstCombo = row[`${obj}_worst_combo`]}
												<Table.Cell>
													{#if combo === null || combo === undefined}
														no feasible combined scenario
													{:else}
														{fmt(Number(single))} / {fmt(Number(combo))} / {Number(gap) >= 0
															? '+'
															: ''}{fmt(Number(gap))}
														<span class="text-muted-foreground block text-xs">worst: {worstCombo}</span>
													{/if}
												</Table.Cell>
											{/each}
										</Table.Row>
									{/each}
								</Table.Body>
							</Table.Root>
						</div>

						<div>
							<p class="mb-1 text-sm font-medium">Trade-off view — one line per (design, combined scenario) pair</p>
							<p class="text-muted-foreground mb-2 text-xs">
								Lines are colored by design (matching the "Design" swatches in the table above). The
								rightmost axis, <strong>Combined scenario #</strong>, tells you which pairwise
								combination that line belongs to — hover a line for its full name, or look it up in
								the key below. The other objective axes are each in their own units, so read them as
								separate trade-offs, not on a common scale.
							</p>
							<div style="height: 380px;">
								<ParallelCoordinates
									data={comboChartRows}
									dimensions={comboChartDimensions}
									colorByIndex={comboColorByIndex}
									lineLabels={comboChartLineLabels}
								/>
							</div>
							<details class="text-muted-foreground mt-2 text-xs">
								<summary class="cursor-pointer select-none">Combined scenario # key ({combinedScenario.combo_names.length})</summary>
								<ol class="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 md:grid-cols-3">
									{#each combinedScenario.combo_names as combo, i}
										<li>{i + 1} → {combo}</li>
									{/each}
								</ol>
							</details>
						</div>

						<div class="space-y-6">
							<p class="text-sm font-medium">Compound-disruption performance table</p>
							<p class="text-muted-foreground text-xs">
								Rows = candidate designs, columns = the combined scenarios tested. Each cell is
								that row's design, re-optimized (capacities fixed) under that column's combined
								disruption, and shows the resulting value of the objective named in that table's
								heading. Large numbers are abbreviated — "-79.6M" means -79,600,000 — hover any
								cell to see the exact, unrounded value. "—" = infeasible:
								<strong>{comboTotalInfeasible} of {comboTotalPairs}</strong> (design, combined scenario) pairs
								are infeasible overall (the same pairs are infeasible no matter which objective's
								table you're looking at, since feasibility is a property of the pair, not the
								objective). The rightmost column and bottom row count infeasible combos per design
								and per combined scenario.
							</p>
							{#each OBJ_KEYS as obj}
								<div class="overflow-x-auto">
									<p class="mb-1 text-xs font-medium">{objLabel(obj)}</p>
									<table class="border-collapse text-xs">
										<thead>
											<tr>
												<th class="p-1 text-left"></th>
												{#each combinedScenario.combo_names as combo}
													<th class="p-1 text-left font-normal whitespace-nowrap">{combo}</th>
												{/each}
												<th class="p-1 text-left font-medium whitespace-nowrap">Infeasible</th>
											</tr>
										</thead>
										<tbody>
											{#each comboDesignIds as designId}
												<tr>
													<td class="p-1 pr-3 font-medium whitespace-nowrap">
														Sol {combinedScenario.summary.find((s) => s.design_id === designId)?.solution_number ??
															designId} (id {designId})
													</td>
													{#each combinedScenario.combo_names as combo}
														{@const v = comboValue(designId, combo, obj)}
														<td
															class="h-6 w-16 border border-gray-200 text-center tabular-nums"
															title={v === null ? 'infeasible' : fmt(v)}
														>
															{v === null ? '—' : fmtCompact(v)}
														</td>
													{/each}
													<td class="p-1 pl-3 font-medium whitespace-nowrap">
														{comboInfeasibleByDesign[designId] ?? 0} / {combinedScenario.combo_names.length}
													</td>
												</tr>
											{/each}
											<tr class="border-t">
												<td class="p-1 pr-3 font-medium whitespace-nowrap">Infeasible</td>
												{#each combinedScenario.combo_names as combo}
													<td class="p-1 text-center whitespace-nowrap">
														{comboInfeasibleByCombo[combo] ?? 0} / {comboDesignIds.length}
													</td>
												{/each}
												<td class="p-1 pl-3 font-medium whitespace-nowrap">
													{comboTotalInfeasible} / {comboTotalPairs}
												</td>
											</tr>
										</tbody>
									</table>
								</div>
							{/each}
						</div>

						{#if combinedScenario.supports_superadditivity}
							<div class="space-y-6">
								<p class="text-sm font-medium">Super-additivity</p>
								<p class="text-muted-foreground text-xs">
									Does a disruption pair hit harder than its two disruptions would separately? Each
									cell shows <strong>super-additivity</strong> = combined − (baseline + ΔA + ΔB),
									i.e. how far the combined outcome runs beyond the sum of its two single-disruption
									effects — both the number and the color encode this same value now.
									<span class="font-medium text-red-700">Red / positive = super-additive</span> —
									the pair synergizes worse than expected, the interaction risk this test exists to
									catch. <span class="font-medium text-blue-700">Blue / negative = sub-additive</span>
									— the disruptions overlap or saturate, so the pair does better than the naive
									sum. Hover a cell for the underlying raw compound value. Gray = the pair, its two
									single-disruption reference points, or the baseline weren't all feasible.
									Objectives that don't vary by scenario (e.g. a first-stage-only investment cost)
									have no interaction to show and are omitted here.
								</p>
								{#each superaddObjKeys as obj}
									<div class="overflow-x-auto">
										<p class="mb-1 text-xs font-medium">{objLabel(obj)}</p>
										<table class="border-collapse text-xs">
											<thead>
												<tr>
													<th class="p-1 text-left"></th>
													{#each combinedScenario.combo_names as combo}
														<th class="p-1 text-left font-normal whitespace-nowrap">{combo}</th>
													{/each}
												</tr>
											</thead>
											<tbody>
												{#each comboDesignIds as designId}
													<tr>
														<td class="p-1 pr-3 font-medium whitespace-nowrap">
															Sol {combinedScenario.summary.find((s) => s.design_id === designId)
																?.solution_number ?? designId} (id {designId})
														</td>
														{#each combinedScenario.combo_names as combo}
															{@const v = comboValue(designId, combo, obj)}
															{@const sa = comboSuperaddValue(designId, combo, obj)}
															<td
																class="h-6 w-16 border border-gray-200 text-center tabular-nums"
																style={`background-color:${superaddColor(sa, comboSuperaddRanges[obj])}`}
																title={sa === null
																	? 'infeasible / no reference data'
																	: `super-additivity: ${fmt(sa)}, raw compound value: ${v === null ? 'n/a' : fmt(v)}`}
															>
																{sa === null ? '—' : `${sa >= 0 ? '+' : ''}${fmtCompact(sa)}`}
															</td>
														{/each}
													</tr>
												{/each}
											</tbody>
										</table>
									</div>
								{/each}
							</div>
						{/if}

						{#if singleDisruptionNames.length > 0}
							<div class="space-y-4 border-t pt-6">
								<p class="text-sm font-medium">Compare single vs. combined disruption</p>
								<p class="text-muted-foreground text-xs">
									How does a design's worst-case performance change under disruption A alone, B
									alone, and the two combined? Pick a design and any two disruptions to compare.
								</p>
								{#if strategicDesigns}
									<div>
										<Label for="triplet-design-select">Design ID</Label>
										<select
											id="triplet-design-select"
											class="border-input mt-1 block w-40 rounded-md border bg-transparent px-3 py-1.5 text-sm shadow-xs"
											bind:value={selectedDesignId}
										>
											{#each strategicDesigns.designs as d}
												<option value={d.design_id}>
													Design {d.design_id} (Solution {d.solution_number})
												</option>
											{/each}
										</select>
									</div>
								{/if}
								{#if !selectedDesign}
									<p class="text-muted-foreground text-xs">Select a design above to compare it here.</p>
								{:else}
									<div class="grid grid-cols-2 gap-4 md:w-1/2">
										<div>
											<Label for="triplet-a">Disruption A</Label>
											<select
												id="triplet-a"
												class="border-input mt-1 block w-full rounded-md border bg-transparent px-3 py-1.5 text-sm shadow-xs"
												bind:value={tripletA}
											>
												{#each singleDisruptionNames as name}
													<option value={name}>{name}</option>
												{/each}
											</select>
										</div>
										<div>
											<Label for="triplet-b">Disruption B</Label>
											<select
												id="triplet-b"
												class="border-input mt-1 block w-full rounded-md border bg-transparent px-3 py-1.5 text-sm shadow-xs"
												bind:value={tripletB}
											>
												{#each singleDisruptionNames as name}
													<option value={name}>{name}</option>
												{/each}
											</select>
										</div>
									</div>
									{#if !selectedDesignTested}
										<p class="text-muted-foreground text-xs">
											Design {selectedDesign.design_id} wasn't tested by the compound-disruption
											stress test above (only the wish list, or explicitly requested designs, are
											tested) — nothing was solved for it, so there's nothing to compare yet. Add
											it to the wish list and re-run the stress test to compare it here.
										</p>
									{:else if tripletLines.length > 0}
										<div style="height: 340px;">
											<ParallelCoordinates
												data={tripletChartRows}
												dimensions={tripletDimensions}
												colorByIndex={tripletColorByIndex}
												lineLabels={tripletLineLabels}
											/>
										</div>
									{:else}
										<p class="text-muted-foreground text-xs">
											{tripletA} and {tripletB} were tested for this design, but the solve was
											infeasible for at least one of A alone, B alone, or the combined pair.
										</p>
									{/if}
								{/if}
							</div>
						{/if}
					{/if}
				</Card.Content>
			</Card.Root>
		{/if}

		<!-- Per-objective best-worst ranges for this round's matched designs. Split out of the
		     "Matched solutions" card and parked at the bottom of the page on purpose: up there it
		     pushed the wish-list buttons off the right edge behind a horizontal scrollbar, and the
		     DM's decision at that point is "do I want to keep this design?", not "what are its
		     eight raw envelope endpoints?". The numbers are still worth having for analysis, so
		     they keep their own table down here rather than being dropped. -->
		{#if current && viewedEntry?.solutions && viewedEntry.solutions.length > 0}
			<Card.Root>
				<Card.Header>
					<Card.Title>Matched solutions — objective ranges</Card.Title>
					<Card.Description>
						The same {viewedEntry.solutions.length} design(s) shown in "Matched solutions" above, with
						each one's best and worst case per objective across all scenarios. Reference detail for
						analysis — the trade-off and per-scenario views above show the same envelopes visually.
					</Card.Description>
				</Card.Header>
				<Card.Content>
					<div class="overflow-x-auto">
						<Table.Root>
							<Table.Header>
								<Table.Row>
									<Table.Head>Solution</Table.Head>
									<Table.Head>Design ID</Table.Head>
									<Table.Head>Matched by</Table.Head>
									{#each OBJ_KEYS as obj (obj)}
										<Table.Head>{objLabel(obj)} (best–worst)</Table.Head>
									{/each}
								</Table.Row>
							</Table.Header>
							<Table.Body>
								{#each viewedEntry.solutions as sol, i (sol.design_id)}
									<Table.Row>
										<Table.Cell>
											<!-- Same focus control as the table above, so clicking a row here also
											     highlights that solution in the charts. -->
											<button
												type="button"
												class="hover:underline"
												class:font-semibold={selectedSolutionIdx === i}
												title="Focus this solution in the charts above"
												onclick={() => toggleSolutionSelection(i)}
											>
												<span
													class="inline-block h-3 w-3 rounded-full align-middle"
													style={`background-color:${solutionColor(i)}`}
												></span>
												Solution {sol.solution_number}
											</button>
											{#if sol.repeat}
												<Badge variant="outline" class="ml-1">repeat</Badge>
											{/if}
										</Table.Cell>
										<Table.Cell>{sol.design_id}</Table.Cell>
										<Table.Cell>
											<div class="flex flex-wrap gap-1">
												{#each sol.matched_by as name (name)}
													<Badge variant="secondary">{name}</Badge>
												{/each}
											</div>
										</Table.Cell>
										{#each OBJ_KEYS as obj (obj)}
											<Table.Cell>{fmt(sol.best_case[obj])} – {fmt(sol.worst_case[obj])}</Table.Cell>
										{/each}
									</Table.Row>
								{/each}
							</Table.Body>
						</Table.Root>
					</div>
				</Card.Content>
			</Card.Root>

			<Card.Root>
				<Card.Header>
					<Card.Title>Strategic decisions</Card.Title>
					<Card.Description>
						What a matched solution actually builds — the first-stage capacity decisions behind the
						performance shown above, against the capacity that already exists. Pick a design, or
						focus a solution in the charts above and this follows it.
					</Card.Description>
				</Card.Header>
				<Card.Content class="space-y-4">
					{#if strategicDesigns}
						<div>
							<Label for="strategic-design-select">Design ID</Label>
							<select
								id="strategic-design-select"
								class="border-input mt-1 block w-64 rounded-md border bg-transparent px-3 py-1.5 text-sm shadow-xs"
								bind:value={strategicCardDesignId}
							>
								{#each strategicDesignOptions as opt (opt.designId)}
									<option value={opt.designId}>
										Design {opt.designId} — Solution {opt.solutionNumber}
									</option>
								{/each}
							</select>

							{#if strategicCardCapacityRows.length > 0}
								<div class="mt-4 overflow-x-auto">
									<p class="mb-2 text-sm font-medium">
										Design {strategicCardDesignId}{#if strategicCardSolution}
											&nbsp;(Solution {strategicCardSolution.solutionNumber}){/if} — capacities
										and change relative to the existing system
									</p>
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
											{#each strategicCardCapacityRows as row (row.sym)}
												<Table.Row>
													<Table.Cell>{row.component}</Table.Cell>
													<Table.Cell>{row.unit}</Table.Cell>
													<Table.Cell>{fmt(row.existing)}</Table.Cell>
													<Table.Cell>{fmt(row.added)}</Table.Cell>
													<Table.Cell>{fmt(row.total)}</Table.Cell>
													<Table.Cell>
														{row.changePct === null
															? '—'
															: `${row.changePct >= 0 ? '+' : ''}${row.changePct.toFixed(1)}%`}
													</Table.Cell>
												</Table.Row>
											{/each}
										</Table.Body>
									</Table.Root>
								</div>
							{/if}
						</div>
					{:else if strategicLoading}
						<p class="text-muted-foreground py-4 text-sm">Loading strategic designs…</p>
					{:else if strategicError}
						<div class="rounded-md border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-800">
							{strategicError}
						</div>
					{/if}
				</Card.Content>
			</Card.Root>
		{/if}

		{#if strategicDesigns && strategicDesigns.designs.length > 0}
			<Card.Root>
				<Card.Header>
					<Card.Title>Strategic Design Explorer</Card.Title>
					<Card.Description>
						Browse every unique strategic design discovered this session ({strategicDesigns.designs
							.length}) — first-stage capacities and worst-case robust objectives. Lines are colored
						by which scalarizer variant discovered that design. Drag on the Design ID axis to narrow
						the range.
					</Card.Description>
				</Card.Header>
				<Card.Content class="space-y-4">
					<div class="flex flex-wrap gap-3 text-xs">
						{#each scalarizersPresent as sc}
							<span class="flex items-center gap-1.5">
								<span
									class="inline-block h-3 w-3 rounded-full"
									style={`background-color:${scalarizerColorByName[sc] ?? '#888'}`}
								></span>
								{scalarizerLabelByName[sc] ?? sc}
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
								<option value={d.design_id}>
									Design {d.design_id} (Solution {d.solution_number})
								</option>
							{/each}
						</select>

						{#if selectedDesign}
							<p class="text-muted-foreground mt-2 text-xs">
								Discovered by <strong>{scalarizerLabelByName[selectedDesign.scalarizer] ?? selectedDesign.scalarizer}</strong>
								{#if selectedDesign.first_iteration}
									(iteration {selectedDesign.first_iteration})
								{/if}
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
								<p class="mb-2 text-sm font-medium">Worst-case robust objectives (the quantity actually optimized)</p>
								<Table.Root>
									<Table.Header>
										<Table.Row>
											<Table.Head>Objective</Table.Head>
											<Table.Head>Worst-case (robust)</Table.Head>
											<Table.Head>Worst-case ideal</Table.Head>
											<Table.Head>Worst-case nadir</Table.Head>
										</Table.Row>
									</Table.Header>
									<Table.Body>
										{#each selectedRobustRows as row}
											<Table.Row>
												<Table.Cell>{row.label}</Table.Cell>
												<Table.Cell>{fmt(row.worstCase)}</Table.Cell>
												<Table.Cell>{fmt(row.ideal)}</Table.Cell>
												<Table.Cell>{fmt(row.nadir)}</Table.Cell>
											</Table.Row>
										{/each}
									</Table.Body>
								</Table.Root>
							</div>

							<div class="mt-4 overflow-x-auto">
								<p class="mb-2 text-sm font-medium">Performance across all {scenarioCount} scenarios</p>
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
	{/if}
</div>
