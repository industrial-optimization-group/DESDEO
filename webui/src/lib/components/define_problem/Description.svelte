<script lang="ts">
    import {
		FormField,
		FormLabel,
        FormControl,
	} from '$lib/components/ui/form';
	import Textarea from '$lib/components/ui/textarea/textarea.svelte';
    let { form } = $props();
	const { form: formData, errors } = form;
</script>
<FormField {form} name="description">
    <FormControl>
        <FormLabel for="description">Description</FormLabel>
        <Textarea
            id="description"
            name="description"
            bind:value={$formData.description}
            rows={3}
        />
        {#if $errors.description}<span class="invalid text-red-500">{$errors.description}</span>{/if}
    </FormControl>
</FormField>