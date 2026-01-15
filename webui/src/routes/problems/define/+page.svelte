<script lang="ts" module>
	/**
	 * 	+page.svelte (Problem Definition Form)
	 *
	 *	@created July 2025
	 *
	 *	@description
	 *	This page implements a problem definition form for DESDEO optimization problems.
	 *	In addition to problem name and description, it supports adding variables, objectives,
	 *	and constants with both scalar and tensor types.
	 *
	 *	@features
	 *	- Support for both scalar and tensor variables/constants
	 *	- Basic validation with some structured error display
	 *	- JSON input parsing for complex fields (func, surrogates, scenario_keys, tensor inputs)
	 *
	 *	@architecture
	 *	- SvelteKit Superforms for form state management and validation
	 *	- Reactive form state through $formData store
	 *	- Basic error propagation and display
	 *
	 *	@dependencies
	 *	- SvelteKit Superforms: Form state management and validation
	 *	- Zod schemas: Type inference and validation
	 *	- Custom form components: Variables, Constants, Objectives, Name, Description
	 *	- UI components: FormButton, Card
	 *
	 *	@limitations
	 *	- Constraints, extra functions, scalarization functions etc. not implemented
	 *	- Success message after successful submission not implemented
	 *	- Could benefit from better UX for a lot of inputs
	 *
	 *	@notes
	 *	- SuperDebug component available for debugging (commented out)
	 *	- Form uses JSON dataType for proper array/object handling
	 *	- Tainted message warns users about unsaved changes
	 */
	/*
	export type Variable = z.infer<typeof schemas.Variable>;
	export type TensorVariable = z.infer<typeof schemas.TensorVariable>;
	export type Constant = z.infer<typeof schemas.Constant>;
	export type TensorConstant = z.infer<typeof schemas.TensorConstant>;
	export type Objective = z.infer<typeof schemas.Objective>;
	*/
</script>

<script lang="ts">
	import { superForm, fileProxy } from 'sveltekit-superforms';
	import Card from '$lib/components/ui/card/card.svelte';
	import FormButton from '$lib/components/ui/form/form-button.svelte';
	import type { PageData } from '../$types';

	const { data } = $props<{ data: PageData }>();

	const { form, enhance, errors } = superForm(data.form);

	const file = fileProxy(form, 'json_file');
</script>

<section class="mx-10">
	<div class="m-6 mx-auto max-w-4xl">
		<h1 class="mt-10 text-center text-2xl font-semibold">Problem Definition</h1>

		<form
			class="flex flex-col gap-4"
			action="?/upload_json"
			method="POST"
			enctype="multipart/form-data"
			use:enhance
		>
			<Card class="p-6">
				<input type="file" name="json_file" accept=".json" bind:files={$file} />
			</Card>
			<FormButton>Submit</FormButton>
		</form>
	</div>
</section>
