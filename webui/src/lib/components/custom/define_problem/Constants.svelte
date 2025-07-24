<script lang="ts">
    import {
		FormFieldset,
		FormLegend
	} from '$lib/components/ui/form';
	import Input from '$lib/components/ui/input/input.svelte';
    let { form, removeConstant, addConstant, addConstantShapeDim, isTensorConstant, removeConstantShapeDim } = $props();
	const { form: formData, errors } = form;
</script>

<FormFieldset {form} name="constants">
    <FormLegend>Constants</FormLegend>
    {#if $errors.constants}<div class="text-red-500 text-sm mb-2 p-2 bg-red-50 border border-red-200 rounded">{$errors.constants}</div>{/if}
    {#if $errors.constantErrors}<div class="text-red-500 text-sm mb-2 p-2 bg-red-50 border border-red-200 rounded">{$errors.constantErrors}</div>{/if}
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
                                constant.shape = constant.shape.map((v: number, i: number) =>
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
            <Input placeholder="Values (e.g. [[2,3],[3,4]])" bind:value={constant.values} />
        {:else}
            <Input placeholder="Value (number or boolean)" bind:value={constant.value} />
        {/if}
    {/each}
    <div class="flex gap-2">
        <button type="button" class="mb-2 rounded border px-2 py-1" onclick={() => addConstant('scalar')}>+ Scalar</button>
        <button type="button" class="mb-2 rounded border px-2 py-1" onclick={() => addConstant('tensor')}>+ Tensor</button>
    </div>
</FormFieldset>