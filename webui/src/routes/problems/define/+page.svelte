<script lang="ts">
	import {
		FormField,
		FormLabel,
		FormButton,
		FormControl,
		FormFieldset,
		FormLegend
	} from '$lib/components/ui/form';
	import Input from '$lib/components/ui/input/input.svelte';
	import Textarea from '$lib/components/ui/textarea/textarea.svelte';
	import { superForm } from 'sveltekit-superforms';
	import { schemas } from '$lib/api/zod-types';
	import { z } from 'zod';
	import { Card } from '$lib/components/ui/card';
	type Variable = z.infer<typeof schemas.Variable>;
	type TensorVariable = z.infer<typeof schemas.TensorVariable>;
	type Constant = z.infer<typeof schemas.Constant>;
	type TensorConstant = z.infer<typeof schemas.TensorConstant>;

	// Minimal form state for now
	const form = superForm(
		{
			name: '',
			description: '',
			variables: [] as (TensorVariable | Variable)[],
			constants: [] as (Constant | TensorConstant)[],
			objectives: [] // JSON string for now
		},
		{ dataType: 'json' }
	);
	const { form: formData, enhance, errors } = form;

  function addVariable(kind: 'scalar' | 'tensor') {
        if (kind === 'scalar') {
      let variable: Variable = {
              name: '',
              symbol: '',
              variable_type: 'real',
              lowerbound: null,
              upperbound: null,
              initial_value: null
          };
      $formData.variables = [
        ...$formData.variables,
        variable
      ];
    } else {
      let variable: TensorVariable = {
              name: '',
              symbol: '',
              shape: [2],
              variable_type: 'real',
              lowerbounds: null,
              upperbounds: null,
              initial_values: null
          };
      $formData.variables = [
        ...$formData.variables,
        variable
      ];
    }
  }

	function removeVariable(idx: number) {
		$formData.variables = $formData.variables.filter((_, i) => i !== idx);
	}
	// Helpers for tensor shape
	function addShapeDim(variable: TensorVariable) {
		variable.shape = [...variable.shape, 1];
    // Trigger Svelte reactivity
    $formData.variables = [...$formData.variables];
	}
	function removeShapeDim(variable: TensorVariable, dimIdx: number) {
		if (variable.shape.length > 1) {
			variable.shape = variable.shape.filter((_, i) => i !== dimIdx);
      // Trigger Svelte reactivity
      $formData.variables = [...$formData.variables];
		}
	}
  function isTensorVariable(v: Variable | TensorVariable): v is TensorVariable {
    return Array.isArray((v as any).shape);
  }

    // Helper to add a new constant
  function addConstant(kind: 'scalar' | 'tensor') {
    if (kind === 'scalar') {
      let constant: Constant = { name: '', symbol: '', value: false };
      $formData.constants = [
        ...$formData.constants,
        constant
      ];
    } else {
      let constant: TensorConstant = { name: '', symbol: '', shape: [2], values: [] };
      $formData.constants = [
        ...$formData.constants,
        constant
      ];
    }
  }

  function removeConstant(idx: number) {
    $formData.constants = $formData.constants.filter((_, i) => i !== idx);
  }

  function addConstantShapeDim(constant: TensorConstant) {
    constant.shape = [...constant.shape, 1];
  }
  function removeConstantShapeDim(constant: TensorConstant, dimIdx: number) {
    if (constant.shape.length > 1) {
      constant.shape = constant.shape.filter((_, i) => i !== dimIdx);
    }
  }
  function isTensorConstant(v: Constant | TensorConstant): v is TensorConstant {
    return Array.isArray((v as any).shape);
  }
</script>

<section class="mx-10">
  <!-- <div>{JSON.stringify($formData.variables)}</div>
  <div>{JSON.stringify($formData.constants)}</div> -->
	<div class="max-w-4xl mx-auto m-6">
		<h1 class="mt-10 text-center text-2xl font-semibold">Problem Definition</h1>
		<form class="flex flex-col gap-4" method="POST" action="?/create" use:enhance>
			<Card class="p-6">
				<FormField {form} name="name">
					<FormControl>
						<FormLabel for="name">Name</FormLabel>
						<Input id="name" name="name" bind:value={$formData.name} />
						{#if $errors.name}
							<p>{$errors.name}</p>
						{/if}
					</FormControl>
				</FormField>
				<FormField {form} name="description">
					<FormControl>
						<FormLabel for="description">Description</FormLabel>
						<Textarea
							id="description"
							name="description"
							bind:value={$formData.description}
							rows={3}
						/>
						{#if $errors.description}
							<p>{$errors.description}</p>
						{/if}
					</FormControl>
				</FormField>
			</Card>

			<FormFieldset {form} name="variables">
				<FormLegend>Variables</FormLegend>

				{#each $formData.variables as variable, idx}
					<div>
						<button
							type="button"
							class="right-2 top-2 rounded border border-red-200 px-2 py-0.5 text-red-500"
							onclick={() => {removeVariable(idx)}}
							aria-label="Delete variable">×</button
						>
					</div>
					<Input placeholder="Name" bind:value={variable.name} />
					<Input placeholder="Symbol" bind:value={variable.symbol} />
					<select bind:value={variable.variable_type} class="rounded border px-2 py-1">
						<option value="real">real</option>
						<option value="integer">integer</option>
						<option value="binary">binary</option>
					</select>

					{#if isTensorVariable(variable)}
						<div class="col-span-2 flex items-center gap-2">
							<span>Shape:</span>
							{#each variable.shape as dim, dimIdx}
								<input
									type="number"
									min="1"
									class="w-16 rounded border px-1 py-0.5"
									bind:value={variable.shape[dimIdx]}
									oninput={(e) => {
										const target = e.target as HTMLInputElement | null;
										if (target) {
                      // Create a new array to trigger reactivity
                      variable.shape = variable.shape.map((v, i) =>
                          i === dimIdx ? Math.max(1, Number(target.value)) : v
                      );
										}
									}}
								/>
								<button
									type="button"
									class="text-red-500"
									onclick={() => removeShapeDim(variable, dimIdx)}
									disabled={variable.shape.length === 1}>–</button
								>
							{/each}
							<button type="button" class="text-green-600" onclick={() => addShapeDim(variable)}
								>+</button
							>
						</div>
						<Input placeholder="Lowerbounds (optional)" bind:value={variable.lowerbounds} />
						<Input placeholder="Upperbounds (optional)" bind:value={variable.upperbounds} />
						<Input placeholder="Initial values (optional)" bind:value={variable.initial_values} />
					{:else}
						<Input placeholder="Lowerbound (optional)" bind:value={variable.lowerbound} />
						<Input placeholder="Upperbound (optional)" bind:value={variable.upperbound} />
						<Input placeholder="Initial value (optional)" bind:value={variable.initial_value} />
					{/if}
				{/each}
          <div class="flex gap-2">
              <button type="button" class="mb-2 rounded border px-2 py-1" onclick={() => addVariable('scalar')}>+ Scalar</button>
              <button type="button" class="mb-2 rounded border px-2 py-1" onclick={() => addVariable('tensor')}>+ Tensor</button>
          </div>
			</FormFieldset>







      <FormFieldset {form} name="constants">
          <FormLegend>Constants</FormLegend>
          {#each $formData.constants as constant, idx}
              <div>
                  <button
                      type="button"
                      class="right-2 top-2 rounded border border-red-200 px-2 py-0.5 text-red-500"
                      onclick={() => removeConstant(idx)}
                      aria-label="Delete constant">×</button>
              </div>
              <Input placeholder="Name" bind:value={constant.name} />
              <Input placeholder="Symbol" bind:value={constant.symbol} />
              {#if isTensorConstant(constant)}
                  <div class="col-span-2 flex items-center gap-2">
                      <span>Shape:</span>
                      {#each constant.shape as dim, dimIdx}
                          <input
                              type="number"
                              min="1"
                              class="w-16 rounded border px-1 py-0.5"
                              bind:value={constant.shape[dimIdx]}
                              oninput={(e) => {
                                  const target = e.target as HTMLInputElement | null;
                                  if (target) {
                                      constant.shape = constant.shape.map((v, i) =>
                                          i === dimIdx ? Math.max(1, Number(target.value)) : v
                                      );
                                      $formData.constants = [...$formData.constants];
                                  }
                              }}
                          />
                          <button
                              type="button"
                              class="text-red-500"
                              onclick={() => removeConstantShapeDim(constant, dimIdx)}
                              disabled={constant.shape.length === 1}>–</button>
                      {/each}
                      <button type="button" class="text-green-600" onclick={() => { addConstantShapeDim(constant); $formData.constants = [...$formData.constants]; }}>+</button>
                  </div>
                  <Input placeholder="Values (comma separated)" bind:value={constant.values} />
              {:else}
                  <Input type="number" placeholder="Value (number or boolean)" bind:value={constant.value} />
              {/if}
          {/each}
          <div class="flex gap-2">
              <button type="button" class="mb-2 rounded border px-2 py-1" onclick={() => addConstant('scalar')}>+ Scalar</button>
              <button type="button" class="mb-2 rounded border px-2 py-1" onclick={() => addConstant('tensor')}>+ Tensor</button>
          </div>
      </FormFieldset>






			<FormField {form} name="objectives">
				<FormControl>
					<FormLabel for="objectives">Objectives (JSON array)</FormLabel>
					<Textarea
						id="objectives"
						name="objectives"
						bind:value={$formData.objectives}
						rows={3}
						placeholder="['f1', 'f2']"
					/>
				</FormControl>
			</FormField>
			<FormButton>Add Problem</FormButton
			>
		</form>
	</div>
</section>
