<script lang="ts">
	/**
	 * The design registry of a setup with the wishlist and the final design. Changes are passed
	 * to `onSave`. With representative solution sets given, their designs can be imported at an
	 * editable reference point over `importObjectives`; empty entries are left out.
	 */
	import { Button } from '$lib/components/ui/button';
	import Checkbox from '$lib/components/ui/checkbox/checkbox.svelte';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import type { JinaDesignInfo, ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';
	import ObjectivePointInputs from './ObjectivePointInputs.svelte';
	import { finitePoint, midpointPrefill, type Range } from './reference-point';

	let {
		problem,
		designs,
		wishlist,
		finalId,
		selectedId = $bindable(null),
		representativeSets = [],
		importObjectives = [],
		objectiveRanges = {},
		onSave,
		onImport
	}: {
		problem: ProblemInfo;
		designs: JinaDesignInfo[];
		wishlist: number[];
		finalId: number | null;
		selectedId?: number | null;
		representativeSets?: { id: number; name: string }[];
		importObjectives?: string[];
		objectiveRanges?: Record<string, Range>;
		onSave: (wishlist: number[], finalId: number | null) => void;
		onImport?: (setId: number, referencePoint: Record<string, number>) => void;
	} = $props();

	const VIEW_LABELS: Record<string, string> = {
		aggregated: 'aggregated',
		per_scenario: 'per-scenario'
	};

	function origin(design: JinaDesignInfo): string {
		return design.source === 'import' ? 'imported' : `solved, ${VIEW_LABELS[design.view ?? '']}`;
	}

	let importSet = $state<{ id: number; name: string } | null>(null);
	let importPoint = $state<Record<string, number | null>>({});

	function chooseImport(set: { id: number; name: string }) {
		importSet = set;
		const missing = importObjectives.filter((obj) => !(obj in importPoint));
		importPoint = {
			...importPoint,
			...midpointPrefill(missing, objectiveRanges)
		};
	}

	function confirmImport() {
		if (!importSet || !onImport) return;
		onImport(importSet.id, finitePoint(importPoint, importObjectives));
		importSet = null;
	}

	function toggle(id: number, checked: boolean) {
		const next = checked ? [...wishlist, id] : wishlist.filter((w) => w !== id);
		onSave(next, finalId);
	}
</script>

<div class="space-y-2">
	<div class="flex items-center justify-between">
		<h3 class="text-sm font-semibold">Designs ({designs.length})</h3>
		{#if onImport && representativeSets.length > 0}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="outline" size="sm">Import</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end">
					{#each representativeSets as set (set.id)}
						<DropdownMenu.Item onclick={() => chooseImport(set)}>{set.name}</DropdownMenu.Item>
					{/each}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}
	</div>
	{#if importSet}
		<div class="grid gap-1 rounded border p-2">
			<span class="text-sm font-medium">Import {importSet.name}</span>
			<p class="text-xs text-gray-500">
				The designs are evaluated in each scenario at this reference point.
			</p>
			<ObjectivePointInputs
				{problem}
				objectives={importObjectives}
				idPrefix="import"
				bind:values={importPoint}
			/>
			<div class="flex justify-end gap-2">
				<Button variant="ghost" size="sm" onclick={() => (importSet = null)}>Cancel</Button>
				<Button size="sm" onclick={confirmImport}>Import</Button>
			</div>
		</div>
	{/if}
	{#if designs.length === 0}
		<p class="text-sm text-gray-500">No designs yet. Iterate to find some.</p>
	{/if}
	<ul class="max-h-72 space-y-1 overflow-y-auto">
		{#each designs as design (design.id)}
			<li
				class="flex items-center gap-2 rounded px-1 py-0.5 text-sm {design.id === selectedId
					? 'bg-blue-50'
					: ''}"
			>
				<Checkbox
					checked={wishlist.includes(design.id)}
					onCheckedChange={(checked) => toggle(design.id, !!checked)}
					aria-label="In wishlist"
					title="In wishlist"
				/>
				<button class="flex-1 text-left" onclick={() => (selectedId = design.id)}>
					#{design.id} <span class="text-xs text-gray-500">{origin(design)}</span>
				</button>
				{#if design.id === finalId}
					<span class="rounded bg-green-100 px-1 text-xs text-green-800">final</span>
					<Button
						variant="ghost"
						size="sm"
						class="h-6 px-2 text-xs"
						onclick={() => onSave(wishlist, null)}>Unmark</Button
					>
				{:else}
					<Button
						variant="ghost"
						size="sm"
						class="h-6 px-2 text-xs"
						onclick={() => onSave(wishlist, design.id)}>Mark final</Button
					>
				{/if}
			</li>
		{/each}
	</ul>
	<p class="text-xs text-gray-500">Tick a design to keep it on the wishlist.</p>
</div>
