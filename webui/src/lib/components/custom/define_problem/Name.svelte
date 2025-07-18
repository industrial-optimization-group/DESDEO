<script lang="ts">
    import {
		FormField,
		FormLabel,
        FormControl,
	} from '$lib/components/ui/form';
	import Input from '$lib/components/ui/input/input.svelte';
    let { form } = $props();
	const { form: formData, errors } = form;
</script>
<FormField {form} name="name">
    <FormControl>
        <FormLabel for="name">Name</FormLabel>
        <Input id="name" name="name" bind:value={$formData.name} />
        {#if $errors.name}<span class="invalid text-red-500">{$errors.name}</span>{/if}
    </FormControl>
</FormField>