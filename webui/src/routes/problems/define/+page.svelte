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
