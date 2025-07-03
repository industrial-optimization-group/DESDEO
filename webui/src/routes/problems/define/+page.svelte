<script lang="ts" context="module">
	export type Variable = z.infer<typeof schemas.Variable>;
	export type TensorVariable = z.infer<typeof schemas.TensorVariable>;
	export type Constant = z.infer<typeof schemas.Constant>;
	export type TensorConstant = z.infer<typeof schemas.TensorConstant>;
	export type Objective = z.infer< typeof schemas.Objective>;
</script>

<script lang="ts">
	import {
		FormButton,
	} from '$lib/components/ui/form';
	import { superForm } from 'sveltekit-superforms';
	import { schemas } from '$lib/api/zod-schemas';
	import { z } from 'zod';
	import { Card } from '$lib/components/ui/card';
	import Objectives from '$lib/components/define_problem/Objectives.svelte';
	import Constants from '$lib/components/define_problem/Constants.svelte';
	import Variables from '$lib/components/define_problem/Variables.svelte';
	import Name from '$lib/components/define_problem/Name.svelte';
	import Description from '$lib/components/define_problem/Description.svelte';
	import SuperDebug from 'sveltekit-superforms';


	// Minimal form state for now
	const form = superForm(
		{
			name: null,
			description: null,
			variables: [] as (TensorVariable | Variable)[],
			constants: [] as (Constant | TensorConstant)[],
			objectives: [] as Objective[],
		},
		{ 
			dataType: 'json',
			onError({ result }) {
				$message = result.error.message || "Unknown error";
			}
		}
	);
	const { form: formData, message, enhance, errors } = form;

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
	function addVariableShapeDim(variable: TensorVariable) {
		variable.shape = [...variable.shape, 1];
    // Trigger Svelte reactivity
    $formData.variables = [...$formData.variables];
	}
	function removeVariableShapeDim(variable: TensorVariable, dimIdx: number) {
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

	function addObjective() { 
		const objective: Objective = {
			name: '',
			symbol: '',
			unit: null,
			func: null,
			simulator_path: null,
			surrogates: null,
			maximize: false,
			is_linear: false,
			is_convex: false,
			is_twice_differentiable: false,
			ideal: null,
			nadir: null,
			objective_type: "analytical",
			scenario_keys: null
		};
		$formData.objectives = [...$formData.objectives, objective];
	}
	function removeObjective(idx: number) { 
		$formData.objectives = $formData.objectives.filter((_, i) => i !== idx);
	}

</script>

<section class="mx-10">
	<div class="max-w-4xl mx-auto m-6">
		<h1 class="mt-10 text-center text-2xl font-semibold">Problem Definition</h1>

		{#if $message}<h3 class="text-red-500 mb-4">{$message}</h3>{/if}
		{#if $errors._errors}<div class="text-red-500 mb-4">{$errors._errors}</div>{/if}
		<form class="flex flex-col gap-4" method="POST" action="?/create" use:enhance>
			<Card class="p-6">
				<Name {form}/>
				<Description {form}/>
			</Card>

			<Variables {form} {removeVariable} {addVariable} {addVariableShapeDim} {isTensorVariable} {removeVariableShapeDim} />
			<Constants {form} {removeConstant} {addConstant} {addConstantShapeDim} {isTensorConstant} {removeConstantShapeDim} />
			<Objectives {form} {addObjective} {removeObjective} />
			<FormButton>Add Problem</FormButton
			>
		</form>
	</div>
	<SuperDebug data={$formData} />
</section>
