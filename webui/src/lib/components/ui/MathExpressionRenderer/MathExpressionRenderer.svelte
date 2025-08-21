<script lang="ts">
	import { onMount } from 'svelte';
	import { ComputeEngine, type SemiBoxedExpression } from '@cortex-js/compute-engine';
	import MathField from '$lib/MathField.svelte';

	export let func: any; // MathJSON expression (array or object)

	let latex = '';
	const ce = new ComputeEngine();

	function flattenMax(expr: unknown): unknown {
		if (Array.isArray(expr) && expr[0] === 'Max' && Array.isArray(expr[1]) && expr.length === 2) {
			// Rewrite ["Max", [a, b, c]] as ["Max", a, b, c]
			return ['Max', ...expr[1]];
		}

		// Recurse through children if it is an array
		if (Array.isArray(expr)) {
			return expr.map(flattenMax);
		}

		return expr;
	}

	onMount(() => {
		try {
			const expr = ce.box(flattenMax(func) as SemiBoxedExpression);
			latex = expr.latex;
		} catch (err) {
			console.log(flattenMax(func));
			console.error('Invalid MathJSON expression:', err);
			latex = 'Invalid expression';
		}
	});
</script>

<MathField read-only class="text-lg" value={latex} />
