<script lang="ts">
  import { FormField, FormLabel, FormButton, FormControl } from '$lib/components/ui/form';
  import Input from '$lib/components/ui/input/input.svelte';
  import Textarea from '$lib/components/ui/textarea/textarea.svelte';
  import { superForm } from "sveltekit-superforms";
  import type { Variable, TensorVariable } from '$lib/schemas/problem';

  // Minimal form state for now
  const form = superForm({
    name: '',
    description: '',
    variables: [] as (Variable | TensorVariable)[],
    constants: [], // JSON string for now
    objectives: [] // JSON string for now
  }, { dataType: 'json'});
  const { form: formData, enhance, errors } = form;

    let scalar: Variable = {
    name: '',
    symbol: '',
    variable_type: "real",
    lowerbound: null,
    upperbound: null,
    initial_value: null
  };

  let tensor: TensorVariable = {
    name: '',
    symbol: '',
    variable_type: "real",
    shape: [2],
    lowerbounds: null,
    upperbounds: null,
    initial_values: null
  };


  // Helper for adding/removing variables
  function addVariable() {
$formData.variables = [...$formData.variables, { ...scalar }];
      scalar =  { 
        name: '', 
        symbol: '', 
        variable_type: "real", 
        lowerbound: null, 
        upperbound: null, 
        initial_value: null }
    
  }
  function addTensorVariable() {
    $formData.variables = [  ...$formData.variables, {...tensor}];
      tensor = { 
        name: '', 
        symbol: '', 
        variable_type: "real", 
        shape: [2], 
        lowerbounds: null, 
        upperbounds: null, 
        initial_values: null }
    
  }
  function removeVariable(idx: number) {
    $formData.variables = $formData.variables.filter((_, i) => i !== idx);
  }
  // Helpers for tensor shape
  function addShapeDim(variable: TensorVariable) {
    variable.shape = [...variable.shape, 1];
  }
  function removeShapeDim(variable: TensorVariable, dimIdx: number) {
    if (variable.shape.length > 1) {
      variable.shape = variable.shape.filter((_, i) => i !== dimIdx);
    }
  }
</script>

<h1 class="mt-10 text-center text-2xl font-semibold">Problem Definition</h1>
<pre>{JSON.stringify($formData.variables, null, 2)}</pre>
<form class="max-w-xl mx-auto flex flex-col gap-4" method="POST" action="?/create" use:enhance>
  <FormField form={form} name="name">
    <FormControl>
      <FormLabel for="name">Name</FormLabel>
      <Input id="name" name="name" bind:value={$formData.name} />
      {#if $errors.name}
        <p>{$errors.name}</p>
      {/if}
    </FormControl>
  </FormField>
  <FormField form={form} name="description">
    <FormControl>
      <FormLabel for="description">Description</FormLabel>
      <Textarea id="description" name="description" bind:value={$formData.description} rows={3} />
      {#if $errors.description}
        <p>{$errors.description}</p>
      {/if}
    </FormControl>
  </FormField>

  <div class="border rounded p-4">
       <div class="border p-2 rounded bg-gray-50">
      <b>New Variable</b>
      <div class="grid grid-cols-2 gap-2 mb-2">
        <Input placeholder="Name" bind:value={scalar.name} />
        <Input placeholder="Symbol" bind:value={scalar.symbol} />
        <select bind:value={scalar.variable_type} class="border rounded px-2 py-1">
          <option value="real">real</option>
          <option value="integer">integer</option>
          <option value="binary">binary</option>
        </select>
        <Input placeholder="Lowerbound (optional)" bind:value={scalar.lowerbound} />
        <Input placeholder="Upperbound (optional)" bind:value={scalar.upperbound} />
        <Input placeholder="Initial value (optional)" bind:value={scalar.initial_value} />
      </div>
      <button type="button" class="border px-2 py-1 rounded w-full" on:click={addVariable}>Add Variable</button>
    </div>
  </div>
    <!-- Tensor variable miniform -->
  <div class="border p-2 rounded bg-gray-50">
    <b>New Tensor Variable</b>
    <div class="grid grid-cols-2 gap-2 mb-2">
      <Input placeholder="Name" bind:value={tensor.name} />
      <Input placeholder="Symbol" bind:value={tensor.symbol} />
      <select bind:value={tensor.variable_type} class="border rounded px-2 py-1">
        <option value="real">real</option>
        <option value="integer">integer</option>
        <option value="binary">binary</option>
      </select>
      <div class="col-span-2 flex items-center gap-2">
        <span>Shape:</span>
        {#each tensor.shape as dim, dimIdx}
          <input
            type="number"
            min="1"
            class="w-16 border rounded px-1 py-0.5"
            bind:value={tensor.shape[dimIdx]}
            on:input={(e) => {
              const target = e.target as HTMLInputElement | null;
              if (target) {
                tensor.shape[dimIdx] = Math.max(1, Number(target.value));
              }
            }}
          />
          <button type="button" class="text-red-500" on:click={() => removeShapeDim(tensor, dimIdx)} disabled={tensor.shape.length === 1}>–</button>
        {/each}
        <button type="button" class="text-green-600" on:click={()=>addShapeDim(tensor)}>+</button>
      </div>
      <Input placeholder="Lowerbounds (optional)" bind:value={tensor.lowerbounds} />
      <Input placeholder="Upperbounds (optional)" bind:value={tensor.upperbounds} />
      <Input placeholder="Initial values (optional)" bind:value={tensor.initial_values} />
    </div>
    <button type="button" class="border px-2 py-1 rounded w-full" on:click={addTensorVariable}>Add Tensor Variable</button>
  </div>
  
  <!-- List of added variables -->
  {#each $formData.variables as variable, idx}
    <div class="border p-2 mb-2 rounded bg-gray-50">
      <div class="flex justify-between items-center mb-1">
        <b>{'shape' in variable ? 'Tensor Variable' : 'Variable'} #{idx + 1}</b>
        <button type="button" class="text-red-600" on:click={() => removeVariable(idx)}>Remove</button>
      </div>
      <div class="grid grid-cols-2 gap-2">
        <Input placeholder="Name" bind:value={variable.name} />
        <Input placeholder="Symbol" bind:value={variable.symbol} />
        <select bind:value={variable.variable_type} class="border rounded px-2 py-1">
          <option value="real">real</option>
          <option value="integer">integer</option>
          <option value="binary">binary</option>
        </select>
        {#if 'shape' in variable}
          <div class="col-span-2 flex items-center gap-2">
            <span>Shape:</span>
            {#each variable.shape as dim, dimIdx}
              <input
                type="number"
                min="1"
                class="w-16 border rounded px-1 py-0.5"
                bind:value={variable.shape[dimIdx]}
                on:input={(e) => {
                  const target = e.target as HTMLInputElement | null;
                  if (target) {
                    variable.shape[dimIdx] = Math.max(1, Number(target.value));
                  }
                }}
              />
              <button type="button" class="text-red-500" on:click={() => removeShapeDim(variable, dimIdx)} disabled={variable.shape.length === 1}>–</button>
            {/each}
            <button type="button" class="text-green-600" on:click={() => addShapeDim(variable)}>+</button>
          </div>
          <Input placeholder="Lowerbounds (optional)" bind:value={variable.lowerbounds} />
          <Input placeholder="Upperbounds (optional)" bind:value={variable.upperbounds} />
          <Input placeholder="Initial values (optional)" bind:value={variable.initial_values} />
        {:else}
          <Input placeholder="Lowerbound (optional)" bind:value={variable.lowerbound} />
          <Input placeholder="Upperbound (optional)" bind:value={variable.upperbound} />
          <Input placeholder="Initial value (optional)" bind:value={variable.initial_value} />
        {/if}
      </div>
    </div>
  {/each}

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
