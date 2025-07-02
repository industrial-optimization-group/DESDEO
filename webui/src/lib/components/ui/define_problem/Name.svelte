<script lang="ts">
    	import {
		FormField,
		FormLabel,
        FormControl,
	} from '$lib/components/ui/form';
	import Input from '$lib/components/ui/input/input.svelte';
	import type { SuperForm } from 'sveltekit-superforms';

    export let form: SuperForm<any>;
	const { form: formData } = form;
</script>
<FormField {form} name="name">
    <FormControl>
        <FormLabel for="name">Name</FormLabel>
        <Input id="name" name="name" bind:value={$formData.name} />
    </FormControl>
</FormField>