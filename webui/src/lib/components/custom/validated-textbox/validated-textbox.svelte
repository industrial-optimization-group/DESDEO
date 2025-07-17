<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { z } from 'zod';

	export let min: number = 0;
	export let max: number = 100;
	export let placeholder: string = `Enter a number (${min}–${max})`;

	export let value: string = '';
	export let onChange: (value: string) => void = () => {};
	let error: string | null = null;

	const schema = (min: number, max: number) =>
		z
			.string()
			.refine((val) => /^-?\d*\.?\d+$/.test(val), {
				message: 'Only numbers are allowed.'
			})
			.transform(Number)
			.refine((num) => num >= min && num <= max, {
				message: `Value must be between ${min} and ${max}.`
			});

	function validate(val: string) {
		const result = schema(min, max).safeParse(val);
		if (!result.success) {
			error = result.error.errors[0].message;
		} else {
			error = null;
			onChange(val);
		}
		value = val;
	}
</script>

<Input
	type="text"
	{placeholder}
	class="max-w-xs"
	bind:value
	oninput={(e) => validate(e.currentTarget.value)}
/>
{#if error}
	<p class="mt-1 text-xs text-red-600">{error}</p>
{/if}
