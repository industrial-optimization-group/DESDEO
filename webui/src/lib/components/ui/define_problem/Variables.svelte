<script lang="ts">
    	import {
		FormFieldset,
		FormLegend
	} from '$lib/components/ui/form';
	import Input from '$lib/components/ui/input/input.svelte';
	import type { SuperForm } from 'sveltekit-superforms';
	import type { TensorVariable, Variable } from '../../../../routes/problems/define/+page.svelte';
    
    export let form: SuperForm<any>;
	const { form: formData } = form;
    export let removeVariable: (idx: number) => void;
    export let addVariable: (kind: 'scalar' | 'tensor') => void;
    export let addVariableShapeDim: (Variable: TensorVariable) => void;
    export let isTensorVariable: (v: Variable | TensorVariable) => v is TensorVariable;
    export let removeVariableShapeDim: (Variable: TensorVariable, dimIdx: number) => void;
</script>

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
                        onclick={() => removeVariableShapeDim(variable, dimIdx)}
                        disabled={variable.shape.length === 1}>–</button
                    >
                {/each}
                <button type="button" class="text-green-600" onclick={() => addVariableShapeDim(variable)}
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