<script lang="ts">
	import { enhance } from '$app/forms';
	import type { ActionResult } from '@sveltejs/kit';
	import type { EMOState, EMOSaveState, UserSavedEMOResult, EMOSolution } from './types';
	import { Button } from '$lib/components/ui/button';
	import { Input, Root } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Select } from '$lib/components/ui/select/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/card';
	import { Alert, AlertDescription } from '$lib/components/ui/alert';
	import { Badge } from '$lib/components/ui/badge';
	import { Textarea } from '$lib/components/ui/textarea';

	// Form state
	let problemId = 1;
	let selectedMethod: 'NSGA3' | 'RVEA' = 'NSGA3';
	let maxEvaluations = 1000;
	let numberOfVectors = 20;
	let useArchive = true;

	// Preference settings (aspiration levels)
	let aspirationLevels: Record<string, number> = {
		f_1_min: 0.5,
		f_2_min: 0.3,
		f_3_min: 0.2
	};

	// Results state
	let solveResult: EMOState | null = null;
	let saveResult: EMOSaveState | null = null;
	let savedSolutions: UserSavedEMOResult[] = [];
	let selectedSolutions: EMOSolution[] = [];
	let newSolutionName = '';

	// UI state
	let isLoading = false;
	let error: string | null = null;
	let successMessage: string | null = null;

	// Helper function to add/remove aspiration levels
	function addAspirationLevel() {
		const newKey = `f_${Object.keys(aspirationLevels).length + 1}_min`;
		aspirationLevels[newKey] = 0.0;
		aspirationLevels = { ...aspirationLevels };
	}

	function removeAspirationLevel(key: string) {
		delete aspirationLevels[key];
		aspirationLevels = { ...aspirationLevels };
	}

	// Form submission handlers
	function handleSolveSubmit() {
		return async ({ result, update }: { result: ActionResult; update: any }) => {
			isLoading = false;
			error = null;
			successMessage = null;

			if (result.type === 'success' && result.data?.success) {
				solveResult = result.data.data;
				successMessage = result.data.message || 'Problem solved successfully!';
			} else if (result.type === 'failure') {
				error = result.data?.error || 'Failed to solve problem';
			}
			await update();
		};
	}

	function handleSaveSubmit() {
		return async ({ result, update }: { result: ActionResult; update: any }) => {
			isLoading = false;
			error = null;
			successMessage = null;

			if (result.type === 'success' && result.data?.success) {
				saveResult = result.data.data;
				successMessage = result.data.message || 'Solutions saved successfully!';
				selectedSolutions = [];
				newSolutionName = '';
			} else if (result.type === 'failure') {
				error = result.data?.error || 'Failed to save solutions';
			}
			await update();
		};
	}

	function handleGetSavedSubmit() {
		return async ({ result, update }: { result: ActionResult; update: any }) => {
			isLoading = false;
			error = null;
			successMessage = null;

			if (result.type === 'success' && result.data?.success) {
				savedSolutions = result.data.data || [];
				successMessage = result.data.message || 'Saved solutions loaded successfully!';
			} else if (result.type === 'failure') {
				error = result.data?.error || 'Failed to load saved solutions';
			}
			await update();
		};
	}

	// Helper functions
	function toggleSolutionSelection(solution: EMOSolution, checked: boolean) {
		if (checked) {
			// Add solution if not already selected
			const isAlreadySelected = selectedSolutions.some(
				(s) => JSON.stringify(s.objectives) === JSON.stringify(solution.objectives)
			);
			if (!isAlreadySelected) {
				selectedSolutions = [...selectedSolutions, solution];
			}
		} else {
			// Remove solution from selection
			selectedSolutions = selectedSolutions.filter(
				(s) => JSON.stringify(s.objectives) !== JSON.stringify(solution.objectives)
			);
		}
	}

	function prepareSolutionsForSave(): UserSavedEMOResult[] {
		return selectedSolutions.map((solution, index) => ({
			name: `${newSolutionName || 'Solution'} ${index + 1}`,
			optimal_variables: solution.variables || {},
			optimal_objectives: solution.objectives || {},
			constraint_values: solution.constraint_values || {},
			extra_func_values: solution.extra_func_values || {}
		}));
	}

	$: preferenceJson = JSON.stringify({ aspiration_levels: aspirationLevels });
	$: solutionsJson = JSON.stringify(prepareSolutionsForSave());
</script>

<div class="container mx-auto space-y-6 p-6">
	<h1 class="text-3xl font-bold">EMO (Evolutionary Multi-Objective) Example Usage</h1>

	<!-- Error/Success Messages -->
	{#if error}
		<Alert variant="destructive">
			<AlertDescription>{error}</AlertDescription>
		</Alert>
	{/if}

	{#if successMessage}
		<Alert>
			<AlertDescription>{successMessage}</AlertDescription>
		</Alert>
	{/if}

	<!-- Solve Problem Form -->
	<Card>
		<CardHeader>
			<CardTitle>1. Solve EMO Problem</CardTitle>
			<CardDescription>
				Configure and solve a multi-objective optimization problem using NSGA3 or RVEA algorithms.
			</CardDescription>
		</CardHeader>
		<CardContent>
			<form
				method="POST"
				action="?/solve"
				use:enhance={handleSolveSubmit}
				class="space-y-4"
				on:submit={() => (isLoading = true)}
			>
				<input type="hidden" name="problem_id" value={problemId} />
				<input type="hidden" name="preference" value={preferenceJson} />

				<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
					<div class="space-y-2">
						<Label for="problem-id">Problem ID</Label>
						<Input id="problem-id" type="number" bind:value={problemId} min="1" />
					</div>

					<div class="space-y-2">
						<Label for="method-select">Method</Label>
						<select
							id="method-select"
							name="method"
							bind:value={selectedMethod}
							class="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-sm file:border-0 file:bg-transparent file:text-sm file:font-medium focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
						>
							<option value="NSGA3">NSGA3</option>
							<option value="RVEA">RVEA</option>
						</select>
					</div>

					<div class="space-y-2">
						<Label for="max-evals">Max Evaluations</Label>
						<Input
							id="max-evals"
							type="number"
							name="max_evaluations"
							bind:value={maxEvaluations}
							min="100"
							step="100"
						/>
					</div>

					<div class="space-y-2">
						<Label for="num-vectors">Number of Vectors</Label>
						<Input
							id="num-vectors"
							type="number"
							name="number_of_vectors"
							bind:value={numberOfVectors}
							min="5"
							step="5"
						/>
					</div>
				</div>

				<div class="flex items-center space-x-2">
					<input
						type="checkbox"
						id="use-archive"
						name="use_archive"
						bind:checked={useArchive}
						class="border-input text-primary focus:ring-ring h-4 w-4 rounded border focus:ring-2 focus:ring-offset-2"
					/>
					<Label for="use-archive">Use Archive</Label>
				</div>

				<!-- Aspiration Levels -->
				<div class="space-y-2">
					<div class="flex items-center justify-between">
						<Label>Aspiration Levels (Preferences)</Label>
						<Button type="button" variant="outline" size="sm" onclick={addAspirationLevel}>
							Add Objective
						</Button>
					</div>
					<div class="grid grid-cols-1 gap-2 md:grid-cols-2">
						{#each Object.entries(aspirationLevels) as [key, value]}
							<div class="flex items-center space-x-2">
								<Label class="w-20 text-sm">{key}:</Label>
								<Input type="number" bind:value={aspirationLevels[key]} step="0.1" class="flex-1" />
								<Button
									type="button"
									variant="ghost"
									size="sm"
									onclick={() => removeAspirationLevel(key)}
								>
									×
								</Button>
							</div>
						{/each}
					</div>
				</div>

				<Button type="submit" disabled={isLoading} class="w-full">
					{isLoading ? 'Solving...' : 'Solve Problem'}
				</Button>
			</form>
		</CardContent>
	</Card>

	<!-- Results Display -->
	{#if solveResult}
		<Card>
			<CardHeader>
				<CardTitle>Optimization Results</CardTitle>
				<CardDescription>
					Method: <Badge variant="secondary">{solveResult.method}</Badge>
					Solutions found: <Badge>{solveResult.solutions?.length || 0}</Badge>
				</CardDescription>
			</CardHeader>
			<CardContent>
				{#if solveResult.solutions && solveResult.solutions.length > 0}
					<div class="max-h-96 space-y-2 overflow-y-auto">
						{#each solveResult.solutions as solution, index}
							<div class="space-y-2 rounded border p-3">
								<div class="flex items-center justify-between">
									<span class="font-medium">Solution {index + 1}</span>
									<Checkbox
										checked={selectedSolutions.some(
											(s) => JSON.stringify(s.objectives) === JSON.stringify(solution.objectives)
										)}
										onCheckedChange={(checked: boolean) => {
											// checked is guaranteed to be a boolean
											toggleSolutionSelection(solution, checked);
										}}
									/>
								</div>

								{#if solution.objectives}
									<div>
										<span class="text-sm font-medium">Objectives:</span>
										<div class="text-muted-foreground text-sm">
											{JSON.stringify(solution.objectives, null, 2)}
										</div>
									</div>
								{/if}

								{#if solution.variables}
									<div>
										<span class="text-sm font-medium">Variables:</span>
										<div class="text-muted-foreground text-sm">
											{JSON.stringify(solution.variables, null, 2)}
										</div>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-muted-foreground">No solutions found.</p>
				{/if}
			</CardContent>
		</Card>
	{/if}

	<!-- Save Solutions Form -->
	{#if selectedSolutions.length > 0}
		<Card>
			<CardHeader>
				<CardTitle>2. Save Selected Solutions</CardTitle>
				<CardDescription>
					Save {selectedSolutions.length} selected solution(s) for future reference.
				</CardDescription>
			</CardHeader>
			<CardContent>
				<form
					method="POST"
					action="?/save"
					use:enhance={handleSaveSubmit}
					class="space-y-4"
					on:submit={() => (isLoading = true)}
				>
					<input type="hidden" name="problem_id" value={problemId} />
					<input type="hidden" name="solutions" value={solutionsJson} />

					<div class="space-y-2">
						<Label for="solution-name">Solution Name Prefix</Label>
						<Input id="solution-name" bind:value={newSolutionName} placeholder="My Solution" />
					</div>

					<Button type="submit" disabled={isLoading}>
						{isLoading ? 'Saving...' : `Save ${selectedSolutions.length} Solution(s)`}
					</Button>
				</form>
			</CardContent>
		</Card>
	{/if}

	<!-- Load Saved Solutions -->
	<Card>
		<CardHeader>
			<CardTitle>3. Load Saved Solutions</CardTitle>
			<CardDescription>Retrieve previously saved solutions from your account.</CardDescription>
		</CardHeader>
		<CardContent>
			<form
				method="POST"
				action="?/getSavedSolutions"
				use:enhance={handleGetSavedSubmit}
				on:submit={() => (isLoading = true)}
			>
				<Button type="submit" disabled={isLoading}>
					{isLoading ? 'Loading...' : 'Load Saved Solutions'}
				</Button>
			</form>

			{#if savedSolutions.length > 0}
				<div class="mt-4 max-h-64 space-y-2 overflow-y-auto">
					<h4 class="font-medium">Saved Solutions ({savedSolutions.length})</h4>
					{#each savedSolutions as solution}
						<div class="space-y-2 rounded border p-3">
							<div class="font-medium">{solution.name}</div>
							<div class="text-sm">
								<div>
									<strong>Objectives:</strong>
									{JSON.stringify(solution.optimal_objectives)}
								</div>
								<div><strong>Variables:</strong> {JSON.stringify(solution.optimal_variables)}</div>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</CardContent>
	</Card>

	<!-- Usage Information -->
	<Card>
		<CardHeader>
			<CardTitle>Usage Information</CardTitle>
		</CardHeader>
		<CardContent class="space-y-4">
			<div>
				<h4 class="mb-2 font-medium">Supported Methods:</h4>
				<ul class="list-inside list-disc space-y-1 text-sm">
					<li><strong>NSGA3:</strong> Best for many-objective optimization (3+ objectives)</li>
					<li><strong>RVEA:</strong> Best for large-scale multi-objective optimization</li>
				</ul>
			</div>

			<div>
				<h4 class="mb-2 font-medium">Preference Types:</h4>
				<ul class="list-inside list-disc space-y-1 text-sm">
					<li><strong>Aspiration Levels:</strong> Desired values for each objective</li>
					<li>Future versions will support preferred ranges and solution examples</li>
				</ul>
			</div>

			<div>
				<h4 class="mb-2 font-medium">Workflow:</h4>
				<ol class="list-inside list-decimal space-y-1 text-sm">
					<li>Configure problem parameters and preferences</li>
					<li>Solve using selected algorithm</li>
					<li>Review generated solutions</li>
					<li>Select and save preferred solutions</li>
					<li>Load saved solutions for comparison</li>
				</ol>
			</div>
		</CardContent>
	</Card>
</div>
