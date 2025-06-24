<script lang="ts">
  import { FormField, FormLabel, FormButton, FormControl } from '$lib/components/ui/form';
  import Input from '$lib/components/ui/input/input.svelte';
  import Textarea from '$lib/components/ui/textarea/textarea.svelte';
  import { superForm } from "sveltekit-superforms";

  // Minimal form state for now
  const form = superForm({
    name: '',
    description: '',
    variables: '', // JSON string for now
    constants: '', // JSON string for now
    objectives: '' // JSON string for now
  });
  const { form: formData, enhance } = form;
</script>

<h1 class="mt-10 text-center text-2xl font-semibold">Problem Definition</h1>
<form class="max-w-xl mx-auto flex flex-col gap-4" method="POST" action="?/create">
  <FormField form={form} name="name">
    <FormControl>
      <FormLabel for="name">Name</FormLabel>
      <Input id="name" name="name" bind:value={$formData.name} required />
    </FormControl>
  </FormField>
  <FormField form={form} name="description">
    <FormControl>
      <FormLabel for="description">Description</FormLabel>
      <Textarea id="description" name="description" bind:value={$formData.description} rows={3} />
    </FormControl>
  </FormField>
  <FormField form={form} name="variables">
    <FormControl>
      <FormLabel for="variables">Variables (JSON array)</FormLabel>
      <Textarea id="variables" name="variables" bind:value={$formData.variables} rows={3} placeholder='["x1", "x2"]' />
    </FormControl>
  </FormField>
  <FormField form={form} name="constants">
    <FormControl>
      <FormLabel for="constants">Constants (JSON array)</FormLabel>
      <Textarea id="constants" name="constants" bind:value={$formData.constants} rows={3} placeholder='["c1", "c2"]' />
    </FormControl>
  </FormField>
  <FormField form={form} name="objectives">
    <FormControl>
      <FormLabel for="objectives">Objectives (JSON array)</FormLabel>
      <Textarea id="objectives" name="objectives" bind:value={$formData.objectives} rows={3} placeholder='["f1", "f2"]' />
    </FormControl>
  </FormField>
  <FormButton>Add Problem</FormButton>
</form>
