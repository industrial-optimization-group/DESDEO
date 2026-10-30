<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { z } from 'zod';

	export let min: number = 0;
	export let max: number = 100;
	export let placeholder: string = `Enter a number (${min}–${max})`;

	export let value: string = '';
	export let onChange: (value: string) => void = () => {};
	let error: string | null = null;

	// What the user is typing. The parent usually echoes each change back formatted (2 -> "2.00"),
	// so outside updates are only taken while the field is not being edited.
	let draft = value;
	let focused = false;
	$: if (!focused) draft = value;

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
		draft = val;
	}
</script>

<Input
	type="text"
	{placeholder}
	class="max-w-xs"
	bind:value={draft}
	onfocus={() => (focused = true)}
	onblur={() => {
		focused = false;
		draft = value;
	}}
	oninput={(e) => validate(e.currentTarget.value)}
/>
{#if error}
	<p class="mt-1 text-xs text-red-600">{error}</p>
{/if}
