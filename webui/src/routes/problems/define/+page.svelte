<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import Card from '$lib/components/ui/card/card.svelte';
	import * as Tabs from '$lib/components/ui/tabs';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import type { ConstraintDB, ObjectiveDB, VariableDB } from '$lib/gen/models';
	import {
		ConstraintTypeEnum,
		ObjectiveTypeEnum,
		VariableTypeEnum
	} from '$lib/gen/models';
	import { createProblem, fetchProblem, type ProblemPayload, uploadProblemJson } from './handler';

	type VariableForm = {
		name: string;
		symbol: string;
		variable_type: VariableDB['variable_type'];
		lowerbound: string;
		upperbound: string;
		initial_value: string;
	};

	type ObjectiveForm = {
		name: string;
		symbol: string;
		func: string;
		description: string;
		unit: string;
		maximize: boolean;
		ideal: string;
		nadir: string;
		objective_type: ObjectiveDB['objective_type'];
		is_linear: boolean;
		is_convex: boolean;
		is_twice_differentiable: boolean;
		scenario_keys: string;
		simulator_path: string;
		surrogates: string;
	};

	type ConstraintForm = {
		name: string;
		symbol: string;
		func: string;
		cons_type: ConstraintDB['cons_type'];
		is_linear: boolean;
		is_convex: boolean;
		is_twice_differentiable: boolean;
		scenario_keys: string;
		simulator_path: string;
		surrogates: string;
	};

	type ConstantForm = {
		name: string;
		symbol: string;
		value: string;
	};

	const variableTypeOptions = Object.values(VariableTypeEnum);
	const objectiveTypeOptions = Object.values(ObjectiveTypeEnum);
	const constraintTypeOptions = Object.values(ConstraintTypeEnum);

	const emptyVariable = (): VariableForm => ({
		name: '',
		symbol: '',
		variable_type: VariableTypeEnum.real,
		lowerbound: '',
		upperbound: '',
		initial_value: ''
	});

	const emptyObjective = (): ObjectiveForm => ({
		name: '',
		symbol: '',
		func: '',
		description: '',
		unit: '',
		maximize: false,
		ideal: '',
		nadir: '',
		objective_type: ObjectiveTypeEnum.analytical,
		is_linear: false,
		is_convex: false,
		is_twice_differentiable: false,
		scenario_keys: '',
		simulator_path: '',
		surrogates: ''
	});

	const emptyConstraint = (): ConstraintForm => ({
		name: '',
		symbol: '',
		func: '',
		cons_type: ConstraintTypeEnum['<='],
		is_linear: true,
		is_convex: false,
		is_twice_differentiable: false,
		scenario_keys: '',
		simulator_path: '',
		surrogates: ''
	});

	const emptyConstant = (): ConstantForm => ({
		name: '',
		symbol: '',
		value: ''
	});

	let mode = $state<string>('form'); // 'upload' | 'form'
	let isSubmitting = $state(false);
	let formErrors = $state<string[]>([]);
	let successMessage = $state<string | null>(null);
	let apiError = $state<string | null>(null);
	let showAdvanced = $state(false);

	let name = $state('');
	let description = $state('');
	let scenarioKeys = $state('');
	let isConvexSelection = $state<'auto' | 'true' | 'false'>('auto');
	let isLinearSelection = $state<'auto' | 'true' | 'false'>('auto');
	let isTwiceDifferentiableSelection = $state<'auto' | 'true' | 'false'>('auto');

	let variables = $state<VariableForm[]>([emptyVariable()]);
	let objectives = $state<ObjectiveForm[]>([emptyObjective()]);
	let constraints = $state<ConstraintForm[]>([]);
	let constants = $state<ConstantForm[]>([]);

	let jsonFile = $state<File | null>(null);

	const parseNumber = (value: string): number | null => {
		if (value.trim() === '') return null;
		const parsed = Number(value);
		return Number.isFinite(parsed) ? parsed : null;
	};

	const parseJsonArray = (value: string): unknown[] | null => {
		if (value.trim() === '') return null;
		const parsed = JSON.parse(value);
		if (!Array.isArray(parsed)) {
			throw new Error('Expected a JSON array.');
		}
		return parsed;
	};

	const parseFunctionValue = (value: string): unknown[] | string | null => {
		const trimmed = value.trim();
		if (trimmed === '') return null;
		try {
			const parsed = JSON.parse(trimmed);
			if (Array.isArray(parsed)) return parsed;
			if (typeof parsed === 'string') return parsed;
			return trimmed;
		} catch (error) {
			return trimmed;
		}
	};

	const toStringList = (value: string): string[] | null => {
		const items = value
			.split(',')
			.map((entry) => entry.trim())
			.filter(Boolean);
		return items.length > 0 ? items : null;
	};

	const addVariable = () => {
		variables = [...variables, emptyVariable()];
	};

	const addObjective = () => {
		objectives = [...objectives, emptyObjective()];
	};

	const addConstraint = () => {
		constraints = [...constraints, emptyConstraint()];
	};

	const addConstant = () => {
		constants = [...constants, emptyConstant()];
	};

	const _duplicateItem = <T>(items: T[], index: number) => {
		const next = [...items];
		next.splice(index + 1, 0, structuredClone(items[index]));
		return next;
	};

	const duplicateItem = <T extends Record<string, any>>(items: T[], index: number) => {
		const item = items[index];

		const clone = {
			...item,
		};

		const next = [...items];
		next.splice(index + 1, 0, clone);
		return next;
	};

	const removeItem = <T>(items: T[], index: number) => items.filter((_, i) => i !== index);

	const validateForm = () => {
		const errors: string[] = [];
		if (!name.trim()) errors.push('Problem name is required.');
		if (!description.trim()) errors.push('Problem description is required.');
		if (variables.length === 0) errors.push('At least one variable is required.');
		if (objectives.length === 0) errors.push('At least one objective is required.');

		variables.forEach((variable, index) => {
			if (!variable.name.trim()) errors.push(`Variable ${index + 1}: name is required.`);
			if (!variable.symbol.trim()) errors.push(`Variable ${index + 1}: symbol is required.`);
			if (!variable.variable_type) errors.push(`Variable ${index + 1}: type is required.`);
			const lower = parseNumber(variable.lowerbound);
			const upper = parseNumber(variable.upperbound);
			if (variable.lowerbound.trim() && lower === null)
				errors.push(`Variable ${index + 1}: lower bound must be a number.`);
			if (variable.upperbound.trim() && upper === null)
				errors.push(`Variable ${index + 1}: upper bound must be a number.`);
			if (lower !== null && upper !== null && lower >= upper) {
				errors.push(`Variable ${index + 1}: lower bound must be less than upper bound.`);
			}
			if (variable.initial_value.trim() && parseNumber(variable.initial_value) === null) {
				errors.push(`Variable ${index + 1}: initial value must be a number.`);
			}
		});

		objectives.forEach((objective, index) => {
			if (!objective.name.trim()) errors.push(`Objective ${index + 1}: name is required.`);
			if (!objective.symbol.trim()) errors.push(`Objective ${index + 1}: symbol is required.`);
			if (objective.ideal.trim() && parseNumber(objective.ideal) === null) {
				errors.push(`Objective ${index + 1}: ideal must be a number.`);
			}
			if (objective.nadir.trim() && parseNumber(objective.nadir) === null) {
				errors.push(`Objective ${index + 1}: nadir must be a number.`);
			}
		});

		constraints.forEach((constraint, index) => {
			if (!constraint.name.trim()) errors.push(`Constraint ${index + 1}: name is required.`);
			if (!constraint.symbol.trim()) errors.push(`Constraint ${index + 1}: symbol is required.`);
			if (!constraint.cons_type) errors.push(`Constraint ${index + 1}: type is required.`);
			if (!constraint.func.trim()) {
				errors.push(`Constraint ${index + 1}: func is required.`);
			}
		});

		constants.forEach((constant, index) => {
			if (!constant.name.trim()) errors.push(`Constant ${index + 1}: name is required.`);
			if (!constant.symbol.trim()) errors.push(`Constant ${index + 1}: symbol is required.`);
			if (constant.value.trim() === '' || parseNumber(constant.value) === null) {
				errors.push(`Constant ${index + 1}: value must be a number.`);
			}
		});

		return errors;
	};

	const parseTriState = (value: 'auto' | 'true' | 'false'): boolean | null => {
		if (value === 'auto') return null;
		return value === 'true';
	};

	const buildPayload = (): ProblemPayload => ({
		name: name.trim(),
		description: description.trim(),
		variables: variables.map((variable) => ({
			name: variable.name.trim(),
			symbol: variable.symbol.trim(),
			variable_type: variable.variable_type,
			lowerbound: parseNumber(variable.lowerbound),
			upperbound: parseNumber(variable.upperbound),
			initial_value: parseNumber(variable.initial_value)
		})),
		objectives: objectives.map((objective) => ({
			name: objective.name.trim(),
			symbol: objective.symbol.trim(),
			description: objective.description.trim() || null,
			unit: objective.unit.trim() || null,
			func: parseFunctionValue(objective.func),
			maximize: objective.maximize,
			ideal: parseNumber(objective.ideal),
			nadir: parseNumber(objective.nadir),
			objective_type: objective.objective_type,
			is_linear: objective.is_linear,
			is_convex: objective.is_convex,
			is_twice_differentiable: objective.is_twice_differentiable,
			scenario_keys: showAdvanced ? toStringList(objective.scenario_keys) : null,
			simulator_path: showAdvanced ? objective.simulator_path.trim() || null : null,
			surrogates: showAdvanced ? toStringList(objective.surrogates) : null
		})),
		constraints:
			constraints.length > 0
				? constraints.map((constraint) => ({
						name: constraint.name.trim(),
						symbol: constraint.symbol.trim(),
						func: parseFunctionValue(constraint.func) ?? '',
						cons_type: constraint.cons_type,
						is_linear: constraint.is_linear,
						is_convex: constraint.is_convex,
						is_twice_differentiable: constraint.is_twice_differentiable,
						scenario_keys: showAdvanced ? toStringList(constraint.scenario_keys) : null,
						simulator_path: showAdvanced ? constraint.simulator_path.trim() || null : null,
						surrogates: showAdvanced ? toStringList(constraint.surrogates) : null
					}))
				: null,
		constants:
			constants.length > 0
				? constants.map((constant) => ({
						name: constant.name.trim(),
						symbol: constant.symbol.trim(),
						value: parseNumber(constant.value) ?? 0
					}))
				: null,
		scenario_keys: showAdvanced ? toStringList(scenarioKeys) : null,
		is_convex: parseTriState(isConvexSelection),
		is_linear: parseTriState(isLinearSelection),
		is_twice_differentiable: parseTriState(isTwiceDifferentiableSelection)
	});

	const handleClearForm = () => {
		name = '';
		description = '';
		scenarioKeys = '';
		isConvexSelection = 'auto';
		isLinearSelection = 'auto';
		isTwiceDifferentiableSelection = 'auto';
		showAdvanced = false;
		variables = [emptyVariable()];
		objectives = [emptyObjective()];
		constraints = [];
		constants = [];
		formErrors = [];
		apiError = null;
		successMessage = null;
	};

	const handleSubmit = async () => {
		formErrors = [];
		apiError = null;
		successMessage = null;

		const errors = validateForm();
		if (errors.length > 0) {
			formErrors = errors;
			return;
		}

		isSubmitting = true;
		const response = await createProblem(buildPayload());
		isSubmitting = false;

		if (!response.ok) {
			apiError = response.error;
			return;
		}

		successMessage = `Problem \"${response.data.name}\" created successfully. Redirecting...`;
		setTimeout(() => {
			goto('/problems');
		}, 800);
	};

	const handleJsonUpload = async () => {
		apiError = null;
		successMessage = null;

		if (!jsonFile) {
			apiError = 'Please select a JSON file to upload.';
			return;
		}

		isSubmitting = true;
		const response = await uploadProblemJson({ json_file: jsonFile });
		isSubmitting = false;

		if (!response.ok) {
			apiError = response.error;
			return;
		}

		successMessage = `Problem \"${response.data.name}\" created successfully. Redirecting...`;
		setTimeout(() => {
			goto('/problems');
		}, 800);
	};

	const populateFormFromData = (parsed: Partial<ProblemPayload>) => {
		let hasAdvanced = false;
		if (parsed.name) name = parsed.name;
		if (parsed.description) description = parsed.description;
		if (parsed.scenario_keys) {
			scenarioKeys = parsed.scenario_keys.join(', ');
			hasAdvanced = true;
		}
		isConvexSelection = parsed.is_convex === null || parsed.is_convex === undefined ? 'auto' : parsed.is_convex ? 'true' : 'false';
		isLinearSelection = parsed.is_linear === null || parsed.is_linear === undefined ? 'auto' : parsed.is_linear ? 'true' : 'false';
		isTwiceDifferentiableSelection =
			parsed.is_twice_differentiable === null || parsed.is_twice_differentiable === undefined
				? 'auto'
				: parsed.is_twice_differentiable
					? 'true'
					: 'false';

		if (parsed.variables && parsed.variables.length > 0) {
			variables = parsed.variables.map((variable) => ({
				name: variable.name ?? '',
				symbol: variable.symbol ?? '',
				variable_type: variable.variable_type ?? VariableTypeEnum.real,
				lowerbound: variable.lowerbound?.toString() ?? '',
				upperbound: variable.upperbound?.toString() ?? '',
				initial_value: variable.initial_value?.toString() ?? ''
			}));
		}

		if (parsed.objectives && parsed.objectives.length > 0) {
			objectives = parsed.objectives.map((objective) => ({
				name: objective.name ?? '',
				symbol: objective.symbol ?? '',
				func:
					typeof objective.func === 'string'
						? objective.func
						: objective.func
							? JSON.stringify(objective.func, null, 2)
							: '',
				description: objective.description ?? '',
				unit: objective.unit ?? '',
				maximize: objective.maximize ?? false,
				ideal: objective.ideal?.toString() ?? '',
				nadir: objective.nadir?.toString() ?? '',
				objective_type: objective.objective_type ?? ObjectiveTypeEnum.analytical,
				is_linear: objective.is_linear ?? false,
				is_convex: objective.is_convex ?? false,
				is_twice_differentiable: objective.is_twice_differentiable ?? false,
				scenario_keys: objective.scenario_keys?.join(', ') ?? '',
				simulator_path:
					typeof objective.simulator_path === 'string'
						? objective.simulator_path
						: objective.simulator_path && 'url' in objective.simulator_path
							? String(objective.simulator_path.url ?? '')
							: '',
				surrogates: objective.surrogates?.join(', ') ?? ''
			}));

			if (parsed.objectives.some((objective) => objective.scenario_keys || objective.surrogates || objective.simulator_path)) {
				hasAdvanced = true;
			}
		}

		if (parsed.constraints && parsed.constraints.length > 0) {
			constraints = parsed.constraints.map((constraint) => ({
				name: constraint.name ?? '',
				symbol: constraint.symbol ?? '',
				func:
					typeof constraint.func === 'string'
						? constraint.func
						: JSON.stringify(constraint.func ?? [], null, 2),
				cons_type: constraint.cons_type ?? ConstraintTypeEnum['<='],
				is_linear: constraint.is_linear ?? true,
				is_convex: constraint.is_convex ?? false,
				is_twice_differentiable: constraint.is_twice_differentiable ?? false,
				scenario_keys: constraint.scenario_keys?.join(', ') ?? '',
				simulator_path:
					typeof constraint.simulator_path === 'string'
						? constraint.simulator_path
						: constraint.simulator_path && 'url' in constraint.simulator_path
							? String(constraint.simulator_path.url ?? '')
							: '',
				surrogates: constraint.surrogates?.join(', ') ?? ''
			}));

			if (parsed.constraints.some((constraint) => constraint.scenario_keys || constraint.surrogates || constraint.simulator_path)) {
				hasAdvanced = true;
			}
		}

		if (parsed.constants && parsed.constants.length > 0) {
			constants = parsed.constants.map((constant) => ({
				name: constant.name ?? '',
				symbol: constant.symbol ?? '',
				value: constant.value?.toString() ?? ''
			}));
		}

		showAdvanced = hasAdvanced;
		mode = 'form';
	};

	const handlePopulateFromJson = async () => {
		apiError = null;
		successMessage = null;

		if (!jsonFile) {
			apiError = 'Please select a JSON file to populate the form.';
			return;
		}

		const jsonText = await jsonFile.text();
		try {
			const parsed = JSON.parse(jsonText) as Partial<ProblemPayload>;
			populateFormFromData(parsed);
		} catch (error) {
			console.error('Failed to parse JSON', error);
			apiError = 'Invalid JSON file.';
		}
	};

	onMount(async () => {
		const editId = page.url.searchParams.get('edit');
		if (!editId) return;

		const problemId = Number(editId);
		if (Number.isNaN(problemId)) return;

		const response = await fetchProblem(problemId);
		if (!response.ok) {
			apiError = response.error;
			return;
		}

		populateFormFromData(response.data as unknown as Partial<ProblemPayload>);
	});
</script>

<section class="mx-10">
	<div class="m-6 mx-auto max-w-6xl">
		<h1 class="mt-10 text-center text-2xl font-semibold">Problem Definition</h1>

		<Tabs.Root value={mode} class="mt-6 w-full" onValueChange={(value) => (mode = value)}>
			<Tabs.List class="w-full">
				<Tabs.Trigger value="form">Define via Form</Tabs.Trigger>
				<Tabs.Trigger value="upload">Upload JSON</Tabs.Trigger>
			</Tabs.List>

			<Tabs.Content value="upload" class="w-full">
				<Card class="mt-4 p-6">
					<div class="flex flex-col gap-4">
						<div class="flex flex-col gap-2">
							<Label for="json-file">JSON file</Label>
							<Input
								id="json-file"
								type="file"
								accept=".json"
								onchange={(event) => {
									const target = event.currentTarget as HTMLInputElement;
									jsonFile = target.files?.[0] ?? null;
								}}
							/>
						</div>
						<div class="flex flex-wrap gap-2">
							<Button type="button" disabled={isSubmitting} onclick={handleJsonUpload}>
								{isSubmitting ? 'Uploading…' : 'Submit JSON'}
							</Button>
							<Button type="button" variant="outline" onclick={handlePopulateFromJson} disabled={isSubmitting}>
								Populate form from JSON
							</Button>
						</div>
						{#if apiError}
							<Card class="border-destructive/40 bg-destructive/10 p-4 text-sm">
								{apiError}
							</Card>
						{/if}
						{#if successMessage}
							<Card class="border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
								{successMessage}
							</Card>
						{/if}
					</div>
				</Card>
			</Tabs.Content>

			<Tabs.Content value="form" class="w-full">
				<Card class="mt-4 p-6">
					<div class="grid gap-6">
						<div class="grid gap-4">
							<div class="grid gap-2">
								<Label for="problem-name">Name</Label>
								<Input id="problem-name" bind:value={name} placeholder="Problem name" required />
							</div>
							<div class="grid gap-2">
								<Label for="problem-description">Description</Label>
								<Textarea
									id="problem-description"
									bind:value={description}
									placeholder="Describe the problem"
									required
								/>
							</div>
							<label class="flex items-center gap-2 text-sm">
								<Checkbox bind:checked={showAdvanced} />
								Show advanced fields
							</label>
							{#if showAdvanced}
								<div class="grid gap-2">
									<Label for="problem-scenario-keys">Scenario keys (comma separated)</Label>
									<Input id="problem-scenario-keys" bind:value={scenarioKeys} />
								</div>
								<div class="grid gap-3">
									<Label>Problem characteristics</Label>
									<div class="grid gap-2 md:grid-cols-3">
										<div class="grid gap-2">
											<Label class="text-xs text-muted-foreground">Linear</Label>
											<Select.Root bind:value={isLinearSelection} type="single">
												<Select.Trigger>{isLinearSelection}</Select.Trigger>
												<Select.Content>
													<Select.Item value="auto">auto</Select.Item>
													<Select.Item value="true">true</Select.Item>
													<Select.Item value="false">false</Select.Item>
												</Select.Content>
											</Select.Root>
										</div>
										<div class="grid gap-2">
											<Label class="text-xs text-muted-foreground">Convex</Label>
											<Select.Root bind:value={isConvexSelection} type="single">
												<Select.Trigger>{isConvexSelection}</Select.Trigger>
												<Select.Content>
													<Select.Item value="auto">auto</Select.Item>
													<Select.Item value="true">true</Select.Item>
													<Select.Item value="false">false</Select.Item>
												</Select.Content>
											</Select.Root>
										</div>
										<div class="grid gap-2">
											<Label class="text-xs text-muted-foreground">Twice differentiable</Label>
											<Select.Root bind:value={isTwiceDifferentiableSelection} type="single">
												<Select.Trigger>{isTwiceDifferentiableSelection}</Select.Trigger>
												<Select.Content>
													<Select.Item value="auto">auto</Select.Item>
													<Select.Item value="true">true</Select.Item>
													<Select.Item value="false">false</Select.Item>
												</Select.Content>
											</Select.Root>
										</div>
									</div>
								</div>
							{/if}
						</div>

						<div class="grid gap-3">
							<div class="flex items-center justify-between">
								<h2 class="text-lg font-semibold">Constants</h2>
								<Button type="button" variant="outline" onclick={addConstant}>
									Add constant
								</Button>
							</div>
							{#if constants.length === 0}
								<p class="text-muted-foreground text-sm">No constants added yet.</p>
							{/if}
							<div class="grid gap-4">
								{#each constants as constant, index}
									<details class="rounded-lg border">
										<summary class="flex cursor-pointer items-center justify-between gap-2 px-4 py-3 text-sm font-semibold">
											<span>
												Constant {index + 1}{constant.name || constant.symbol ? ` — ${constant.name || constant.symbol}` : ''}
											</span>
										</summary>
										<div class="grid gap-4 px-4 pb-4">
											<div class="flex items-center justify-end gap-2">
												<Button
													type="button"
													variant="ghost"
													onclick={() => (constants = duplicateItem(constants, index))}
												>
													Duplicate
												</Button>
												<Button
													type="button"
													variant="ghost"
													onclick={() => (constants = removeItem(constants, index))}
												>
													Remove
												</Button>
											</div>
											<div class="grid gap-2 md:grid-cols-3">
												<div class="grid gap-2">
													<Label>Name</Label>
													<Input bind:value={constant.name} placeholder="Constant name" />
												</div>
												<div class="grid gap-2">
													<Label>Symbol</Label>
													<Input bind:value={constant.symbol} placeholder="c_1" />
												</div>
												<div class="grid gap-2">
													<Label>Value</Label>
													<Input bind:value={constant.value} placeholder="e.g., 1.0" />
												</div>
											</div>
										</div>
									</details>
								{/each}
							</div>
						</div>

						<div class="grid gap-3">
							<div class="flex items-center justify-between">
								<h2 class="text-lg font-semibold">Variables</h2>
								<Button type="button" variant="outline" onclick={addVariable}>
									Add variable
								</Button>
							</div>
							<div class="grid gap-4">
								{#each variables as variable, index}
									<details class="rounded-lg border">
										<summary class="flex cursor-pointer items-center justify-between gap-2 px-4 py-3 text-sm font-semibold">
											<span>
												Variable {index + 1}{variable.name || variable.symbol ? ` — ${variable.name || variable.symbol}` : ''}
											</span>
										</summary>
										<div class="grid gap-4 px-4 pb-4">
											<div class="flex items-center justify-end gap-2">
												<Button
													type="button"
													variant="ghost"
													onclick={() => (variables = duplicateItem(variables, index))}
												>
													Duplicate
												</Button>
												<Button
													type="button"
													variant="ghost"
													onclick={() => (variables = removeItem(variables, index))}
												>
													Remove
												</Button>
											</div>
											<div class="grid gap-2 md:grid-cols-2">
												<div class="grid gap-2">
													<Label>Name</Label>
													<Input bind:value={variable.name} placeholder="Variable name" />
												</div>
												<div class="grid gap-2">
													<Label>Symbol</Label>
													<Input bind:value={variable.symbol} placeholder="x_1" />
												</div>
												<div class="grid gap-2">
													<Label>Type</Label>
													<Select.Root bind:value={variable.variable_type} type="single">
														<Select.Trigger>{variable.variable_type}</Select.Trigger>
														<Select.Content>
															{#each variableTypeOptions as option}
																<Select.Item value={option}>{option}</Select.Item>
															{/each}
														</Select.Content>
													</Select.Root>
												</div>
												<div class="grid gap-2">
													<Label>Initial value</Label>
													<Input bind:value={variable.initial_value} placeholder="Optional" />
												</div>
												<div class="grid gap-2">
													<Label>Lower bound</Label>
													<Input bind:value={variable.lowerbound} placeholder="Optional" />
												</div>
												<div class="grid gap-2">
													<Label>Upper bound</Label>
													<Input bind:value={variable.upperbound} placeholder="Optional" />
												</div>
											</div>
										</div>
									</details>
								{/each}
							</div>
						</div>

						<div class="grid gap-3">
							<div class="flex items-center justify-between">
								<h2 class="text-lg font-semibold">Objectives</h2>
								<Button type="button" variant="outline" onclick={addObjective}>
									Add objective
								</Button>
							</div>
							<div class="grid gap-4">
								{#each objectives as objective, index}
									<details class="rounded-lg border">
										<summary class="flex cursor-pointer items-center justify-between gap-2 px-4 py-3 text-sm font-semibold">
											<span>
												Objective {index + 1}{objective.name || objective.symbol ? ` — ${objective.name || objective.symbol}` : ''}
											</span>
										</summary>
										<div class="grid gap-4 px-4 pb-4">
											<div class="flex items-center justify-end gap-2">
												<Button
													type="button"
													variant="ghost"
													onclick={() => (objectives = duplicateItem(objectives, index))}
												>
													Duplicate
												</Button>
												<Button
													type="button"
													variant="ghost"
													onclick={() => (objectives = removeItem(objectives, index))}
												>
													Remove
												</Button>
											</div>
											<div class="grid gap-2 md:grid-cols-2">
												<div class="grid gap-2">
													<Label>Name</Label>
													<Input bind:value={objective.name} placeholder="Objective name" />
												</div>
												<div class="grid gap-2">
													<Label>Symbol</Label>
													<Input bind:value={objective.symbol} placeholder="f_1" />
												</div>
												<div class="grid gap-2">
													<Label>Type</Label>
													<Select.Root bind:value={objective.objective_type} type="single">
														<Select.Trigger>{objective.objective_type}</Select.Trigger>
														<Select.Content>
															{#each objectiveTypeOptions as option}
																<Select.Item value={option}>{option}</Select.Item>
															{/each}
														</Select.Content>
													</Select.Root>
												</div>
												<div class="grid gap-2">
													<Label>Unit</Label>
													<Input bind:value={objective.unit} placeholder="Optional" />
												</div>
											</div>
											<div class="grid gap-2">
												<Label>Function (string or JSON array)</Label>
												<Textarea bind:value={objective.func} placeholder="x_1 + x_2 or ['Add', 'x_1', 'x_2']" />
											</div>
											<div class="grid gap-2 md:grid-cols-2">
												<div class="grid gap-2">
													<Label>Ideal</Label>
													<Input bind:value={objective.ideal} placeholder="Optional" />
												</div>
												<div class="grid gap-2">
													<Label>Nadir</Label>
													<Input bind:value={objective.nadir} placeholder="Optional" />
												</div>
												<div class="grid gap-2">
													<Label>Description</Label>
													<Input bind:value={objective.description} placeholder="Optional" />
												</div>
											</div>
											{#if showAdvanced}
												<div class="grid gap-2 md:grid-cols-2">
													<div class="grid gap-2">
														<Label>Scenario keys (comma separated)</Label>
														<Input bind:value={objective.scenario_keys} placeholder="Optional" />
													</div>
													<div class="grid gap-2">
														<Label>Simulator path or URL</Label>
														<Input bind:value={objective.simulator_path} placeholder="Optional" />
													</div>
													<div class="grid gap-2">
														<Label>Surrogates (comma separated)</Label>
														<Input bind:value={objective.surrogates} placeholder="Optional" />
													</div>
												</div>
											{/if}
											<div class="flex flex-wrap gap-4">
												<label class="flex items-center gap-2 text-sm">
													<Checkbox bind:checked={objective.maximize} />
													Maximize
												</label>
												<label class="flex items-center gap-2 text-sm">
													<Checkbox bind:checked={objective.is_linear} />
													Linear
												</label>
												<label class="flex items-center gap-2 text-sm">
													<Checkbox bind:checked={objective.is_convex} />
													Convex
												</label>
												<label class="flex items-center gap-2 text-sm">
													<Checkbox bind:checked={objective.is_twice_differentiable} />
													Twice differentiable
												</label>
											</div>
										</div>
									</details>
								{/each}
							</div>
						</div>

						<div class="grid gap-3">
							<div class="flex items-center justify-between">
								<h2 class="text-lg font-semibold">Constraints</h2>
								<Button type="button" variant="outline" onclick={addConstraint}>
									Add constraint
								</Button>
							</div>
							{#if constraints.length === 0}
								<p class="text-muted-foreground text-sm">No constraints added yet.</p>
							{/if}
							<div class="grid gap-4">
								{#each constraints as constraint, index}
									<details class="rounded-lg border">
										<summary class="flex cursor-pointer items-center justify-between gap-2 px-4 py-3 text-sm font-semibold">
											<span>
												Constraint {index + 1}{constraint.name || constraint.symbol ? ` — ${constraint.name || constraint.symbol}` : ''}
											</span>
										</summary>
										<div class="grid gap-4 px-4 pb-4">
											<div class="flex items-center justify-end gap-2">
												<Button
													type="button"
													variant="ghost"
													onclick={() => (constraints = duplicateItem(constraints, index))}
												>
													Duplicate
												</Button>
												<Button
													type="button"
													variant="ghost"
													onclick={() => (constraints = removeItem(constraints, index))}
												>
													Remove
												</Button>
											</div>
											<div class="grid gap-2 md:grid-cols-2">
												<div class="grid gap-2">
													<Label>Name</Label>
													<Input bind:value={constraint.name} placeholder="Constraint name" />
												</div>
												<div class="grid gap-2">
													<Label>Symbol</Label>
													<Input bind:value={constraint.symbol} placeholder="g_1" />
												</div>
												<div class="grid gap-2">
													<Label>Type</Label>
													<Select.Root bind:value={constraint.cons_type} type="single">
														<Select.Trigger>{constraint.cons_type}</Select.Trigger>
														<Select.Content>
															{#each constraintTypeOptions as option}
																<Select.Item value={option}>{option}</Select.Item>
															{/each}
														</Select.Content>
													</Select.Root>
												</div>
											</div>
											<div class="grid gap-2">
												<Label>Function (string or JSON array)</Label>
												<Textarea bind:value={constraint.func} placeholder="The left hand side of the expression: e.g., x_1 + x_2 or ['Add', 'x_1', 'x_2']" />
											</div>
											{#if showAdvanced}
												<div class="grid gap-2 md:grid-cols-2">
													<div class="grid gap-2">
														<Label>Scenario keys (comma separated)</Label>
														<Input bind:value={constraint.scenario_keys} placeholder="Optional" />
													</div>
													<div class="grid gap-2">
														<Label>Simulator path or URL</Label>
														<Input bind:value={constraint.simulator_path} placeholder="Optional" />
													</div>
													<div class="grid gap-2">
														<Label>Surrogates (comma separated)</Label>
														<Input bind:value={constraint.surrogates} placeholder="Optional" />
													</div>
												</div>
											{/if}
											<div class="flex flex-wrap gap-4">
												<label class="flex items-center gap-2 text-sm">
													<Checkbox bind:checked={constraint.is_linear} />
													Linear
												</label>
												<label class="flex items-center gap-2 text-sm">
													<Checkbox bind:checked={constraint.is_convex} />
													Convex
												</label>
												<label class="flex items-center gap-2 text-sm">
													<Checkbox bind:checked={constraint.is_twice_differentiable} />
													Twice differentiable
												</label>
											</div>
										</div>
									</details>
								{/each}
							</div>
						</div>

						<div class="flex flex-col gap-3">
							{#if formErrors.length > 0}
								<Card class="border-destructive/40 bg-destructive/10 p-4 text-sm">
									<ul class="list-disc space-y-1 pl-4">
										{#each formErrors as error}
											<li>{error}</li>
										{/each}
									</ul>
								</Card>
							{/if}
							{#if apiError}
								<Card class="border-destructive/40 bg-destructive/10 p-4 text-sm">
									{apiError}
								</Card>
							{/if}
							{#if successMessage}
								<Card class="border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
									{successMessage}
								</Card>
							{/if}
							<div class="flex flex-wrap gap-2">
								<Button type="button" variant="outline" onclick={handleClearForm} disabled={isSubmitting}>
									Clear form
								</Button>
								<Button type="button" disabled={isSubmitting} onclick={handleSubmit}>
									{isSubmitting ? 'Submitting…' : 'Create problem'}
								</Button>
							</div>
						</div>
					</div>
				</Card>
			</Tabs.Content>
		</Tabs.Root>
	</div>
</section>
