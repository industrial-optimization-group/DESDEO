<script lang="ts">
    import {
		FormFieldset,
		FormLegend
	} from '$lib/components/ui/form';
	import Input from '$lib/components/ui/input/input.svelte';
    let { form, addObjective, removeObjective } = $props();
	const { form: formData, errors } = form;
</script>
            
<FormFieldset {form} name="objectives">
    <FormLegend>Objectives</FormLegend>
    {#if $errors.objectives}<div class="text-red-500 text-sm mb-2 p-2 bg-red-50 border border-red-200 rounded">{$errors.objectives}</div>{/if}
    {#if $errors.objectiveErrors}<div class="text-red-500 text-sm mb-2 p-2 bg-red-50 border border-red-200 rounded">{$errors.objectiveErrors}</div>{/if}
    {#each $formData.objectives as objective, idx}
        <div>
            <button
                type="button"
                class="right-2 top-2 rounded border border-red-200 px-2 py-0.5 text-red-500"
                onclick={() => removeObjective(idx)}
                aria-label="Delete objective">×</button>
        </div>
        <Input placeholder="Name" bind:value={objective.name} />
        <Input placeholder="Symbol" bind:value={objective.symbol} />
        <Input placeholder="Unit" bind:value={objective.unit} /> <!-- optional -->
        <Input type="textarea" placeholder='Functions, e.g. ["x1 + x2", "x1 * x2"]' bind:value={objective.func} /> <!-- optional -->
        <Input placeholder="Simulator path" bind:value={objective.simulator_path} /> <!-- optional -->
        <Input placeholder='Surrogates, e.g. ["surrogate1", "surrogate2"]' bind:value={objective.surrogates} /> <!-- optional -->
        <div class="flex items-center gap-2">
            <label>
                <input type="checkbox" bind:checked={objective.maximize} />
                Maximize
            </label>
            <label>
                <input type="checkbox" bind:checked={objective.is_linear} />
                Is Linear
            </label>
            <label>
                <input type="checkbox" bind:checked={objective.is_convex} />
                Is Convex
            </label>
            <label>
                <input type="checkbox" bind:checked={objective.is_twice_differentiable} />
                Is Twice Differentiable
            </label>
        </div>
        <Input type="number" step="any" placeholder="Ideal" bind:value={objective.ideal} />
        <Input type="number" step="any" placeholder="Nadir" bind:value={objective.nadir} /> <!-- optional -->
        <select bind:value={objective.objective_type} class="rounded border px-2 py-1">
            <option value="analytical">Analytical</option>
            <option value="data_based">Data Based</option>
            <option value="simulator">Simulator</option>
            <option value="surrogate">Surrogate</option>
        </select>
        <Input type="text" placeholder='Scenario keys, e.g. ["scenario1", "scenario2"]' bind:value={objective.scenario_keys} /> <!-- optional -->
    {/each}
    <div class="flex gap-2">
        <button type="button" class="mb-2 rounded border px-2 py-1" onclick={() => addObjective()}> + </button>
    </div>
</FormFieldset>