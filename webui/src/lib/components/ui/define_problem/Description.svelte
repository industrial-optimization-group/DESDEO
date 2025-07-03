<script lang="ts">
    	import {
		FormField,
		FormLabel,
        FormControl,
	} from '$lib/components/ui/form';
	import Textarea from '$lib/components/ui/textarea/textarea.svelte';
    let { form } = $props();
	const { form: formData } = form;
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
    </FormControl>
</FormField>