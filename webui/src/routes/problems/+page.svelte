<script lang="ts">
	/**
	 * +page.svelte
	 *
	 * @author Giomara Larraga <glarragw@jyu.fi>
	 * @created June 2025
	 * @updated September 2025
	 *
	 * @description
	 * This page displays a list of optimization problems in DESDEO and allows users to view and interact with details for each problem.
	 * It features a data table for problem selection and a tabbed interface for viewing general info, objectives, variables, constraints, and extra functions.
	 * Each table supports expandable rows for mathematical formulations, and the UI is responsive to the selected problem.
	 *
	 * @props
	 * @property {Object} data - Contains a list of optimization problems fetched from the server.
	 * @property {ProblemInfo[]} data.problemList - List of problems.
	 *
	 * @features
	 * - DataTable for selecting a problem, with callbacks for selection and "solve" actions.
	 * - Tabbed interface for viewing problem details: General, Objectives, Variables, Constraints, Extra Functions.
	 * - Expandable rows for viewing math expressions for objectives, constraints, and extra functions.
	 * - Responsive UI: shows a message if no problems are available, or if no problem is selected.
	 * - Summarizes variable types if there are more than 10 variables.
	 * - Uses Svelte runes mode for reactivity.
	 *
	 * @dependencies
	 * - DataTable: Custom data table component for problems.
	 * - Tabs, Table: UI components.
	 * - MathExpressionRenderer: Renders math expressions.
	 * - OpenAPI-generated ProblemInfo type.
	 * - methodSelection: Svelte store for the currently selected problem and method.
	 *
	 * @notes
	 * - TODO: Add functionality to create, edit, and delete problems.
	 * - TODO: Add table of available solutions in the general tab (see: https://github.com/giomara-larraga/DESDEO/blob/temp/webui/src/routes/(app)/problem/%2Bpage.svelte).
	 * - isConvex, isLinear, isTwice differentiable are empty for all the problems available.
	 * - Properties isSurrogateAvailable, constraint.simulated, and constraint.expensive (or equivalents) are missing in the problem type.
	 * - There is no way to know if the problem was defined by the user or is a pre-defined problem.
	 * - The "Solve" button updates the methodSelection store with the selected problem ID, but it is not updating the name selected method.
	 */

	import DataTable from '$lib/components/custom/problems-data-table/data-table.svelte';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Table from '$lib/components/ui/table/index.js';
	import { Button } from '$lib/components/ui/button';
	import type { components } from '$lib/api/client-types';
	import { methodSelection } from '../../stores/methodSelection';
	import { invalidateAll } from '$app/navigation';
	import { deleteProblem, downloadProblemJson, getAssignedSolver, getAvailableSolvers, assignSolver, addRepresentativeSolutionSet } from './handler';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { openInputDialog } from '$lib/components/custom/dialogs/dialogs';

	type ProblemInfo = components['schemas']['ProblemInfo'];

	import type { PageProps } from './$types';
	import MathExpressionRenderer from '$lib/components/ui/MathExpressionRenderer/MathExpressionRenderer.svelte';

	let { data }: PageProps = $props();
	let problemList = $derived(data.problemList);
	let selectedProblem = $state<ProblemInfo | undefined>(undefined);
	let expandedObjectives = $state(new Set<number>());
	let expandedConstraints = $state(new Set<number>());
	let expandedExtras = $state(new Set<number>());
	let expandedRepSolutions = $state(new Set<number>());
	let assignedSolver = $state<string | null>(null);
	let availableSolvers = $state<string[]>([]);
	let selectedSolver = $state('');

	// Import representative solution set state
	let importDialogOpen = $state(false);
	let importName = $state('');
	let importDescription = $state('');
	let importSolutionData = $state<{ [key: string]: number[] }>({});
	let importIdeal = $state<{ [key: string]: number }>({});
	let importNadir = $state<{ [key: string]: number }>({});
	let importError = $state('');
	let importSubmitting = $state(false);
	let fileInputEl = $state<HTMLInputElement | undefined>();

	function computeIdealNadir(solutionData: { [key: string]: number[] }) {
		const ideal: { [key: string]: number } = {};
		const nadir: { [key: string]: number } = {};
		if (!selectedProblem?.objectives) return { ideal, nadir };

		for (const obj of selectedProblem.objectives) {
			const key = obj.symbol || obj.name;
			const values = solutionData[key];
			if (!values?.length) continue;
			if (obj.maximize) {
				ideal[key] = Math.max(...values);
				nadir[key] = Math.min(...values);
			} else {
				ideal[key] = Math.min(...values);
				nadir[key] = Math.max(...values);
			}
		}
		return { ideal, nadir };
	}

	function parseCSV(text: string): { [key: string]: number[] } {
		const lines = text.trim().split('\n');
		if (lines.length < 2) return {};
		const headers = lines[0].split(',').map((h) => h.trim());
		const data: { [key: string]: number[] } = {};
		for (const h of headers) data[h] = [];
		for (let i = 1; i < lines.length; i++) {
			const values = lines[i].split(',');
			for (let j = 0; j < headers.length; j++) {
				data[headers[j]].push(parseFloat(values[j]));
			}
		}
		return data;
	}

	async function handleFileSelected(event: Event) {
		const input = event.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;

		importError = '';
		const text = await file.text();
		input.value = '';
		const isJson = file.name.toLowerCase().endsWith('.json');

		try {
			if (isJson) {
				const parsed = JSON.parse(text);
				let solutionData: { [key: string]: number[] };
				let jsonName: string | undefined;
				let jsonIdeal: { [key: string]: number } | undefined;
				let jsonNadir: { [key: string]: number } | undefined;

				if (Array.isArray(parsed)) {
					// Row-oriented: [{col1: v1, col2: v2}, ...] → column-oriented
					solutionData = {};
					for (const row of parsed) {
						for (const [key, val] of Object.entries(row)) {
							if (!solutionData[key]) solutionData[key] = [];
							solutionData[key].push(Number(val));
						}
					}
				} else {
					solutionData = parsed.solution_data ?? {};
					jsonName = parsed.name;
					jsonIdeal = parsed.ideal;
					jsonNadir = parsed.nadir;
				}

				importSolutionData = solutionData;
				importName = jsonName ?? file.name.replace(/\.json$/i, '');
				importDescription = parsed.description ?? '';
				const defaults = computeIdealNadir(importSolutionData);
				importIdeal = jsonIdeal ?? defaults.ideal;
				importNadir = jsonNadir ?? defaults.nadir;
			} else {
				importSolutionData = parseCSV(text);
				importName = file.name.replace(/\.csv$/i, '');
				importDescription = '';
				const defaults = computeIdealNadir(importSolutionData);
				importIdeal = defaults.ideal;
				importNadir = defaults.nadir;
			}

			if (Object.keys(importSolutionData).length === 0) {
				importError = 'No data found in file.';
				return;
			}

			importDialogOpen = true;
		} catch (e) {
			importError = `Failed to parse file: ${e instanceof Error ? e.message : String(e)}`;
			importDialogOpen = true;
		}
	}

	async function handleImportSubmit() {
		if (!selectedProblem) return;
		importSubmitting = true;
		importError = '';
		try {
			const success = await addRepresentativeSolutionSet({
				name: importName,
				description: importDescription || undefined,
				solution_data: importSolutionData,
				ideal: importIdeal,
				nadir: importNadir,
				problem_id: selectedProblem.id
			});
			if (success) {
				importDialogOpen = false;
				const problemId = selectedProblem.id;
				await invalidateAll();
				selectedProblem = problemList.find((p) => p.id === problemId);
			} else {
				importError = 'Failed to add solution set. Check the server logs for details.';
			}
		} catch (e) {
			importError = `Error: ${e instanceof Error ? e.message : String(e)}`;
		} finally {
			importSubmitting = false;
		}
	}

	$effect(() => {
		if (!selectedProblem) {
			assignedSolver = null;
			availableSolvers = [];
			selectedSolver = '';
			return;
		}
		selectedSolver = '';
		getAssignedSolver(selectedProblem.id).then((solver) => {
			assignedSolver = solver;
		});
		getAvailableSolvers().then((solvers) => {
			availableSolvers = solvers;
		});
	});

	function toggleSet(set: Set<number>, index: number): Set<number> {
		const next = new Set(set);
		if (next.has(index)) next.delete(index);
		else next.add(index);
		return next;
	}

	function handleDelete(problem: ProblemInfo) {
		openInputDialog({
			title: 'Delete Problem',
			description: `Are you sure you want to delete "${problem.name}"? The problem and all associated data (solutions, sessions, metadata) will be permanently removed. Type "delete" to confirm.`,
			confirmText: 'Delete',
			cancelText: 'Cancel',
			placeholder: 'Type "delete" to confirm',
			confirmVariant: 'destructive',
			requiredValue: 'delete',
			onConfirm: async () => {
				const success = await deleteProblem(problem.id);

				if (success) {
					if (selectedProblem?.id === problem.id) {
						selectedProblem = undefined;
					}
					await invalidateAll();
				}
			}
		});
	}
</script>

<div class="px-8">
	<h1 class="primary mb-2 text-pretty pt-4 text-left text-lg font-semibold lg:text-xl">
		Optimization Problems
	</h1>
	<p class="text-md text-justify text-gray-700">
		Here you can select one of the problems available in DESDEO to start optimizing. According to
		the selected problem, you will be able to select the most suitable method according to the types
		of preferences you want to utilize.
	</p>
	{#if problemList.length === 0}
		<p class="text-gray-600">You have not defined any problems yet.</p>
	{:else}
		<div class="mt-4 grid grid-cols-2 gap-8 sm:grid-cols-1 lg:grid-cols-2">
			<div class="w-full">
				<DataTable
					data={problemList}
					onSelect={(e: ProblemInfo) => {
						selectedProblem = e;
						console.log('Selected problem:', selectedProblem.id);
					}}
					onClickSolve={(e: ProblemInfo) => {
						selectedProblem = e;
						console.log('Selected problem:', selectedProblem.id);
						methodSelection.setProblem(selectedProblem?.id ?? null);
					}}
					onDelete={handleDelete}
					onDownload={(problem) => downloadProblemJson(problem.id, problem.name)}
				/>
			</div>
			<div class="w-full">
				<Tabs.Root value="general" class="w-full">
					<Tabs.List class="w-full">
						<Tabs.Trigger value="general">General</Tabs.Trigger>
						<Tabs.Trigger value="objectives">Objectives</Tabs.Trigger>
						<Tabs.Trigger value="variables">Variables</Tabs.Trigger>
						<Tabs.Trigger value="constraints">Constraints</Tabs.Trigger>
						<Tabs.Trigger value="extra">Extra Functions</Tabs.Trigger>
						<Tabs.Trigger value="metadata">Metadata</Tabs.Trigger>
					</Tabs.List>

					<!-- General Tab -->
					<Tabs.Content value="general" class="w-full">
						{#if selectedProblem}
							<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
								<div class="grid w-full grid-cols-2 gap-x-4 gap-y-2 text-justify">
									<div class="col-span-2 flex">
										<div class="w-40 font-semibold">Description</div>
										<div class="flex-1">{selectedProblem.description ?? '—'}</div>
									</div>
									<div class="col-span-2 border-b border-gray-300"></div>
									<div class="col-span-2 flex">
										<div class="w-40 font-semibold">Domain</div>
										<div class="flex-1">{selectedProblem.variable_domain ?? '—'}</div>
									</div>
									<div class="col-span-2 border-b border-gray-300"></div>
									<div class="col-span-2 flex items-center">
										<div class="w-40 font-semibold">Characteristics</div>
										<div class="flex flex-wrap gap-2">
											{#if selectedProblem.is_linear}
												<span
													class="inline-block rounded bg-blue-100 px-2 py-1 text-xs font-semibold text-blue-800"
													>Linear</span
												>
											{/if}
											{#if selectedProblem.is_convex}
												<span
													class="inline-block rounded bg-green-100 px-2 py-1 text-xs font-semibold text-green-800"
													>Convex</span
												>
											{/if}
											{#if selectedProblem.is_twice_differentiable}
												<span
													class="inline-block rounded bg-purple-100 px-2 py-1 text-xs font-semibold text-purple-800"
													>Twice Differentiable</span
												>
											{/if}
											{#if !selectedProblem.is_linear && !selectedProblem.is_convex && !selectedProblem.is_twice_differentiable}
												<span
													class="inline-block rounded bg-gray-100 px-2 py-1 text-xs font-semibold text-gray-800"
													>None</span
												>
											{/if}
										</div>
									</div>
									<div class="col-span-2 border-b border-gray-300"></div>
								</div>
							</div>
						{:else}
							Select a problem to see details.
						{/if}
					</Tabs.Content>

					<!-- Objectives Tab -->
					<Tabs.Content value="objectives" class="w-full">
						{#if selectedProblem}
							{#if selectedProblem.objectives && Array.isArray(selectedProblem.objectives) && selectedProblem.objectives.length}
								<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
									<Table.Root>
										<Table.Caption>
											List of objective functions for {selectedProblem.name}.
										</Table.Caption>
										<Table.Header>
											<Table.Row>
												<Table.Head class="font-semibold">Name</Table.Head>
												<Table.Head class="font-semibold">Type</Table.Head>
												<Table.Head class="font-semibold">Direction</Table.Head>
												<Table.Head class="font-semibold">Ideal</Table.Head>
												<Table.Head class="font-semibold">Nadir</Table.Head>
												<Table.Head class="font-semibold">Formulation</Table.Head>
											</Table.Row>
										</Table.Header>
										<Table.Body>
											{#each selectedProblem.objectives as obj, i}
												<Table.Row>
													<Table.Cell class="text-justify"
														>{(obj.symbol || obj.name) ?? '_'}</Table.Cell
													>
													<Table.Cell class="text-justify">{obj.objective_type ?? '—'}</Table.Cell>
													<Table.Cell class="text-justify"
														>{obj.maximize ? 'Maximize' : 'Minimize'}</Table.Cell
													>
													<Table.Cell class="text-justify">{obj.ideal ?? '—'}</Table.Cell>
													<Table.Cell class="text-justify">{obj.nadir ?? '—'}</Table.Cell>
													<Table.Cell class="text-justify">
														<Button
															variant="outline"
															disabled={!obj.func}
															onclick={() => {
																expandedObjectives = toggleSet(expandedObjectives, i);
															}}
														>
															{expandedObjectives.has(i) ? 'Hide' : 'Show'} Formulation
														</Button>
													</Table.Cell>
												</Table.Row>
												{#if expandedObjectives.has(i) && obj.func}
													<Table.Row>
														<Table.Cell colspan={6} class="bg-gray-50 px-6 py-4">
															<MathExpressionRenderer func={obj.func} />
														</Table.Cell>
													</Table.Row>
												{/if}
											{/each}
										</Table.Body>
									</Table.Root>
								</div>
							{:else}
								<p>No objective functions details available.</p>
							{/if}
						{:else}
							Select a problem to see details.
						{/if}
					</Tabs.Content>

					<!-- Variables Tab -->
					<Tabs.Content value="variables" class="w-full">
						{#if selectedProblem}
							{#if selectedProblem.variables && Array.isArray(selectedProblem.variables) && selectedProblem.variables.length <= 10}
								<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
									<Table.Root>
										<Table.Caption>List of variables for {selectedProblem.name}.</Table.Caption>
										<Table.Header>
											<Table.Row>
												<Table.Head class="font-semibold">Name</Table.Head>
												<Table.Head class="font-semibold">Lower Bound</Table.Head>
												<Table.Head class="font-semibold">Upper Bound</Table.Head>
												<Table.Head class="font-semibold">Type</Table.Head>
											</Table.Row>
										</Table.Header>
										<Table.Body>
											{#each selectedProblem.variables as variable}
												<Table.Row>
													<Table.Cell class="text-justify"
														>{(variable.symbol || variable.name) ?? '—'}</Table.Cell
													>
													<Table.Cell class="text-justify">{variable.lowerbound ?? '—'}</Table.Cell>
													<Table.Cell class="text-justify">{variable.upperbound ?? '—'}</Table.Cell>
													<Table.Cell class="text-justify"
														>{variable.variable_type ?? '—'}</Table.Cell
													>
												</Table.Row>
											{/each}
										</Table.Body>
									</Table.Root>
								</div>
							{:else if selectedProblem.variables && Array.isArray(selectedProblem.variables)}
								<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
									<p class="mb-2 font-medium text-gray-700">
										This problem has
										<span class="font-bold">{selectedProblem.variables.length}</span> variables:
									</p>
									<ul class="ml-2 flex flex-col gap-2">
										<li class="flex items-center gap-2">
											<span
												class="inline-block rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800"
											>
												{selectedProblem.variables.filter((v) => v.variable_type === 'integer')
													.length}
											</span>
											<span class="text-gray-700">integer</span>
										</li>
										<li class="flex items-center gap-2">
											<span
												class="inline-block rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-800"
											>
												{selectedProblem.variables.filter((v) => v.variable_type === 'binary')
													.length}
											</span>
											<span class="text-gray-700">binary</span>
										</li>
										<li class="flex items-center gap-2">
											<span
												class="inline-block rounded-full bg-purple-100 px-3 py-1 text-xs font-semibold text-purple-800"
											>
												{selectedProblem.variables.filter((v) => v.variable_type === 'real').length}
											</span>
											<span class="text-gray-700">real</span>
										</li>
									</ul>
									<p class="mb-2 text-sm italic text-gray-600">
										Only a summary is shown because this problem has more than 10 variables.
									</p>
								</div>
							{:else}
								<p>No variable details available.</p>
							{/if}
						{:else}
							Select a problem to see details.
						{/if}
					</Tabs.Content>

					<!-- Constraints Tab -->
					<Tabs.Content value="constraints" class="w-full">
						{#if selectedProblem}
							{#if selectedProblem.constraints && Array.isArray(selectedProblem.constraints) && selectedProblem.constraints.length}
								<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
									<Table.Root>
										<Table.Caption>
											List of constraints for {selectedProblem.name}.
										</Table.Caption>
										<Table.Header>
											<Table.Row>
												<Table.Head class="font-semibold">Name</Table.Head>
												<Table.Head class="font-semibold">Type</Table.Head>
												<Table.Head class="font-semibold">Convex</Table.Head>
												<Table.Head class="font-semibold">Linear</Table.Head>
												<Table.Head class="font-semibold">Twice Differentiable</Table.Head>
												<Table.Head class="font-semibold">Formulation</Table.Head>
											</Table.Row>
										</Table.Header>
										<Table.Body>
											{#each selectedProblem.constraints as constraint, i}
												<Table.Row>
													<Table.Cell class="text-justify"
														>{(constraint.symbol || constraint.name) ?? '—'}</Table.Cell
													>
													<Table.Cell class="text-justify">{constraint.cons_type ?? '—'}</Table.Cell
													>
													<Table.Cell class="text-justify"
														>{constraint.is_convex ? 'Yes' : 'No'}</Table.Cell
													>
													<Table.Cell class="text-justify"
														>{constraint.is_linear ? 'Yes' : 'No'}</Table.Cell
													>
													<Table.Cell class="text-justify"
														>{constraint.is_twice_differentiable ? 'Yes' : 'No'}</Table.Cell
													>
													<Table.Cell class="text-justify">
														<Button
															variant="outline"
															disabled={!constraint.func}
															onclick={() => {
																expandedConstraints = toggleSet(expandedConstraints, i);
															}}
														>
															{expandedConstraints.has(i) ? 'Hide' : 'Show'} Formulation
														</Button>
													</Table.Cell>
												</Table.Row>
												{#if expandedConstraints.has(i) && constraint.func}
													<Table.Row>
														<Table.Cell colspan={6} class="bg-gray-50 px-6 py-4">
															<MathExpressionRenderer func={constraint.func} />
														</Table.Cell>
													</Table.Row>
												{/if}
											{/each}
										</Table.Body>
									</Table.Root>
								</div>
							{:else}
								<p>No constraint details available.</p>
							{/if}
						{:else}
							Select a problem to see details.
						{/if}
					</Tabs.Content>

					<!-- Extra Functions Tab -->
					<Tabs.Content value="extra" class="w-full">
						{#if selectedProblem}
							{#if selectedProblem.extra_funcs && Array.isArray(selectedProblem.extra_funcs) && selectedProblem.extra_funcs.length}
								<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
									<Table.Root>
										<Table.Caption>
											List of extra functions for {selectedProblem.name}.
										</Table.Caption>
										<Table.Header>
											<Table.Row>
												<Table.Head class="font-semibold">Name</Table.Head>
												<Table.Head class="font-semibold">Formulation</Table.Head>
											</Table.Row>
										</Table.Header>
										<Table.Body>
											{#each selectedProblem.extra_funcs as obj, i}
												<Table.Row>
													<Table.Cell class="text-justify"
														>{(obj.symbol || obj.name) ?? '—'}</Table.Cell
													>
													<Table.Cell class="text-justify">
														<Button
															variant="outline"
															disabled={!obj.func}
															onclick={() => {
																expandedExtras = toggleSet(expandedExtras, i);
															}}
														>
															{expandedExtras.has(i) ? 'Hide' : 'Show'} Formulation
														</Button>
													</Table.Cell>
												</Table.Row>
												{#if expandedExtras.has(i) && obj.func}
													<Table.Row>
														<Table.Cell colspan={2} class="bg-gray-50 px-6 py-4">
															<MathExpressionRenderer func={obj.func} />
														</Table.Cell>
													</Table.Row>
												{/if}
											{/each}
										</Table.Body>
									</Table.Root>
								</div>
							{:else}
								<p>No extra function details available.</p>
							{/if}
						{:else}
							Select a problem to see details.
						{/if}
					</Tabs.Content>

					<!-- Metadata Tab -->
					<Tabs.Content value="metadata" class="w-full">
						{#if selectedProblem}
							<!-- Solver Section -->
							<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
								<h3 class="mb-2 font-semibold">Solver</h3>
								<div class="mb-3">
									{#if assignedSolver}
										<span
											class="inline-block rounded bg-blue-100 px-2 py-1 text-sm font-medium text-blue-800"
										>
											{assignedSolver}
										</span>
									{:else}
										<p class="text-sm text-gray-500">No solver assigned.</p>
									{/if}
								</div>
								<div class="flex items-center gap-2">
									<Select.Root
										type="single"
										bind:value={selectedSolver}
									>
										<Select.Trigger class="w-64 bg-white">
											{selectedSolver || 'Click to select'}
										</Select.Trigger>
										<Select.Content>
											{#each availableSolvers as solver}
												<Select.Item value={solver}>{solver}</Select.Item>
											{/each}
										</Select.Content>
									</Select.Root>
									<Button
										variant="outline"
										disabled={selectedSolver === ''}
										onclick={() => {
											if (selectedProblem && selectedSolver) {
												assignSolver(selectedProblem.id, selectedSolver).then((success) => {
													if (success) {
														assignedSolver = selectedSolver;
													}
												});
											}
										}}
									>
										Set
									</Button>
								</div>
							</div>

							<!-- Representative Non-Dominated Solution Sets -->
							<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
								<h3 class="mb-2 font-semibold">Representative Solution Sets</h3>
								{#if selectedProblem.problem_metadata?.representative_nd_metadata?.length}
									<Table.Root>
										<Table.Header>
											<Table.Row>
												<Table.Head class="font-semibold">Name</Table.Head>
												<Table.Head class="font-semibold">Description</Table.Head>
												<Table.Head class="font-semibold">Solutions</Table.Head>
												<Table.Head class="font-semibold">Details</Table.Head>
											</Table.Row>
										</Table.Header>
										<Table.Body>
											{#each selectedProblem.problem_metadata.representative_nd_metadata as repSet, i}
												{@const solutionCount = Object.values(repSet.solution_data)[0]?.length ?? 0}
												<Table.Row>
													<Table.Cell>{repSet.name}</Table.Cell>
													<Table.Cell>{repSet.description ?? '—'}</Table.Cell>
													<Table.Cell>{solutionCount}</Table.Cell>
													<Table.Cell>
														<Button
															variant="outline"
															onclick={() => {
																expandedRepSolutions = toggleSet(expandedRepSolutions, i);
															}}
														>
															{expandedRepSolutions.has(i) ? 'Hide' : 'Show'} Details
														</Button>
													</Table.Cell>
												</Table.Row>
												{#if expandedRepSolutions.has(i)}
													<Table.Row>
														<Table.Cell colspan={4} class="bg-gray-50 px-6 py-4">
															<Table.Root>
																<Table.Header>
																	<Table.Row>
																		<Table.Head class="font-semibold">Objective</Table.Head>
																		<Table.Head class="font-semibold">Ideal</Table.Head>
																		<Table.Head class="font-semibold">Nadir</Table.Head>
																	</Table.Row>
																</Table.Header>
																<Table.Body>
																	{#each Object.keys(repSet.ideal) as key}
																		<Table.Row>
																			<Table.Cell>{key}</Table.Cell>
																			<Table.Cell>{repSet.ideal[key]}</Table.Cell>
																			<Table.Cell>{repSet.nadir[key]}</Table.Cell>
																		</Table.Row>
																	{/each}
																</Table.Body>
															</Table.Root>
														</Table.Cell>
													</Table.Row>
												{/if}
											{/each}
										</Table.Body>
									</Table.Root>
								{:else}
									<p class="text-sm text-gray-500">No representative solution sets.</p>
								{/if}
								<input
									type="file"
									accept=".json,.csv"
									class="hidden"
									bind:this={fileInputEl}
									onchange={handleFileSelected}
								/>
								<Button
									variant="outline"
									class="mt-3"
									onclick={() => fileInputEl?.click()}
								>
									Import from file
								</Button>
							</div>

							<!-- Forest Metadata -->
							{#if selectedProblem.problem_metadata?.forest_metadata?.length}
								<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
									<h3 class="mb-2 font-semibold">Forest Metadata</h3>
									{#each selectedProblem.problem_metadata.forest_metadata as forest}
										<div class="grid w-full grid-cols-2 gap-x-4 gap-y-2">
											<div class="col-span-2 flex">
												<div class="w-40 font-semibold">Years</div>
												<div class="flex-1">{forest.years.join(', ')}</div>
											</div>
											<div class="col-span-2 border-b border-gray-300"></div>
											<div class="col-span-2 flex">
												<div class="w-40 font-semibold">Stand ID Field</div>
												<div class="flex-1">{forest.stand_id_field}</div>
											</div>
											<div class="col-span-2 border-b border-gray-300"></div>
											{#if forest.compensation != null}
												<div class="col-span-2 flex">
													<div class="w-40 font-semibold">Compensation</div>
													<div class="flex-1">{forest.compensation}</div>
												</div>
												<div class="col-span-2 border-b border-gray-300"></div>
											{/if}
											<div class="col-span-2 flex">
												<div class="w-40 font-semibold">Map Data</div>
												<div class="flex-1 text-sm text-gray-500">
													{forest.map_json ? 'Available' : 'Not available'}
												</div>
											</div>
											<div class="col-span-2 border-b border-gray-300"></div>
											<div class="col-span-2 flex">
												<div class="w-40 font-semibold">Schedule</div>
												<div class="flex-1 text-sm text-gray-500">
													{Object.keys(forest.schedule_dict).length} entries
												</div>
											</div>
										</div>
									{/each}
								</div>
							{/if}
						{:else}
							Select a problem to see details.
						{/if}
					</Tabs.Content>
				</Tabs.Root>
			</div>
		</div>
	{/if}

<!-- Import Representative Solution Set Dialog -->
{#if importDialogOpen}
<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="fixed inset-0 z-50 flex items-center justify-center">
	<div class="fixed inset-0 bg-black/50" onclick={() => (importDialogOpen = false)}></div>
	<div class="bg-background relative z-50 grid w-full max-w-lg gap-4 rounded-lg border p-6 shadow-lg max-h-[80vh] overflow-y-auto">
		<div>
			<h2 class="text-lg font-semibold">Import Representative Solution Set</h2>
			<p class="text-muted-foreground text-sm">Review the parsed data and adjust ideal/nadir values before importing.</p>
		</div>
		<div class="grid gap-4 py-4">
			{#if importError}
				<p class="text-sm text-red-600">{importError}</p>
			{/if}
			<div class="grid gap-2">
				<Label for="import-name">Name</Label>
				<Input id="import-name" bind:value={importName} />
			</div>
			<div class="grid gap-2">
				<Label for="import-description">Description</Label>
				<Input id="import-description" bind:value={importDescription} placeholder="Optional" />
			</div>
			<div class="text-sm text-gray-600">
				<p>{Object.keys(importSolutionData).length} columns, {Object.values(importSolutionData)[0]?.length ?? 0} solutions</p>
			</div>
			{#if Object.keys(importIdeal).length > 0}
				<div class="grid gap-2">
					<h4 class="font-semibold">Ideal Values</h4>
					{#each Object.keys(importIdeal) as key}
						<div class="flex items-center gap-2">
							<Label class="w-24 text-sm">{key}</Label>
							<Input
								type="number"
								value={importIdeal[key]}
								onchange={(e: Event) => {
									importIdeal[key] = parseFloat((e.target as HTMLInputElement).value);
								}}
							/>
						</div>
					{/each}
				</div>
				<div class="grid gap-2">
					<h4 class="font-semibold">Nadir Values</h4>
					{#each Object.keys(importNadir) as key}
						<div class="flex items-center gap-2">
							<Label class="w-24 text-sm">{key}</Label>
							<Input
								type="number"
								value={importNadir[key]}
								onchange={(e: Event) => {
									importNadir[key] = parseFloat((e.target as HTMLInputElement).value);
								}}
							/>
						</div>
					{/each}
				</div>
			{/if}
		</div>
		<div class="flex justify-end gap-2">
			<Button variant="outline" onclick={() => (importDialogOpen = false)}>Cancel</Button>
			<Button disabled={importSubmitting || !importName} onclick={handleImportSubmit}>
				{importSubmitting ? 'Importing...' : 'Import'}
			</Button>
		</div>
	</div>
</div>
{/if}

</div>
