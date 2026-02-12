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
	import { deleteProblem, downloadProblemJson } from './handler';
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
				</Tabs.Root>
			</div>
		</div>
	{/if}
</div>
