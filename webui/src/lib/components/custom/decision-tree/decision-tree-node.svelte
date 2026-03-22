<script lang="ts">
	import type { TreeNodeResponse } from './tree-types';
	import { nodeColor } from './tree-utils';

	interface Props {
		node: TreeNodeResponse;
		maxIteration: number;
		isActive?: boolean;
		onmouseenter?: (e: MouseEvent) => void;
		onmouseleave?: (e: MouseEvent) => void;
		onclick?: (e: MouseEvent) => void;
		oncontextmenu?: (e: MouseEvent) => void;
	}

	let {
		node,
		maxIteration,
		isActive = false,
		onmouseenter,
		onmouseleave,
		onclick,
		oncontextmenu
	}: Props = $props();

	let color = $derived(nodeColor(node, maxIteration));
	let radius = $derived(node.node_type === 'final' ? 10 : 8);
	let label = $derived(
		node.node_type === 'final'
			? 'F'
			: node.current_iteration != null
				? `${node.current_iteration}`
				: '?'
	);
</script>

<g
	class="cursor-pointer"
	role="button"
	tabindex="0"
	onmouseenter={onmouseenter}
	onmouseleave={onmouseleave}
	onclick={onclick}
	oncontextmenu={oncontextmenu}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') onclick?.(e as any);
	}}
>
	<circle
		r={radius}
		fill={color}
		stroke={isActive ? '#1d4ed8' : '#fff'}
		stroke-width={isActive ? 3 : 2}
		class="transition-all duration-150"
	/>
	<text
		text-anchor="middle"
		dominant-baseline="central"
		fill="white"
		font-size="9"
		font-weight="bold"
		class="pointer-events-none select-none"
	>
		{label}
	</text>
</g>
