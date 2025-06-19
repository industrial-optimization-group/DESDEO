<script lang="ts">
	import 'mathlive';
	import type { MathfieldElement, MathfieldElementAttributes } from 'mathlive';
	import { on } from 'svelte/events';

	type Props = { value?: string } & Partial<MathfieldElementAttributes>;

	let { value = $bindable(), ...rest }: Props = $props();

	const init = (node: MathfieldElement) => {
		$effect(() => {
			if (value) node.value = value;
		});
		$effect(() => {
			return on(node, 'input', () => {
				value = node.value;
			});
		});
	};
</script>

<math-field use:init {...rest}></math-field>
