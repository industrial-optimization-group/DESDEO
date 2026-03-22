<script lang="ts">
	import { tree as d3tree, type HierarchyPointNode } from 'd3-hierarchy';
	import type {
		SessionTreeResponse,
		TreeHierarchyDatum,
		TreeNodeResponse,
		DecisionEventResponse
	} from './tree-types';
	import type { components } from '$lib/api/client-types';
	import { buildHierarchy, analyzeTradeoffs } from './tree-utils';
	import DecisionTreeNode from './decision-tree-node.svelte';
	import DecisionTreeTooltip from './decision-tree-tooltip.svelte';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors.js';
	import { getDisplayAccuracy, formatNumber } from '$lib/helpers';

	type ProblemInfo = components['schemas']['ProblemInfo'];

	interface Props {
		treeData: SessionTreeResponse | null;
		activeNodeId?: number | null;
		onSelectNode?: (nodeId: number) => void;
		problem?: ProblemInfo | null;
	}

	let { treeData, activeNodeId = null, onSelectNode, problem = null }: Props = $props();

	let tooltipNode = $state<TreeNodeResponse | null>(null);
	let tooltipX = $state(0);
	let tooltipY = $state(0);
	let tooltipVisible = $state(false);
	let containerEl = $state<HTMLDivElement | null>(null);  // is used!

	// Overlay state for right-click context panel
	let overlayVisible = $state(false);
	let overlayNode = $state<TreeNodeResponse | null>(null);
	let overlayPoints = $state<number[][]>([]);
	let overlayChosenIdx = $state<number | null>(null);
	let overlayPreviousValues = $state<number[][]>([]);

	const NODE_W = 60;
	const NODE_H = 80;
	const PADDING = 30;

	// Run d3 tree layout ourselves so we can compute exact bounds
	let layoutRoot = $derived.by(() => {
		if (!treeData || treeData.nodes.length === 0) return null;
		const root = buildHierarchy(treeData);
		const layout = d3tree<TreeHierarchyDatum>().nodeSize([NODE_W, NODE_H]);
		return layout(root);
	});

	// Collect laid-out nodes and links
	let layoutNodes = $derived.by(() => {
		if (!layoutRoot) return [];
		return layoutRoot.descendants();
	});

	let layoutLinks = $derived.by(() => {
		if (!layoutRoot) return [];
		return layoutRoot.links();
	});

	// Compute exact bounding box from layout coordinates
	let bounds = $derived.by(() => {
		if (layoutNodes.length === 0) return { minX: 0, maxX: 0, minY: 0, maxY: 0 };
		let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
		for (const n of layoutNodes) {
			if (n.x < minX) minX = n.x;
			if (n.x > maxX) maxX = n.x;
			if (n.y < minY) minY = n.y;
			if (n.y > maxY) maxY = n.y;
		}
		return { minX, maxX, minY, maxY };
	});

	let svgWidth = $derived(bounds.maxX - bounds.minX + PADDING * 2);
	let svgHeight = $derived(bounds.maxY - bounds.minY + PADDING * 2);
	// Shift so that minX maps to PADDING, minY maps to PADDING
	let offsetX = $derived(-bounds.minX + PADDING);
	let offsetY = $derived(-bounds.minY + PADDING);

	let maxIteration = $derived.by(() => {
		if (!treeData) return 0;
		return Math.max(
			0,
			...treeData.nodes
				.filter((n) => n.node_type === 'step' && n.current_iteration != null)
				.map((n) => n.current_iteration!)
		);
	});

	// Build a map from objective symbol to whether it should be maximized
	let maximizeMap = $derived.by(() => {
		const map: Record<string, boolean> = {};
		if (!problem?.objectives) return map;
		for (const obj of problem.objectives) {
			map[obj.symbol] = obj.maximize ?? false;
		}
		return map;
	});

	// Forward event for tooltip: the decision made FROM the hovered node (for root nodes)
	let tooltipForwardEvent = $state<DecisionEventResponse | null>(null);

	function handleNodeMouseEnter(e: MouseEvent, node: TreeNodeResponse) {
		// Use viewport coordinates since tooltip is position:fixed
		tooltipX = e.clientX;
		tooltipY = e.clientY;
		tooltipNode = node;
		// Forward event: decision made FROM this node (only show trade-offs when a choice was made here)
		tooltipForwardEvent = treeData?.decision_events.find(
			(fev) => fev.parent_node_id === node.node_id
		) ?? null;
		tooltipVisible = true;
	}

	function handleNodeMouseLeave() {
		tooltipVisible = false;
	}

	function handleNodeClick(node: TreeNodeResponse) {
		if (node.node_type === 'step' && node.node_id > 0 && onSelectNode) {
			onSelectNode(node.node_id);
		}
	}

	function handleNodeContextMenu(e: MouseEvent, node: TreeNodeResponse) {
		e.preventDefault();
		tooltipVisible = false;

		// Only show overlay for step nodes with intermediate points
		if (!node.intermediate_points || node.intermediate_points.length === 0) return;

		const points = (node.intermediate_points as Record<string, number>[]).map(
			(pt) => Object.values(pt)
		);

		overlayNode = node;
		overlayPoints = points;

		// Find if there's a decision event from this node (chosen option)
		const childEvent = treeData?.decision_events.find(
			(ev) => ev.parent_node_id === node.node_id
		);
		overlayChosenIdx = childEvent?.chosen_option_idx ?? null;

		// Previous objective values: the selected_point of this node (what was chosen to arrive here)
		if (node.selected_point) {
			overlayPreviousValues = [Object.values(node.selected_point as Record<string, number>)];
		} else {
			overlayPreviousValues = [];
		}

		overlayVisible = true;
	}

	// Trade-offs: only shown when a decision was made FROM this node
	let overlayTradeoffs = $derived.by(() => {
		if (!overlayNode || overlayChosenIdx == null || !overlayNode.intermediate_points) return null;
		return analyzeTradeoffs(
			overlayNode.intermediate_points as Record<string, number>[],
			overlayChosenIdx,
			maximizeMap
		);
	});

	// The decision event that was made FROM this overlay node (i.e., the child's event)
	let overlayDecisionEvent = $derived.by(() => {
		if (!overlayNode || !treeData) return null;
		return treeData.decision_events.find(
			(ev) => ev.parent_node_id === overlayNode!.node_id
		) ?? null;
	});

	// Objective keys for the overlay table
	let overlayObjectiveKeys = $derived.by(() => {
		if (!overlayNode?.intermediate_points || overlayNode.intermediate_points.length === 0) return [];
		return Object.keys(overlayNode.intermediate_points[0] as Record<string, number>);
	});

	let overlayDisplayAccuracy = $derived(getDisplayAccuracy(problem ?? null));

	function closeOverlay() {
		overlayVisible = false;
	}

	function handleOverlayKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') closeOverlay();
	}
</script>

<svelte:window onkeydown={handleOverlayKeydown} />

<div class="relative h-full w-full overflow-auto" bind:this={containerEl}>
	{#if !treeData || treeData.nodes.length === 0}
		<div class="flex h-full items-center justify-center text-sm text-gray-400">
			No tree data available. Run a few iterations first.
		</div>
	{:else if layoutRoot}
		<div class="p-2">
			<div class="mb-2 text-xs font-semibold text-gray-600">Decision Tree</div>
			<svg width={svgWidth} height={svgHeight}>
				<g transform="translate({offsetX}, {offsetY})">
					<!-- Links as SVG cubic bezier paths -->
					{#each layoutLinks as link}
						{@const sx = link.source.x}
						{@const sy = link.source.y}
						{@const tx = link.target.x}
						{@const ty = link.target.y}
						{@const my = (sy + ty) / 2}
						<path
							d="M{sx},{sy} C{sx},{my} {tx},{my} {tx},{ty}"
							fill="none"
							stroke="#d1d5db"
							stroke-width="2"
						/>
					{/each}

					<!-- Nodes -->
					{#each layoutNodes as pointNode}
						{@const datum = pointNode.data}
						{#if datum.node.node_id !== -1}
							<g transform="translate({pointNode.x}, {pointNode.y})">
								<DecisionTreeNode
									node={datum.node}
									{maxIteration}
									isActive={datum.node.node_id === activeNodeId}
									onmouseenter={(e) => handleNodeMouseEnter(e, datum.node)}
									onmouseleave={handleNodeMouseLeave}
									onclick={() => handleNodeClick(datum.node)}
									oncontextmenu={(e) => handleNodeContextMenu(e, datum.node)}
								/>
							</g>
						{/if}
					{/each}
				</g>
			</svg>
		</div>

		<DecisionTreeTooltip
			node={tooltipNode ?? {
				node_id: 0,
				parent_node_id: null,
				depth: 0,
				node_type: 'step',
				current_iteration: null,
				iterations_left: null,
				selected_point: null,
				intermediate_points: null,
				closeness_measures: null,
				selected_point_index: null,
				selected_intermediate_point: null,
				final_solution_objectives: null
			}}
			forwardEvent={tooltipForwardEvent}
			{maximizeMap}
			x={tooltipX}
			y={tooltipY}
			visible={tooltipVisible && tooltipNode !== null}
		/>
	{/if}
</div>

<!-- Right-click overlay with parallel coordinates snapshot -->
{#if overlayVisible && overlayNode && problem}
	<!-- Backdrop -->
	<button
		class="fixed inset-0 z-[9998] bg-black/30"
		onclick={closeOverlay}
		aria-label="Close overlay"
		tabindex="-1"
	></button>

	<!-- Overlay panel -->
	<div
		class="fixed left-1/2 top-1/2 z-[9999] flex h-[80vh] w-[90vw] max-w-6xl -translate-x-1/2 -translate-y-1/2 flex-col rounded-lg border border-gray-200 bg-white shadow-2xl"
	>
		<!-- Header -->
		<div class="flex items-center justify-between border-b border-gray-200 px-4 py-2">
			<div class="text-sm font-semibold text-gray-700">
				Node #{overlayNode.node_id} — Iteration {overlayNode.current_iteration ?? '?'}
				<span class="ml-2 text-xs text-gray-500">
					({overlayNode.iterations_left ?? '?'} iterations left)
				</span>
				{#if overlayChosenIdx != null}
					<span class="ml-2 text-xs text-gray-500">
						| chose option #{overlayChosenIdx + 1}
					</span>
				{/if}
			</div>
			<button
				class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
				onclick={closeOverlay}
				aria-label="Close"
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
				</svg>
			</button>
		</div>

		<!-- Body: visualization + info dump side by side -->
		<div class="flex flex-1 overflow-hidden">
			<!-- Left: parallel coordinates -->
			<div class="flex-1 overflow-hidden border-r border-gray-200 p-2">
				<VisualizationsPanel
					{problem}
					solutionsObjectiveValues={overlayPoints}
					previousObjectiveValues={overlayPreviousValues}
					externalSelectedIndexes={overlayChosenIdx != null ? [overlayChosenIdx] : []}
					previousPreferenceType={''}
					currentPreferenceType={''}
				/>
			</div>

			<!-- Right: info dump -->
			<div class="w-80 shrink-0 overflow-y-auto p-3 text-xs">
				<!-- Selected point (how DM arrived at this node) -->
				{#if overlayNode.selected_point}
					<div class="mb-3">
						<div class="mb-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
							Previous point
						</div>
						<div class="space-y-0.5">
							{#each Object.entries(overlayNode.selected_point as Record<string, number>) as [key, val]}
								<div class="flex justify-between font-mono">
									<span class="text-gray-600">{key}</span>
									<span class="text-gray-900">{val.toFixed(6)}</span>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Closeness measures -->
				{#if overlayNode.closeness_measures && overlayNode.closeness_measures.length > 0}
					<div class="mb-3">
						<div class="mb-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
							Closeness measures
						</div>
						<div class="flex flex-wrap gap-1">
							{#each overlayNode.closeness_measures as cm, i}
								<span class="rounded bg-gray-100 px-1.5 py-0.5 font-mono {overlayChosenIdx === i ? 'bg-blue-100 font-semibold text-blue-700' : 'text-gray-700'}">
									#{i + 1}: {cm.toFixed(4)}
								</span>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Trade-offs at this choice (only when a decision was made FROM this node) -->
				{#if overlayTradeoffs}
					<div class="mb-3">
						<div class="mb-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
							Trade-offs at this choice
						</div>
						<div class="space-y-1">
							{#each overlayTradeoffs as t}
								{@const color = t.normalizedRank <= 0.25 ? '#059669' : t.normalizedRank >= 0.75 ? '#dc2626' : '#d97706'}
								{@const barW = Math.max(8, (1 - t.normalizedRank) * 100)}
								{@const label = t.total <= 1 ? '' : t.rank === 1 ? 'best' : t.rank === t.total ? 'worst' : `${t.rank}/${t.total}`}
								<div class="flex items-center gap-1.5">
									<span class="w-10 shrink-0 font-mono text-gray-700">{t.key}</span>
									<span class="w-5 shrink-0 text-center text-[9px] text-gray-400" title={t.maximize ? 'maximize' : 'minimize'}>
										{t.maximize ? 'max' : 'min'}
									</span>
									<div class="relative h-3 flex-1 rounded-sm bg-gray-100">
										<div
											class="h-full rounded-sm"
											style="width: {barW}%; background-color: {color};"
										></div>
									</div>
									<span class="w-10 shrink-0 text-right font-semibold" style="color: {color};">
										{label}
									</span>
								</div>
							{/each}
						</div>
						<div class="mt-1 text-[10px] text-gray-400">
							Green = prioritized, Red = sacrificed
						</div>
					</div>
				{/if}


				<!-- Decision event details -->
				{#if overlayDecisionEvent}
					<div class="mb-3">
						<div class="mb-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
							Decision made
						</div>
						<div class="space-y-0.5 text-gray-600">
							<div>Chose option: <span class="font-semibold text-gray-900">#{(overlayDecisionEvent.chosen_option_idx ?? 0) + 1}</span></div>
							<div>Next node: <span class="font-mono text-gray-900">#{overlayDecisionEvent.child_node_id}</span></div>
							<div>Iterations left after: <span class="font-mono text-gray-900">{overlayDecisionEvent.iterations_left_after}</span></div>
						</div>
						{#if overlayDecisionEvent.chosen_point}
							<div class="mt-1.5">
								<div class="mb-0.5 text-[10px] text-gray-500">Chosen point values:</div>
								<div class="space-y-0.5">
									{#each Object.entries(overlayDecisionEvent.chosen_point as Record<string, number>) as [key, val]}
										<div class="flex justify-between font-mono">
											<span class="text-gray-600">{key}</span>
											<span class="text-gray-900">{val.toFixed(6)}</span>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Intermediate points table -->
				{#if overlayNode.intermediate_points && overlayObjectiveKeys.length > 0}
					<div class="mb-3">
						<div class="mb-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
							Intermediate points ({overlayNode.intermediate_points.length})
						</div>
						<div class="overflow-x-auto">
							<table class="min-w-full border-collapse">
								<thead>
									<tr class="border-b border-gray-200">
										<th class="px-1 py-1 text-left text-[10px] font-semibold text-gray-600">#</th>
										<th class="px-1 py-1 text-right text-[10px] font-semibold text-gray-600">Closeness</th>
										{#each overlayObjectiveKeys as key, idx}
											{@const objInfo = problem?.objectives?.find(o => o.symbol === key)}
											<th
												class="px-1 py-1 text-right text-[10px] font-semibold text-gray-600"
												style="border-bottom: 6px solid {COLOR_PALETTE[idx % COLOR_PALETTE.length]}"
											>
												{objInfo ? `${objInfo.name} (${objInfo.maximize ? 'max' : 'min'})` : key}
											</th>
										{/each}
									</tr>
								</thead>
								<tbody>
									{#each overlayNode.intermediate_points as pt, i}
										{@const row = pt as Record<string, number>}
										{@const isChosen = overlayChosenIdx === i}
										<tr class="border-b border-gray-50 {isChosen ? 'bg-blue-50 font-semibold' : ''}">
											<td class="px-1 py-0.5 text-gray-500 {isChosen ? 'border-l-4 border-blue-600' : ''}">{i + 1}</td>
											<td class="px-1 py-0.5 text-right font-mono text-gray-800">
												{overlayNode.closeness_measures?.[i] != null ? formatNumber(overlayNode.closeness_measures[i], 4) : '-'}
											</td>
											{#each overlayObjectiveKeys as key, idx}
												<td class="px-1 py-0.5 text-right font-mono text-gray-800">
													{formatNumber(row[key], overlayDisplayAccuracy[idx] ?? 4)}
												</td>
											{/each}
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				{/if}

				<!-- Final node info -->
				{#if overlayNode.node_type === 'final'}
					<div class="mb-3">
						<div class="mb-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
							Final solution
						</div>
						{#if overlayNode.final_solution_objectives}
							<div class="space-y-0.5">
								{#each Object.entries(overlayNode.final_solution_objectives as Record<string, number>) as [key, val]}
									<div class="flex justify-between font-mono">
										<span class="text-gray-600">{key}</span>
										<span class="font-semibold text-emerald-700">{val.toFixed(6)}</span>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
