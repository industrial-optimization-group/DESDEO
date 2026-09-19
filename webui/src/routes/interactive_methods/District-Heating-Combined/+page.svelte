<script lang="ts">
	/**
	 * JINA (interactive multi-scenario) — reference-point matching with no worst-case
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
	import * as Tabs from '$lib/components/ui/tabs';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Badge } from '$lib/components/ui/badge';
	import ParallelCoordinates from '$lib/components/visualizations/parallel-coordinates/parallel-coordinates.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import { create_session } from '../../methods/sessions/handler';
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
	/** One value per base objective, used to fill that objective's whole row at once. Holds
	 *  whatever the active mode expects — a raw value, a percent, or a change in points. */
	let rowFill: Record<string, number | null> = $state({});

	// --- How the reference point is entered ------------------------------------------------------
	// Three ways to say the same thing, ported from the two-stage robustness method so a DM moving
	// between the two reads them identically. `levels` stays the raw store; the other two modes
	// keep their own numbers and are converted to raw only when the round is actually solved.
	let refMode: 'raw' | 'percent' | 'delta' = $state('raw');
	/** Per cell, on the 0 = nadir … 100 = ideal scale. */
	let percentLevels: Record<string, number | null> = $state({});
	/** Per cell, how far to move off the previous iteration's aspiration, as a percentage of that
	 *  aspiration's own value. Signed: +10 demands 10% better than last round, -10 concedes 10%
	 *  worse. */
	let adjustPercent: Record<string, number | null> = $state({});

	/** Where a raw value sits on its cell's 0 = nadir … 100 = ideal scale. Null when it cannot be
	 *  placed: no value, or a degenerate cell whose ideal and nadir coincide. Works whichever way
	 *  the objective runs, since it interpolates between the two named ends rather than assuming
	 *  ideal is the larger. */
	function percentOfCell(cell: CombinedCell, value: number | null | undefined): number | null {
		if (value === null || value === undefined || !Number.isFinite(value)) return null;
		if (cell.ideal === cell.nadir) return null;
		return (100 * ((value as number) - cell.nadir)) / (cell.ideal - cell.nadir);
	}

	function rawFromPercent(cell: CombinedCell, pct: number): number {
		return cell.nadir + (Math.max(0, Math.min(100, pct)) / 100) * (cell.ideal - cell.nadir);
	}

	/** The previous round's raw aspiration per cell — what a percentage change is measured from. */
	let previousRaw = $derived.by(() => {
		const out: Record<string, number | null> = {};
		for (const c of cells) {
			const v = current?.reference_point?.[c.symbol];
			out[c.symbol] = v === undefined || v === null || !Number.isFinite(v) ? null : v;
		}
		return out;
	});

	let hasPreviousReferencePoint = $derived.by(
		() => !!current && current.iteration_number > 0 && cells.some((c) => previousRaw[c.symbol] !== null)
	);

	/** What a percentage change is measured against: last round's aspiration, or — before any
	 *  round exists to compare with — the middle of the cell's own span. */
	function adjustBase(cell: CombinedCell): number {
		const prev = previousRaw[cell.symbol];
		return prev === null ? (cell.ideal + cell.nadir) / 2 : prev;
	}

	/** Move a cell's aspiration by `percent` of its own magnitude: toward the ideal for a positive
	 *  percent, away from it for a negative one.
	 *
	 *  Direction has to be derived rather than assumed. These objectives are all minimised, but
	 *  their values are not all positive — an operational cost sits at -31,536,203 with an even
	 *  more negative ideal, so "10% better" there means 10% *larger* in magnitude, while for CO2
	 *  it means 10% smaller. Comparing against the cell's own ideal is what gets both right.
	 *
	 *  The result is clamped to the cell's span so a large step cannot ask for something past the
	 *  ideal, which no design could ever reach.
	 */
	function adjustedRaw(cell: CombinedCell, percent: number): number {
		const base = adjustBase(cell);
		// When the base already sits exactly at the ideal, "toward the ideal" has no direction of
		// its own; fall back to the axis orientation so a negative percent can still relax it.
		const towardIdeal =
			cell.ideal > base ? 1 : cell.ideal < base ? -1 : cell.nadir > cell.ideal ? -1 : 1;
		const candidate = base + ((percent || 0) / 100) * Math.abs(base) * towardIdeal;
		const lo = Math.min(cell.ideal, cell.nadir);
		const hi = Math.max(cell.ideal, cell.nadir);
		return Math.max(lo, Math.min(hi, candidate));
	}

	/** A percentage of zero is zero, so a cell whose previous aspiration was exactly 0 cannot be
	 *  moved by this mode at all. Worth flagging in place: many of these cells sit at 0 because
	 *  that *is* their ideal, and no percentage can better the best attainable value. */
	function adjustIsStuck(cell: CombinedCell): boolean {
		return Math.abs(adjustBase(cell)) < 1e-12;
	}

	let stuckCellCount = $derived.by(
		() => (refMode === 'delta' ? cells.filter((c) => adjustIsStuck(c)).length : 0)
	);

	/** What percentage change would land this cell on `raw`? The inverse of `adjustedRaw`, used
	 *  when switching into the % change tab. Null when the base is 0, where no percentage can
	 *  produce anything other than 0. */
	function percentToReach(cell: CombinedCell, raw: number): number | null {
		const base = adjustBase(cell);
		if (Math.abs(base) < 1e-12) return null;
		const towardIdeal =
			cell.ideal > base ? 1 : cell.ideal < base ? -1 : cell.nadir > cell.ideal ? -1 : 1;
		return (100 * (raw - base)) / (Math.abs(base) * towardIdeal);
	}

	/** Switch input mode, carrying the targets across rather than leaving the new tab empty.
	 *
	 *  The three tabs are three ways of writing the same 25 numbers, so switching should change
	 *  the notation and not the request. Converting through the raw reference point keeps that
	 *  true: whatever is on screen means the same thing before and after the switch.
	 *
	 *  Nothing is carried when the current tab is incomplete — there is no reference point to
	 *  convert — so a half-filled grid stays half-filled rather than being filled in with guesses.
	 */
	function switchRefMode(next: 'raw' | 'percent' | 'delta') {
		if (next === refMode) return;
		const effective = missingCount === 0 && cells.length > 0 ? referencePointFromInputs() : null;
		refMode = next;
		if (effective === null) return;

		for (const c of cells) {
			const raw = effective[c.symbol];
			if (raw === undefined || !Number.isFinite(raw)) continue;
			if (next === 'raw') {
				levels[c.symbol] = roundForInput(raw);
			} else if (next === 'percent') {
				const pct = percentOfCell(c, raw);
				percentLevels[c.symbol] = pct === null ? null : roundForInput(pct);
			} else {
				const pct = percentToReach(c, raw);
				adjustPercent[c.symbol] = pct === null ? null : roundForInput(pct);
			}
		}
	}

	/** The raw reference point the solve actually receives, whichever mode it was entered in. */
	function referencePointFromInputs(): Record<string, number> {
		const out: Record<string, number> = {};
		for (const c of cells) {
			if (refMode === 'raw') {
				out[c.symbol] = levels[c.symbol] as number;
			} else if (refMode === 'percent') {
				out[c.symbol] = rawFromPercent(c, Number(percentLevels[c.symbol]));
			} else {
				out[c.symbol] = adjustedRaw(c, Number(adjustPercent[c.symbol]) || 0);
			}
		}
		return out;
	}
	let note = $state('');

	// How many designs to show per round. Each scalarizer variant solves regardless — this trims
	// what comes back, so a trimmed design is still in the design list and can still be
	// wish-listed. Defaults to every variant.
	let maxSolutions: number | null = $state(null);

	/** Variants this problem has: balanced + one per objective. The ceiling on distinct designs. */
	let scalarizerCount = $derived.by(() => grid?.scalarizer_count ?? 0);

	// Which round the result cards show. The session tree is oldest first, so the last entry is
	// the newest; -1 means nothing loaded yet. Only the *display* follows this — the aspiration
	// inputs, wish list and design list always belong to the session as a whole, so browsing an
	// earlier round never changes what the next solve would do.
	let viewedIterationIndex = $state(-1);

	let viewedEntry: CombinedSessionTreeEntry | null = $derived.by(
		() => sessionTree[viewedIterationIndex] ?? null
	);

	let isViewingLatest = $derived(
		sessionTree.length === 0 || viewedIterationIndex >= sessionTree.length - 1
	);

	function goToPreviousIteration() {
		if (viewedIterationIndex > 0) viewedIterationIndex -= 1;
	}

	function goToNextIteration() {
		if (viewedIterationIndex < sessionTree.length - 1) viewedIterationIndex += 1;
	}

	function goToLatestIteration() {
		viewedIterationIndex = sessionTree.length - 1;
	}

	/** Every design the *viewed* round produced. Falls back to the single design for rounds
	 *  recorded before this method solved several variants, and to the live response before the
	 *  session tree has arrived. */
	let solutionsThisRound: CombinedSolution[] = $derived.by(() => {
		const entry = viewedEntry;
		if (entry) {
			const list = entry.solutions ?? [];
			if (list.length > 0) return list;
			return entry.solution ? [entry.solution] : [];
		}
		const list = current?.solutions ?? [];
		if (list.length > 0) return list;
		const single = current?.solution;
		return single ? [single] : [];
	});

	/** The iteration number shown on the result cards — the viewed round's, not always the last. */
	let viewedIterationNumber = $derived.by(
		() => viewedEntry?.iteration_number ?? current?.iteration_number ?? 0
	);

	/** Turn a scalarizer name into something readable, using this problem's own objective labels
	 *  rather than the raw symbol. */
	function scalarizerLabel(name: string): string {
		if (name === 'balanced') return 'Balanced';
		const sym = name.startsWith('emphasize_') ? name.slice('emphasize_'.length) : name;
		return `Emphasize ${objectiveLabels[sym] ?? sym}`;
	}

	/** True when every cell still sits at its ideal. The emphasis shift is
	 *  `ideal + (g - ideal) / factor`, so with `g == ideal` there is no gap to close: every
	 *  variant solves the identical problem and the round yields exactly one design however many
	 *  are asked for. Worth saying out loud rather than letting it look like a bug. */
	let referencePointAtIdeals = $derived.by(() => {
		if (cells.length === 0 || missingCount > 0) return false;
		const effective = referencePointFromInputs();
		return cells.every((c) => {
			const v = effective[c.symbol];
			if (v === null || v === undefined || !Number.isFinite(v)) return false;
			const span = Math.abs(c.nadir - c.ideal) || 1;
			return Math.abs(v - c.ideal) / span < 1e-9;
		});
	});

	/** Round a value before it goes into an input box.
	 *
	 *  A payoff-table ideal arrives as a full double (-31536203.386121...), and a number input
	 *  shows every digit of it. Two decimals is far below any resolution these quantities are
	 *  decided at - euros, tonnes and MWh in the millions and thousands - so this only changes
	 *  what the decision maker reads, never what the choice means.
	 *
	 *  Applied wherever a value is written into a box: seeded from ideals, restored from a saved
	 *  round, copied by a row fill, or converted when the input tab changes.
	 */
	function roundForInput(v: number): number {
		return Number.isFinite(v) ? Math.round(v * 100) / 100 : v;
	}

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
	let missingCount = $derived.by(() => {
		// A blank in change mode means "leave this one where it was", which is a real answer — so
		// only the two absolute modes can be incomplete.
		if (refMode === 'delta') return 0;
		const store = refMode === 'raw' ? levels : percentLevels;
		return cells.filter((c) => {
			const v = store[c.symbol];
			return v === null || v === undefined || !Number.isFinite(v);
		}).length;
	});
	let canSolve = $derived(cells.length > 0 && missingCount === 0 && !solving);

	/** The store the inputs are bound to right now. */
	function activeStore(): Record<string, number | null> {
		if (refMode === 'raw') return levels;
		if (refMode === 'percent') return percentLevels;
		return adjustPercent;
	}

	function applyRowFill(objSymbol: string) {
		const v = rowFill[objSymbol];
		if (v === null || v === undefined || !Number.isFinite(v)) return;
		const rounded = roundForInput(Number(v));
		const store = activeStore();
		for (const c of cells) {
			if (c.obj_symbol === objSymbol) store[c.symbol] = rounded;
		}
	}

	/** Apply every row-fill box that has a value, in one go.
	 *
	 *  Blank boxes are skipped rather than treated as zero, so filling two objectives and leaving
	 *  the others empty leaves those others' cells exactly as the DM last set them.
	 */
	function applyAllRowFills() {
		for (const obj of objectives) applyRowFill(obj);
	}

	/** Nothing to apply when every box is empty — the button would silently do nothing. */
	let rowFillCount = $derived.by(
		() => objectives.filter((obj) => Number.isFinite(Number(rowFill[obj]))).length
	);

	/** Fill everything with each cell's own ideal — the notebook's default template. Not jointly
	 *  attainable (each ideal assumes the investment is tailored to that one scenario), which is
	 *  the point: a starting position to relax from, not a proposal. */
	function fillWithIdeals() {
		// The same neutral starting point expressed in whichever mode is active: each cell's own
		// ideal, 100% of range, or no change at all.
		if (refMode === 'raw') {
			for (const c of cells) levels[c.symbol] = roundForInput(c.ideal);
			for (const o of objectives) {
				const first = cells.find((c) => c.obj_symbol === o);
				rowFill[o] = first ? roundForInput(first.ideal) : null;
			}
		} else if (refMode === 'percent') {
			for (const c of cells) percentLevels[c.symbol] = 100;
			for (const o of objectives) rowFill[o] = 100;
		} else {
			for (const c of cells) adjustPercent[c.symbol] = 0;
			for (const o of objectives) rowFill[o] = 0;
		}
	}

	let resetLabel = $derived(
		refMode === 'raw'
			? 'Reset to ideals'
			: refMode === 'percent'
				? 'Set all to 100%'
				: 'Clear changes'
	);

	// --- Designs discovered this session --------------------------------------------------------
	// One solve per round means designs arrive one at a time, and the same build can resurface in a
	// later round (the backend gives it back its original id). Deduplicating by design_id here is
	// what keeps the charts, the wish list and the domain criterion from counting it twice.
	// --- Strategic decisions ---------------------------------------------------------------------
	// What a design actually builds. The decision variables are capacity *added*, so the row shows
	// it against `strategic_axis_max` — the problem's existing capacity for that component under
	// the district heating convention — and the resulting total.
	let strategicSymbols = $derived.by(() => grid?.strategic_symbols ?? []);

	function existingCapacity(sym: string): number | null {
		const v = grid?.strategic_axis_max?.[sym];
		return v === undefined || v === null || !Number.isFinite(v) ? null : v;
	}

	/** One row per strategic variable for a design: what exists, what this design adds, the total,
	 *  and the addition as a percentage of what exists.
	 *
	 *  `changePct` is null where there is nothing to compare against — a component built from zero
	 *  has no meaningful percentage increase — and `existing`/`total` are null for an unbounded
	 *  variable, where the convention does not apply and only the decision itself is meaningful.
	 */
	function capacityRowsFor(designId: number | null) {
		if (designId === null) return [];
		const entry = designs.find((d) => d.solution.design_id === designId);
		if (!entry) return [];
		const vals = entry.solution.strategic_values ?? {};
		return strategicSymbols.map((sym) => {
			const existing = existingCapacity(sym);
			const added = Number(vals[sym] ?? 0);
			return {
				sym,
				component: grid?.strategic_components?.[sym] ?? grid?.strategic_labels?.[sym] ?? sym,
				unit: grid?.strategic_units?.[sym] ?? '',
				existing,
				added,
				total: existing === null ? null : existing + added,
				changePct: existing !== null && existing !== 0 ? (100 * added) / existing : null
			};
		});
	}

	let strategicCardRows = $derived.by(() => capacityRowsFor(strategicCardDesignId));

	/** The chosen design's entry, carrying which variants found it and when. */
	let strategicCardEntry = $derived.by(() =>
		strategicCardDesignId === null
			? null
			: (designs.find((d) => d.solution.design_id === strategicCardDesignId) ?? null)
	);

	/** How the chosen design performs in each scenario. Free: an iteration already stores this
	 *  breakdown per design, so no extra solve is needed to show it. */
	let strategicCardBreakdown = $derived.by(() => {
		if (strategicCardDesignId === null) return [];
		const entry = designs.find((d) => d.solution.design_id === strategicCardDesignId);
		return entry?.solution.breakdown ?? [];
	});

	let strategicCardSolutionNumber = $derived.by(() =>
		strategicCardDesignId === null ? null : solutionNumberFor(strategicCardDesignId)
	);

	// Follow the chart focus, but never fight a manual pick: the last synced focus is tracked
	// explicitly so choosing a design in the selector cannot be immediately undone by this.
	let lastSyncedDesignFocus: number | null | undefined = undefined;
	$effect(() => {
		const focused = selectedDesignIds.length > 0 ? selectedDesignIds[selectedDesignIds.length - 1] : null;
		const available = designs;
		if (focused !== lastSyncedDesignFocus) {
			lastSyncedDesignFocus = focused;
			if (focused !== null) {
				strategicCardDesignId = focused;
				return;
			}
		}
		// Nothing focused yet, or the selected design vanished with a new session.
		if (
			available.length > 0 &&
			(strategicCardDesignId === null ||
				!available.some((d) => d.solution.design_id === strategicCardDesignId))
		) {
			strategicCardDesignId = available[0].solution.design_id;
		}
	});

	let designs = $derived.by(() => {
		const byId = new Map<number, { solution: CombinedSolution; iteration: number }>();
		for (const entry of sessionTree) {
			// A round can produce several designs now; older rounds carry only the single one.
			const sols = entry.solutions?.length ? entry.solutions : entry.solution ? [entry.solution] : [];
			for (const sol of sols) {
				if (!byId.has(sol.design_id)) {
					byId.set(sol.design_id, { solution: sol, iteration: entry.iteration_number });
				}
			}
		}
		return [...byId.values()].sort((a, b) => a.solution.solution_number - b.solution.solution_number);
	});

	// Several designs can be focused at once — comparing two or three against each other is the
	// whole point of the plot, and a single selection forced the DM to look at them one by one.
	// Empty means "no focus", which shows every design at full colour.
	let selectedDesignIds: number[] = $state([]);

	// --- What is expanded -------------------------------------------------------------------------
	// Detail is opt-in: a round can produce five solutions, each with a 25-row table, and the
	// decision maker usually wants the headline first and one of them in full. Everything starts
	// collapsed; the summary line of each card stays visible so there is enough to decide on
	// without opening anything.
	let showPerScenario = $state(false);
	let showStrategic = $state(false);
	let showPerformance = $state(false);
	/** Expanded solution cards, by design id - several can be open at once for comparison. */
	let expandedSolutions: number[] = $state([]);

	function toggleSolutionDetail(designId: number) {
		expandedSolutions = expandedSolutions.includes(designId)
			? expandedSolutions.filter((id) => id !== designId)
			: [...expandedSolutions, designId];
	}

	/** The binding cells, named rather than counted: the count alone does not tell the decision
	 *  maker whether this solution is worth opening, but which targets are limiting it does. */
	function bindingLabels(sol: CombinedSolution): string[] {
		return sol.cell_results
			.filter((r) => r.binds)
			.map((r) => {
				const cell = cellsBySymbol[r.symbol];
				if (!cell) return r.symbol;
				return cell.shared ? cell.label : `${cell.label} · ${cell.scenario}`;
			});
	}

	/** The design the strategic-decisions card is showing. Follows whichever design was focused
	 *  most recently in the charts; picking one in the card's own selector overrides that until
	 *  the focus changes again. */
	let strategicCardDesignId: number | null = $state(null);

	function isDesignSelected(designId: number): boolean {
		return selectedDesignIds.includes(designId);
	}

	/** Full colour when nothing is focused, or when this design is one of the focused ones. */
	function isDesignHighlighted(designId: number): boolean {
		return selectedDesignIds.length === 0 || selectedDesignIds.includes(designId);
	}

	/** The permanent colour of a design.
	 *
	 *  Keyed off `solution_number` rather than the design's position in `designs`. Both are stable
	 *  today, since numbers are handed out in order and designs are never dropped, but the number
	 *  is stable *by definition* — it is assigned once and never reused — so the colour cannot
	 *  drift if that list is ever filtered or re-sorted.
	 */
	/** The solution number a design is known by, or null if it is not in this session's list. */
	function solutionNumberFor(designId: number): number | null {
		return designs.find((d) => d.solution.design_id === designId)?.solution.solution_number ?? null;
	}

	function designColor(designId: number): string {
		const entry = designs.find((d) => d.solution.design_id === designId);
		const n = entry?.solution.solution_number ?? designId;
		return SOLUTION_COLORS[Math.max(0, n - 1) % SOLUTION_COLORS.length];
	}

	function toggleDesignSelection(designId: number | null) {
		if (designId === null) {
			selectedDesignIds = [];
			return;
		}
		selectedDesignIds = selectedDesignIds.includes(designId)
			? selectedDesignIds.filter((id) => id !== designId)
			: [...selectedDesignIds, designId];
	}

	// Same defaults the chart ships with, minus the per-axis colour squares: lines here are
	// coloured by design, so a colour beside each objective name suggests a relationship that does
	// not exist.
	const CHART_OPTIONS = {
		showAxisLabels: true,
		highlightOnHover: true,
		strokeWidth: 2,
		opacity: 0.6,
		enableBrushing: true,
		showAxisColorSquares: false
	};

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

	// Short names for chart axes. An axis gets one narrow column, so the full metadata label
	// ("Operational Cost (EUR)") had to be truncated - and truncation ate the unit, which is the
	// part a decision maker most needs when reading a number off an axis. Shortening the *name*
	// instead leaves room to keep the unit intact. Anything unlisted falls back to a truncated
	// name, so this is an override rather than something a problem must supply.
	const SHORT_AXIS_NAMES: Record<string, string> = {
		'Operational Cost': 'Net op cost',
		'Investment Cost': 'Inv cost',
		'CO2 Emissions': 'CO2',
		'Unmet Heat': 'Unmet'
	};

	/** Unit per base objective, taken from the cells that measure it. */
	let objUnits = $derived.by(() => {
		const map: Record<string, string> = {};
		for (const c of cells) {
			if (c.unit && !map[c.obj_symbol]) map[c.obj_symbol] = c.unit;
		}
		return map;
	});

	/** The objective's name with no unit - for axes that are not in the objective's own unit. */
	/** Per objective, the span its cells cover and the narrower band common to all of them.
	 *
	 *  A row fill writes one number into every cell of an objective, so two ranges matter and they
	 *  are not the same. `lo..hi` is the union - the value sits inside at least one scenario's
	 *  span. `commonLo..commonHi` is the intersection - the value sits inside *every* scenario's
	 *  span, so no cell reports it as below its ideal or above its nadir. The intersection can be
	 *  empty: if one scenario's whole attainable span lies outside another's, no single number
	 *  works for both, and saying so is more useful than offering a range that does not exist.
	 */
	let objSpans = $derived.by(() => {
		const out: Record<
			string,
			{ lo: number; hi: number; commonLo: number; commonHi: number; hasCommon: boolean }
		> = {};
		for (const obj of objectives) {
			const objCells = cells.filter((c) => c.obj_symbol === obj);
			if (objCells.length === 0) continue;
			const los = objCells.map((c) => Math.min(c.ideal, c.nadir));
			const his = objCells.map((c) => Math.max(c.ideal, c.nadir));
			const commonLo = Math.max(...los);
			const commonHi = Math.min(...his);
			out[obj] = {
				lo: Math.min(...los),
				hi: Math.max(...his),
				commonLo,
				commonHi,
				hasCommon: commonLo <= commonHi
			};
		}
		return out;
	});

	function shortName(obj: string): string {
		const full = objectiveLabels[obj] ?? obj;
		const unit = objUnits[obj];
		const name = unit && full.endsWith(` (${unit})`) ? full.slice(0, full.length - unit.length - 3) : full;
		return SHORT_AXIS_NAMES[name] ?? (name.length > 14 ? `${name.slice(0, 13)}…` : name);
	}

	/** Name plus unit, for axes that carry the objective's own values. */
	function shortLabel(obj: string): string {
		const unit = objUnits[obj];
		return unit ? `${shortName(obj)} (${unit})` : shortName(obj);
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
			map[String(row)] = isDesignHighlighted(designId) ? designColor(designId) : MUTED_LINE_COLOR;
		});
		return map;
	});

	/** Which chart rows belong to a focused design.
	 *
	 *  Passing an array — even an empty one — is what puts the plot into multi-selection mode;
	 *  leaving it null makes the component manage a single selection internally, which is what
	 *  limited this to one solution at a time.
	 */
	let chartSelectedRows = $derived.by(() => {
		const rows: number[] = [];
		chartRowDesignId.forEach((designId, row) => {
			if (isDesignSelected(designId)) rows.push(row);
		});
		return rows;
	});

	/** Clicking a line toggles the design it belongs to, so a click means the same thing in the
	 *  plot as it does on the legend chips. */
	function toggleDesignByChartRow(row: number | null) {
		if (row === null) return;
		const designId = chartRowDesignId[row];
		if (designId !== undefined) toggleDesignSelection(designId);
	}

	function panelSelectedRows(designIdByRow: number[]): number[] {
		const rows: number[] = [];
		designIdByRow.forEach((designId, row) => {
			if (isDesignSelected(designId)) rows.push(row);
		});
		return rows;
	}

	function toggleDesignByPanelRow(designIdByRow: number[], row: number | null) {
		if (row === null) return;
		const designId = designIdByRow[row];
		if (designId !== undefined) toggleDesignSelection(designId);
	}

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
					`<strong>Solution ${d.solution.solution_number}</strong> — ${String(br.scenario)}<br>${values}`;
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
			map[String(row)] = isDesignHighlighted(designId) ? designColor(designId) : MUTED_LINE_COLOR;
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
				`<strong>Solution ${d.solution.solution_number}</strong><br>${values}`;
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
			// `shortName` (no unit) rather than `shortLabel`: the objective's own unit does not
			// apply to this axis.
			name: `${shortName(obj)} (max regret)`,
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
			map[String(i)] = `<strong>${name}</strong><br>${counts}`;
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
				for (const [sym, v] of Object.entries(current.reference_point)) {
					levels[sym] = roundForInput(Number(v));
				}
			}
			sessionTree = await getCombinedSessionTree(problemId, sessionId);
			goToLatestIteration();
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
			const reference_point = referencePointFromInputs();
			current = await runCombinedIteration({
				problem_id: problemId,
				...(sessionId != null ? { session_id: sessionId } : {}),
				reference_point,
				...(maxSolutions !== null ? { max_solutions: maxSolutions } : {}),
				...(note.trim() ? { note: note.trim() } : {})
			});
			wishList = current.wish_list ?? [];
			sessionTree = await getCombinedSessionTree(problemId, sessionId);
			// A fresh solve jumps to the round it just produced, wherever the DM was browsing.
			goToLatestIteration();
			if (current.solution) selectedDesignIds = [];
		} catch (e) {
			errorText = e instanceof Error ? e.message : 'Failed to run the iteration.';
		} finally {
			solving = false;
		}
	}

	// Starts a brand-new interactive session (shared with the sibling District Heating methods,
	// since all of them key their state off the same session id) and reloads this page against it.
	// Nothing from the old session is deleted — it is just no longer selected, and the DM can get
	// back to it from /methods/sessions.
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
			wishList = [];
			selectedDesignIds = [];
			analysis = null;
			analysisError = null;
			note = '';
			// Cleared so `loadAll` re-seeds them: the levels back to each cell's ideal, and the
			// thresholds back to the problem's defaults. Carrying the old session's numbers over
			// would make a "new session" silently start mid-conversation.
			levels = {};
			rowFill = {};
			domainThresholds = {};
			domainThresholdsSeeded = false;
			await loadAll();
		} catch (e) {
			errorText = e instanceof Error ? e.message : 'Failed to start a new session.';
		} finally {
			loading = false;
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
	<title>JINA (interactive multi-scenario) | DESDEO</title>
	<meta
		name="description"
		content="Reference-point matching with one aspiration level per (objective, scenario) cell — no worst-case aggregation."
	/>
</svelte:head>

<div class="container mx-auto max-w-6xl space-y-6 px-4 py-8">
	<div class="flex items-start justify-between gap-4">
		<div>
			<h1 class="text-3xl font-bold tracking-tight">JINA (interactive multi-scenario)</h1>
			<p class="text-muted-foreground mt-1 text-sm italic">
				JINA: Joint Infrastructure Network Adaptation
			</p>
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
		{#if problemId !== null}
			<Button
				variant="outline"
				size="sm"
				disabled={loading || solving}
				onclick={handleNewSession}
				class="shrink-0"
			>
				New session
			</Button>
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
							do not vary by scenario, set in the "Same level in every scenario" row{/if}. Each input shows its own attainable span — ideal is
						what that objective could reach if the investment were tailored to that scenario
						<em>alone</em>, so the ideals are not jointly reachable. Use the boxes below to give an
						objective the same level in all of its scenarios at once, then override only the cells
						you care about.
					</Card.Description>
				</Card.Header>
				<Card.Content class="space-y-4">
					<Tabs.Root
						value={refMode}
						onValueChange={(v) => switchRefMode(v as 'raw' | 'percent' | 'delta')}
					>
						<Tabs.List>
							<Tabs.Trigger value="raw">Raw values</Tabs.Trigger>
							<Tabs.Trigger value="percent">Percent of range</Tabs.Trigger>
							<Tabs.Trigger value="delta">% change from previous</Tabs.Trigger>
						</Tabs.List>
					</Tabs.Root>

					<p class="text-muted-foreground text-xs">
						Switching tabs converts what you have already entered, so the same targets carry across
						— only the notation changes.
						{#if refMode === 'raw'}
							Aspiration levels in each objective's own units. Every cell needs one.
						{:else if refMode === 'percent'}
							Each cell as a position on its own attainable span: <strong>100 = that cell's
							ideal</strong>, <strong>0 = its nadir</strong>. The spans differ per cell, so the same
							percentage means a different raw number in each scenario — which is the point: it
							states ambition, not a value.
						{:else if hasPreviousReferencePoint}
							Move each cell off the previous iteration's aspiration by a percentage
							<strong>of that value itself</strong>, in either direction.
							<strong>+10 demands 10% better</strong> than last round;
							<strong>−10 concedes 10% worse</strong>. Better means toward that cell's ideal, so a
							cost of −25,000,000 goes to −27,500,000 at +10% and −22,500,000 at −10%, while CO₂ of
							1,000 goes to 900 and 1,100. Results are clamped to the cell's span, so neither
							direction can ask for something outside what is attainable. Leave a cell blank to keep
							last round's value.
							{#if stuckCellCount > 0}
								<strong class="text-amber-700">
									{stuckCellCount} of {cells.length} cells had a previous value of exactly 0, and a
									percentage of 0 is 0 — those cannot be moved in this mode. Most are at 0 because
									0 <em>is</em> their ideal, so there is nothing better to ask for; use Raw or Percent
									of range to loosen them.
								</strong>
							{/if}
						{:else}
							No previous iteration to compare against yet, so a percentage applies to the
							<strong>middle of each cell's span</strong> instead. Run a round first if you want to
							steer from your own last reference point.
						{/if}
					</p>

					<div class="flex flex-wrap items-end gap-3 rounded-md border p-3">
						<span class="text-sm font-medium">Same level in every scenario:</span>
						{#each objectives as obj (obj)}
							{@const span = objSpans[obj]}
							<div>
								<Label for={`fill-${obj}`} class="text-xs">{objectiveLabels[obj] ?? obj}</Label>
								<Input
									id={`fill-${obj}`}
									type="number"
									class="w-40"
									bind:value={rowFill[obj]}
									placeholder={refMode === 'raw'
										? 'raw value'
										: refMode === 'percent'
											? '0-100'
											: '+/- %'}
								/>
								{#if refMode === 'raw' && span}
									<p class="text-muted-foreground mt-1 text-xs">
										{fmt(span.lo)} … {fmt(span.hi)}
									</p>
									{#if span.hasCommon}
										<p class="text-muted-foreground text-xs">
											fits every scenario: {fmt(span.commonLo)} … {fmt(span.commonHi)}
										</p>
									{:else}
										<p class="text-xs text-amber-700">
											no single value fits every scenario
										</p>
									{/if}
								{:else if refMode === 'percent'}
									<p class="text-muted-foreground mt-1 text-xs">0 … 100 (100 = ideal)</p>
								{:else}
									<p class="text-muted-foreground mt-1 text-xs">% better / worse than last round</p>
								{/if}
							</div>
						{/each}
						<Button size="sm" variant="outline" disabled={rowFillCount === 0} onclick={applyAllRowFills}>
							Apply
						</Button>
						<Button size="sm" variant="ghost" onclick={fillWithIdeals}>{resetLabel}</Button>
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
														{#if refMode === 'raw'}
															<Input
																type="number"
																class="w-40"
																bind:value={levels[cell.symbol]}
																placeholder="aspiration"
															/>
															<p class="text-muted-foreground mt-1 text-xs">
																ideal {fmt(cell.ideal)} · nadir {fmt(cell.nadir)}
															</p>
														{:else if refMode === 'percent'}
															<Input
																type="number"
																min="0"
																max="100"
																class="w-40"
																bind:value={percentLevels[cell.symbol]}
																placeholder="0-100"
															/>
															<p class="text-muted-foreground mt-1 text-xs">
																100 = {fmt(cell.ideal)} · 0 = {fmt(cell.nadir)}
															</p>
														{:else}
															<Input
																type="number"
																class="w-40"
																bind:value={adjustPercent[cell.symbol]}
																placeholder="+/- %"
																disabled={adjustIsStuck(cell)}
															/>
															<p class="text-muted-foreground mt-1 text-xs">
																{#if adjustIsStuck(cell)}
																	was 0 — a percentage of 0 cannot move it
																{:else}
																	was {fmt(adjustBase(cell))} → {fmt(
																		adjustedRaw(cell, Number(adjustPercent[cell.symbol]) || 0)
																	)}
																{/if}
															</p>
														{/if}
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

					<div class="flex flex-wrap items-end gap-3">
						{#if scalarizerCount > 1}
							<div>
								<Label for="combined-max-solutions" class="text-xs">Solutions to show</Label>
								<select
									id="combined-max-solutions"
									class="border-input bg-background h-9 w-40 rounded-md border px-3 py-1 text-sm shadow-sm"
									bind:value={maxSolutions}
								>
									<option value={null}>All ({scalarizerCount})</option>
									{#each Array.from({ length: scalarizerCount }, (_, i) => i + 1) as n (n)}
										<option value={n}>{n}</option>
									{/each}
								</select>
							</div>
						{/if}
						<div>
							<Label for="combined-note" class="text-xs">Note (optional)</Label>
							<Input id="combined-note" class="w-64" bind:value={note} placeholder="e.g. round 2" />
						</div>
						<Button disabled={!canSolve} onclick={handleSolve}>
							{solving ? 'Solving live (this can take a minute)…' : 'Run iteration'}
						</Button>
						{#if scalarizerCount > 1}
							<p class="text-muted-foreground w-full text-xs">
								Each round solves {scalarizerCount} scalarizer variants of the same problem: one
								using your aspiration levels as given, and one per objective that asks for more on
								that objective. Variants landing on the same build are shown once. Every variant
								solves regardless of this setting — it only trims what is displayed, so nothing is
								lost from the design list or wish list.
								{#if referencePointAtIdeals}
									<strong class="text-amber-700">
										Your levels are all still at their ideals, so the variants have nothing to
										shift and this round will return a single design. Relax some cells to see
										them differ.
									</strong>
								{/if}
							</p>
						{/if}
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

		{#if designs.length > 0}
			<Card.Root>
				<Card.Header>
					<Card.Title>Trade-off view</Card.Title>
					<Card.Description>
						Each line is one (design, scenario) pair — {scenarios.length} lines per design, its full
						performance across the scenarios. Lines sharing a colour belong to the same design.
						Drag on the Scenario axis (right) to narrow to a single scenario. Designs accumulate
						across the session: every design any round produced stays on the plot, so this fills in
						as you iterate. The numeric results for a single round are below.
					</Card.Description>
				</Card.Header>
				<Card.Content class="space-y-3">
					<div class="flex flex-wrap items-center gap-2">
						{#each designs as d (d.solution.design_id)}
							<button
								type="button"
								class="hover:bg-accent flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs"
								class:opacity-40={selectedDesignIds.length > 0 && !isDesignSelected(d.solution.design_id)}
								class:border-foreground={isDesignSelected(d.solution.design_id)}
								onclick={() => toggleDesignSelection(d.solution.design_id)}
							>
								<span
									class="inline-block h-3 w-3 rounded-full"
									style={`background-color:${designColor(d.solution.design_id)}`}
								></span>
								Solution {d.solution.solution_number}
							</button>
						{/each}
						{#if selectedDesignIds.length > 0}
							<Button size="sm" variant="ghost" onclick={() => (selectedDesignIds = [])}>
								Clear ({selectedDesignIds.length})
							</Button>
						{/if}
					</div>
					<div style="height: 470px;">
						<ParallelCoordinates
							data={chartRows}
							dimensions={chartDimensions}
							options={CHART_OPTIONS}
							colorByIndex={chartColorByIndex}
							lineLabels={chartLineLabels}
							multipleSelectedIndexes={chartSelectedRows}
							onLineSelect={(row) => toggleDesignByChartRow(row)}
						/>
					</div>
				</Card.Content>
			</Card.Root>

			<Card.Root>
				<Card.Header>
					<Card.Title class="flex items-center justify-between gap-3">
						<span>Per-scenario view</span>
						<Button size="sm" variant="outline" onclick={() => (showPerScenario = !showPerScenario)}>
							{showPerScenario ? 'Hide' : 'Show'}
						</Button>
					</Card.Title>
					<Card.Description>
						The same designs, split into one panel per scenario. All panels share the axis ranges of
						the trade-off view above, so a line's height means the same thing in each of them. Tick
						numbers are compact ("-32.1M", "7.9k"); hover any line for its exact values. Click a
						solution above to follow one design across all {scenarios.length} scenarios at once.
					</Card.Description>
				</Card.Header>
				{#if showPerScenario}
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
											multipleSelectedIndexes={panelSelectedRows(panel.designIdByRow)}
											onLineSelect={(row) => toggleDesignByPanelRow(panel.designIdByRow, row)}
										/>
									</div>
								{:else}
									<p class="text-muted-foreground py-6 text-center text-xs">No data</p>
								{/if}
							</div>
						{/each}
					</div>
				</Card.Content>
				{/if}
			</Card.Root>
		{/if}

		{#if sessionTree.length > 1}
			<div class="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2">
				<Button
					size="sm"
					variant="outline"
					disabled={viewedIterationIndex <= 0}
					onclick={goToPreviousIteration}
				>
					◀ Previous
				</Button>
				<span class="text-sm">
					Iteration {viewedIterationNumber} of {sessionTree.length}
					{#if viewedEntry?.note}
						— "{viewedEntry.note}"
					{/if}
				</span>
				<Button
					size="sm"
					variant="outline"
					disabled={viewedIterationIndex >= sessionTree.length - 1}
					onclick={goToNextIteration}
				>
					Next ▶
				</Button>
				{#if !isViewingLatest}
					<Button size="sm" variant="ghost" onclick={goToLatestIteration}>Jump to latest</Button>
					<span class="text-xs text-amber-700">
						Viewing an earlier round. The aspiration levels above are still the ones a new solve
						would use — running an iteration adds a new round rather than replacing this one.
					</span>
				{/if}
			</div>
		{/if}

		{#if solutionsThisRound.length > 0}
			{#each solutionsThisRound as sol (sol.design_id)}
			<Card.Root>
				<Card.Header>
					<Card.Title>
						Iteration {viewedIterationNumber} — solution {sol.solution_number}
						{#if solutionsThisRound.length > 1}
							of {solutionsThisRound.length}
						{/if}
					</Card.Title>
					<p class="text-muted-foreground text-xs">
						From {sol.matched_by.map(scalarizerLabel).join(' + ') || 'Balanced'}{#if sol.matched_by.length > 1}
							&nbsp;— these variants all produced this same build{/if}
					</p>
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
							Solution {sol.solution_number}
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
						<Button
							size="sm"
							variant="outline"
							onclick={() => toggleSolutionDetail(sol.design_id)}
						>
							{expandedSolutions.includes(sol.design_id) ? 'Hide details' : 'Show details'}
						</Button>
					</div>

					{#if !expandedSolutions.includes(sol.design_id)}
						{@const binding = bindingLabels(sol)}
						<p class="text-muted-foreground text-xs">
							{#if binding.length > 0}
								Limited by <span class="text-foreground font-medium">{binding.join(', ')}</span> —
								relaxing one of those is what buys improvement elsewhere.
							{:else}
								Every aspiration was met, so no cell is limiting this solution.
							{/if}
						</p>
					{/if}

					{#if expandedSolutions.includes(sol.design_id)}
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

					{/if}

					{#if expandedSolutions.includes(sol.design_id) && Object.keys(sol.strategic_values).length > 0}
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
			{/each}
		{/if}

		{#if designs.length > 0}
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
										<Table.Head>Solution</Table.Head>
										{#each objectives as obj (obj)}
											<Table.Head>{objectiveLabels[obj] ?? obj}</Table.Head>
										{/each}
										<Table.Head>Mean</Table.Head>
									</Table.Row>
								</Table.Header>
								<Table.Body>
									{#each analysis.domain_criterion as row (row.design_id)}
										<Table.Row>
											{@const solNumber = solutionNumberFor(row.design_id)}
										<Table.Cell class="font-medium">
											<span
												class="mr-1.5 inline-block h-3 w-3 rounded-full align-middle"
												style={`background-color:${designColor(row.design_id)}`}
											></span>
											{#if solNumber !== null}
												Solution {solNumber}
											{:else}
												Design {row.design_id}
											{/if}
										</Table.Cell>
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
										options={CHART_OPTIONS}
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

		{#if designs.length > 0 && strategicSymbols.length > 0}
			<Card.Root>
				<Card.Header>
					<Card.Title class="flex items-center justify-between gap-3">
						<span>Strategic decisions</span>
						<Button size="sm" variant="outline" onclick={() => (showStrategic = !showStrategic)}>
							{showStrategic ? 'Hide' : 'Show'}
						</Button>
					</Card.Title>
					<Card.Description>
						What a design actually builds — the first-stage capacities behind the performance shown
						above, against the capacity that already exists. These are here-and-now decisions, so
						one design has a single set of them: the same build is what every scenario is evaluated
						against. Pick a design, or focus one in the charts above and this follows it.
					</Card.Description>
				</Card.Header>
				{#if showStrategic}
				<Card.Content class="space-y-4">
					<div>
						<Label for="combined-strategic-design">Design</Label>
						<select
							id="combined-strategic-design"
							class="border-input mt-1 block w-72 rounded-md border bg-transparent px-3 py-1.5 text-sm shadow-xs"
							bind:value={strategicCardDesignId}
						>
							{#each designs as d (d.solution.design_id)}
								<option value={d.solution.design_id}>
									Solution {d.solution.solution_number}
								</option>
							{/each}
						</select>

						{#if strategicCardEntry}
							{@const found = strategicCardEntry.solution.matched_by ?? []}
							<p class="text-muted-foreground mt-2 text-xs">
								Discovered by
								<span class="text-foreground font-medium">
									{found.length > 0 ? found.map(scalarizerLabel).join(' + ') : 'Balanced'}
								</span>
								(iteration {strategicCardEntry.iteration}){#if found.length > 1}
									&nbsp;— several variants converged on this same build{/if}
							</p>
						{/if}
					</div>

					{#if strategicCardRows.length > 0}
						<div class="overflow-x-auto">
							<p class="mb-2 flex items-center gap-1.5 text-sm font-medium">
								{#if strategicCardDesignId !== null}
									<span
										class="inline-block h-3 w-3 rounded-full"
										style={`background-color:${designColor(strategicCardDesignId)}`}
									></span>
								{/if}
								{#if strategicCardSolutionNumber !== null}
									Solution {strategicCardSolutionNumber}
								{:else}
									Design {strategicCardDesignId}
								{/if}
								— capacities and change relative to the existing system
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
									{#each strategicCardRows as row (row.sym)}
										<Table.Row>
											<Table.Cell class="font-medium">{row.component}</Table.Cell>
											<Table.Cell class="text-muted-foreground">{row.unit}</Table.Cell>
											<Table.Cell>
												{row.existing === null ? '—' : fmt(row.existing)}
											</Table.Cell>
											<Table.Cell>{fmt(row.added)}</Table.Cell>
											<Table.Cell>{row.total === null ? '—' : fmt(row.total)}</Table.Cell>
											<Table.Cell>
												{#if row.changePct === null}
													<span class="text-muted-foreground">—</span>
												{:else}
													{row.changePct > 0 ? '+' : ''}{row.changePct.toFixed(1)}%
												{/if}
											</Table.Cell>
										</Table.Row>
									{/each}
								</Table.Body>
							</Table.Root>
							<p class="text-muted-foreground mt-2 text-xs">
								A dash under <em>Existing capacity</em> means that variable is unbounded in the
								problem, so there is no existing figure to compare against; under
								<em>Change from existing</em> it means the component starts from zero, where a
								percentage increase has no meaning.
							</p>
						</div>
					{/if}

					{#if strategicCardBreakdown.length > 0}
						<div class="overflow-x-auto">
							<p class="mb-2 flex items-center gap-3 text-sm font-medium">
								<span>Performance across all {scenarios.length} scenarios</span>
								<Button
									size="sm"
									variant="outline"
									onclick={() => (showPerformance = !showPerformance)}
								>
									{showPerformance ? 'Hide' : 'Show'}
								</Button>
							</p>
							{#if showPerformance}
							<Table.Root>
								<Table.Header>
									<Table.Row>
										<Table.Head>Scenario</Table.Head>
										{#each objectives as obj (obj)}
											<Table.Head>{objectiveLabels[obj] ?? obj}</Table.Head>
										{/each}
									</Table.Row>
								</Table.Header>
								<Table.Body>
									{#each strategicCardBreakdown as row (String(row.scenario))}
										<Table.Row>
											<Table.Cell class="font-medium">{row.scenario}</Table.Cell>
											{#each objectives as obj (obj)}
												<Table.Cell>{fmt(Number(row[obj]))}</Table.Cell>
											{/each}
										</Table.Row>
									{/each}
								</Table.Body>
							</Table.Root>
							<p class="text-muted-foreground mt-2 text-xs">
								One row per scenario for this one design. A shared objective — one that depends
								only on the here-and-now capacities — takes the same value in every row, because
								the build does not change between scenarios; only the dispatch does.
							</p>
							{/if}
						</div>
					{/if}
				</Card.Content>
				{/if}
			</Card.Root>
		{/if}
	{/if}
</div>
