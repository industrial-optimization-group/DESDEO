<script lang="ts">
	/**
	 * Edits a reference point with one aspiration level per target.
	 *
	 * `value` holds the raw aspiration levels in the objectives' original direction. They can be
	 * entered as raw values, as percent of the ideal–nadir range (100 = ideal, 0 = nadir) or as a
	 * change from the previous reference point in percent of the range toward the ideal.
	 *
	 * With targets of several scenarios, the cells are grouped by objective, and each group has a fill
	 * row that writes one entry into the cells of all scenarios or of the scenarios in `checkedLeaves`.
	 *
	 * With `limit`, entries outside a target's range are limited to it, and so are the bars' fills.
	 *
	 * Each cell has a bar for picking the raw value, filled up to `solution`, the selected design's
	 * value of the target, if given, in the scenario's colour for a per-scenario target and dark grey
	 * otherwise.
	 */
	import { SegmentedControl } from '$lib/components/custom/segmented-control';
	import type { ProblemInfo, Target } from '$lib/gen/endpoints/DESDEOFastAPI';
	import {
		applyEntry,
		changeToRaw,
		percentToRaw,
		rawToChange,
		rawToPercent,
		type Range
	} from './reference-point';
	import { limitToRange } from './scenario-optimal';
	import { compactNumber, formatNumber, objectiveLabel, targetLabel } from './labels';
	import {
		applyAllFills,
		applyFill,
		fillWithIdeals,
		groupByObjective,
		objectiveSpan,
		scopedTargets
	} from './fill';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { HorizontalBar } from '$lib/components/visualizations/horizontal-bar';

	let {
		problem,
		targets,
		ranges,
		previous = null,
		solution = null,
		leafColors = {},
		value = $bindable({}),
		checkedLeaves = [],
		limit = false,
		collapsed = $bindable([])
	}: {
		problem: ProblemInfo;
		targets: Target[];
		ranges: Record<string, Range>;
		previous?: Record<string, number> | null;
		solution?: Record<string, number> | null;
		leafColors?: Record<string, string>;
		value?: Record<string, number>;
		checkedLeaves?: string[];
		limit?: boolean;
		collapsed?: string[];
	} = $props();

	type Mode = 'percent' | 'raw' | 'change';
	let mode = $state<Mode>('raw');

	let modes = $derived([
		{ value: 'raw', label: 'Value' },
		...(previous ? [{ value: 'change', label: 'Change' }] : []),
		{ value: 'percent', label: 'Percent' }
	]);

	$effect(() => {
		if (mode === 'change' && !previous) mode = 'raw';
	});

	function shown(target: Target): number | null {
		const raw = value[target.symbol];
		const range = ranges[target.symbol];
		if (raw === undefined || !range) return null;
		if (mode === 'percent') return Number(rawToPercent(raw, range).toFixed(1));
		if (mode === 'change') {
			const prev = previous?.[target.symbol];
			return prev === undefined ? null : Number(rawToChange(raw, prev, range).toFixed(1));
		}
		return Number(raw.toPrecision(6));
	}

	// Text being typed per target, shown instead of the converted value until the input is left,
	// and the value each input had when it was focused.
	let drafts = $state<Record<string, string>>({});
	let warnings = $state<Record<string, string>>({});
	let atFocus: Record<string, number | undefined> = {};

	$effect(() => {
		void mode;
		drafts = {};
		warnings = {};
		fills = {};
		fillWarnings = {};
	});

	// Targets of another scenario can have the same symbols.
	$effect(() => {
		void targets;
		drafts = {};
		warnings = {};
	});

	// Fill rows of the objective groups, used when there are targets of several scenarios.
	let groups = $derived(groupByObjective(targets));
	let grouped = $derived(new Set(targets.map((t) => t.leaf)).size > 1);
	let scope = $state<'all' | 'checked'>('all');
	let scopeLeaves = $derived(scope === 'all' ? null : checkedLeaves);
	let fills = $state<Record<string, string>>({});
	let fillWarnings = $state<Record<string, string>>({});
	let anyFill = $derived(groups.some((g) => (fills[g.objective] ?? '').trim() !== ''));

	function fillGroup(objective: string) {
		const group = groups.find((g) => g.objective === objective);
		if (!group) return;
		const result = applyFill(
			value,
			scopedTargets(group.targets, scopeLeaves),
			ranges,
			previous,
			mode,
			fills[objective] ?? ''
		);
		value = result.point;
		fillWarnings = result.warning
			? { ...fillWarnings, [objective]: result.warning }
			: without(fillWarnings, objective);
	}

	function fillAll() {
		const result = applyAllFills(value, groups, fills, scopeLeaves, ranges, previous, mode);
		value = result.point;
		fillWarnings = result.warnings;
	}

	function toggleGroup(objective: string) {
		collapsed = collapsed.includes(objective)
			? collapsed.filter((c) => c !== objective)
			: [...collapsed, objective];
	}

	function without<T>(record: Record<string, T>, key: string): Record<string, T> {
		const rest = { ...record };
		delete rest[key];
		return rest;
	}

	function focused(target: Target) {
		atFocus[target.symbol] = value[target.symbol];
	}

	/** Apply each keystroke at once, so a typed value is never lost; an invalid entry restores the value at focus. */
	function typed(target: Target, input: string) {
		drafts = { ...drafts, [target.symbol]: input };
		const range = ranges[target.symbol];
		const initial = atFocus[target.symbol] ?? value[target.symbol];
		const prev = previous?.[target.symbol];
		if (!range || initial === undefined || (mode === 'change' && prev === undefined)) return;
		const convert =
			mode === 'percent'
				? (v: number) => percentToRaw(v, range)
				: mode === 'change'
					? (v: number) => changeToRaw(v, prev!, range)
					: (v: number) => v;
		const bounds: [number, number] | undefined =
			mode === 'percent' && !limit ? [0, 100] : undefined;
		const result = applyEntry(input, initial, convert, bounds);
		const limited = limit ? limitToRange(result.value, range) : null;
		const warning = limited?.limited
			? `Limited to the range ${formatNumber(Math.min(...range))} … ${formatNumber(Math.max(...range))}.`
			: result.warning;
		warnings = warning
			? { ...warnings, [target.symbol]: warning }
			: without(warnings, target.symbol);
		value = { ...value, [target.symbol]: limited?.value ?? result.value };
	}

	/** Set a raw value picked on the bar and show it converted in the input. */
	function picked(target: Target, raw: number) {
		const range = ranges[target.symbol];
		value = { ...value, [target.symbol]: limit ? limitToRange(raw, range).value : raw };
		drafts = without(drafts, target.symbol);
		warnings = without(warnings, target.symbol);
	}

	/** Decimals for values picked on a bar over `range`: about four significant digits of its span. */
	function barDecimals(range: Range): number {
		const span = Math.abs(range[1] - range[0]);
		return span > 0 ? Math.max(0, 3 - Math.floor(Math.log10(span))) : 2;
	}

	/** On leaving the input, show the value that will be sent. */
	function left(target: Target) {
		drafts = without(drafts, target.symbol);
		warnings = without(warnings, target.symbol);
		atFocus[target.symbol] = undefined;
	}
</script>

{#snippet cell(target: Target, label: string | null)}
	{@const range = ranges[target.symbol]}
	<div class="grid grid-cols-[minmax(0,1fr)] gap-1">
		<label for="rp-{target.symbol}" class="text-sm font-medium">
			{#if label}
				{label}
			{:else}
				{targetLabel(problem, target)}
				<span class="text-gray-500">({target.maximize ? 'max' : 'min'})</span>
			{/if}
		</label>
		<div class="flex items-center gap-2">
			<Input
				id="rp-{target.symbol}"
				aria-label={targetLabel(problem, target)}
				type="number"
				step="any"
				class="h-8 w-28 border-gray-400 px-2 text-sm"
				min={mode === 'percent' ? 0 : undefined}
				max={mode === 'percent' ? 100 : undefined}
				value={drafts[target.symbol] ?? shown(target)}
				onfocus={() => focused(target)}
				oninput={(e: Event & { currentTarget: HTMLInputElement }) =>
					typed(target, e.currentTarget.value)}
				onblur={() => left(target)}
			/>
			{#if mode !== 'raw'}
				<span class="text-xs text-gray-600">= {formatNumber(value[target.symbol])}</span>
			{/if}
		</div>
		{#if range}
			{@const solutionValue = solution?.[target.symbol]}
			<!-- Without a solution value the bar is unfilled; the padding fits the rotated tick labels. -->
			<div class="pb-6">
				<HorizontalBar
					axisRanges={[Math.min(...range), Math.max(...range)]}
					direction={target.maximize ? 'max' : 'min'}
					solutionValue={limit && solutionValue != null
						? limitToRange(solutionValue, range).value
						: solutionValue}
					selectedValue={value[target.symbol]}
					previousValue={previous?.[target.symbol]}
					barColor={solutionValue === undefined
						? '#eee'
						: ((target.leaf && leafColors[target.leaf]) ?? '#4b5563')}
					options={{
						decimalPrecision: barDecimals(range),
						showPreviousValue: true,
						showSelectedValueLabel: false,
						showPreviousValueLabel: false,
						tickFormat: compactNumber,
						aspectRatio: 'aspect-[6/1]'
					}}
					onSelect={(v: number) => picked(target, v)}
				/>
			</div>
		{/if}
		<!-- The warning takes the place of the range line, so nothing below moves when it appears. -->
		{#if warnings[target.symbol]}
			<span class="truncate text-xs text-amber-700" role="alert" title={warnings[target.symbol]}>
				{warnings[target.symbol]}
			</span>
		{:else if range}
			{@const hint = `ideal ${formatNumber(range[0])} · nadir ${formatNumber(range[1])}${
				previous?.[target.symbol] !== undefined
					? ` · previous ${formatNumber(previous[target.symbol])}`
					: ''
			}`}
			<span class="truncate text-xs text-gray-500" title={hint}>{hint}</span>
		{/if}
	</div>
{/snippet}

<div class="space-y-3">
	<SegmentedControl bind:value={mode} options={modes} size="sm" />
	<p class="text-xs text-gray-500">
		{#if mode === 'percent'}
			100 is the ideal and 0 the nadir of each target.
		{:else if mode === 'change'}
			Percent of each range to move from the previous reference point; positive moves toward the
			ideal.
		{:else}
			Aspiration levels in the objectives' own units.
		{/if}
	</p>
	{#if grouped}
		<div class="space-y-2 rounded border bg-gray-50 p-2">
			<SegmentedControl
				bind:value={scope}
				options={[
					{ value: 'all', label: 'All scenarios' },
					{ value: 'checked', label: 'Checked scenarios' }
				]}
				size="sm"
			/>
			{#if scope === 'checked' && checkedLeaves.length === 0}
				<p class="text-xs text-amber-700">
					No scenarios are checked in the chart; fills change only targets shared by all scenarios.
				</p>
			{/if}
			{#if mode === 'percent'}
				<p class="text-xs text-gray-500">
					A fill is a percent of each scenario's own range, so the values differ by scenario.
				</p>
			{/if}
			<div class="flex flex-wrap gap-2">
				<Button size="sm" variant="outline" disabled={!anyFill} onclick={fillAll}>Apply all</Button>
				<Button
					size="sm"
					variant="outline"
					onclick={() => (value = fillWithIdeals(value, targets, ranges))}>Fill with ideals</Button
				>
			</div>
		</div>
		{#each groups as group (group.objective)}
			{@const open = !collapsed.includes(group.objective)}
			{@const span = objectiveSpan(
				scopedTargets(group.targets, scopeLeaves),
				ranges,
				group.maximize
			)}
			<section class="space-y-2 border-t pt-2">
				<button
					class="flex w-full items-center gap-1 text-left text-sm font-semibold"
					aria-expanded={open}
					onclick={() => toggleGroup(group.objective)}
				>
					<span aria-hidden="true">{open ? '▾' : '▸'}</span>
					<span class="min-w-0 flex-1 truncate">{objectiveLabel(problem, group.objective)}</span>
					<span class="text-xs font-normal text-gray-500">
						({group.maximize ? 'max' : 'min'}, {group.targets.length})
					</span>
				</button>
				<div class="grid grid-cols-[minmax(0,1fr)] gap-1">
					<div class="flex items-center gap-2">
						<label class="sr-only" for="fill-{group.objective}">
							Fill {objectiveLabel(problem, group.objective)}
						</label>
						<Input
							id="fill-{group.objective}"
							type="number"
							step="any"
							placeholder="Fill"
							class="h-8 w-28 border-gray-400 px-2 text-sm"
							min={mode === 'percent' ? 0 : undefined}
							max={mode === 'percent' ? 100 : undefined}
							value={fills[group.objective] ?? ''}
							oninput={(e: Event & { currentTarget: HTMLInputElement }) =>
								(fills = { ...fills, [group.objective]: e.currentTarget.value })}
						/>
						<Button
							size="sm"
							variant="outline"
							class="h-7"
							disabled={(fills[group.objective] ?? '').trim() === ''}
							onclick={() => fillGroup(group.objective)}>Apply</Button
						>
					</div>
					{#if fillWarnings[group.objective]}
						<span class="truncate text-xs text-amber-700" role="alert">
							{fillWarnings[group.objective]}
						</span>
					{:else if mode === 'raw' && span.union}
						{@const spanText = `range ${formatNumber(span.union[0])} … ${formatNumber(span.union[1])}; ${
							span.common
								? `in every scenario: ${formatNumber(span.common[0])} … ${formatNumber(span.common[1])}`
								: 'no single value is attainable in every scenario'
						}`}
						<span class="truncate text-xs text-gray-500" title={spanText}>{spanText}</span>
					{/if}
				</div>
				{#if open}
					<div class="space-y-2 pl-3">
						{#each group.targets as target (target.symbol)}
							{@render cell(target, target.leaf ?? 'All scenarios')}
						{/each}
					</div>
				{/if}
			</section>
		{/each}
	{:else}
		{#each targets as target (target.symbol)}
			{@render cell(target, null)}
		{/each}
	{/if}
</div>
