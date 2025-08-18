<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import PreferenceSwitcher from './preference-switcher.svelte';
	import { writable, type Writable } from 'svelte/store';
	import { Button } from '$lib/components/ui/button/index.js';
	import type { components } from '$lib/api/client-types';
	import {
		HorizontalBar,
		HorizontalBarRanges
	} from '$lib/components/visualizations/horizontal-bar';
	import { Input } from '$lib/components/ui/input/index.js';
	import ValidatedTextbox from '../validated-textbox/validated-textbox.svelte';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors.js';
	import {
		calculateClassification,
		type PreferenceValue,
		formatNumber
	} from '$lib/helpers/index.js';
	import { PREFERENCE_TYPES, SIGNIFICANT_DIGITS } from '$lib/constants/index.js';
	import { getValueRange } from '$lib/components/visualizations/utils/math';

	type ProblemInfo = components['schemas']['ProblemInfo'];
	type Solution = components['schemas']['UserSavedSolutionAddress'];

	interface Props {
		problem: ProblemInfo;
		preferenceValues: number[];
		results: Array<Solution>;
		ref?: HTMLElement | null;
	}

	let {
		problem,
		preferenceValues,
		results,
		ref = null,
	}: Props = $props();

	// Store for solution details including Lagrange multipliers
	let solutionDetails: Record<string, any> = $state({});

	// Function to get solution details including Lagrange multipliers
	async function getSolutionDetails(solution: Solution): Promise<any | null> {
		const solutionKey = `${solution.address_state}_${solution.address_result}`;
		
		// Return cached result if available
		if (solutionDetails[solutionKey]) {
			return solutionDetails[solutionKey];
		}

		try {
			// Use fetch since the typed API client doesn't recognize this endpoint yet
			const response = await fetch('/api/method/nimbus/get_solution_details', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					problem_id: problem.id,
					address_state: solution.address_state,
					address_result: solution.address_result
				})
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const data = await response.json();
			
			// Cache the result
			solutionDetails[solutionKey] = data;
			return data;
		} catch (error) {
			console.error('Failed to get solution details:', error);
			return null;
		}
	}
</script>

<Sidebar.Root side="right" class="fixed right-0 top-12 h-[calc(100vh-3rem)]">
	<Sidebar.Header>
		<span>Solution Analysis</span>
		<p class="mt-1 text-xs font-normal text-gray-500">
			Detailed analysis including Lagrange multipliers for current iteration solutions only.
		</p>
	</Sidebar.Header>
	<Sidebar.Content class="px-4">
		{#if results.length === 0}
			<div class="text-sm text-gray-500 text-center py-8">
				No solutions available for explanation.
			</div>
		{:else}
			{#each results as solution, index}
				<div class="mb-6 p-4 border rounded-lg bg-white shadow-sm">
					<h4 class="font-semibold mb-3 text-lg">Solution {index + 1}</h4>
					
					<!-- Objective values -->
					<div class="mb-4">
						<h5 class="text-sm font-medium mb-2 text-gray-700">Objective Values:</h5>
						<div class="space-y-1">
							{#each Object.entries(solution.objective_values) as [objName, value]}
								<div class="flex justify-between text-xs bg-gray-50 p-2 rounded">
									<span class="font-medium">{objName}:</span> 
									<span class="font-mono">{formatNumber(value, SIGNIFICANT_DIGITS)}</span>
								</div>
							{/each}
						</div>
					</div>

					<!-- Solution details including Lagrange multipliers -->
					{#await getSolutionDetails(solution)}
						<div class="text-xs text-gray-500 p-2 bg-gray-50 rounded">
							Loading detailed information...
						</div>
					{:then details}
						{#if details}
							<!-- Variable values -->
							{#if details.variable_values}
								<div class="mb-4">
									<h5 class="text-sm font-medium mb-2 text-gray-700">Decision Variables:</h5>
									<div class="space-y-1 max-h-32 overflow-y-auto">
										{#each Object.entries(details.variable_values) as [varName, value]}
											<div class="flex justify-between text-xs bg-blue-50 p-2 rounded">
												<span class="font-medium">{varName}:</span> 
												<span class="font-mono">{value}</span>
											</div>
										{/each}
									</div>
								</div>
							{/if}

							<!-- Lagrange multipliers -->
							{#if details.lagrange_multipliers}
								<div class="mb-4">
									<h5 class="text-sm font-medium mb-2 text-gray-700">Lagrange Multipliers:</h5>
									<div class="space-y-1">
										{#each details.lagrange_multipliers as multiplier, idx}
											<div class="flex justify-between text-xs bg-green-50 p-2 rounded">
												<span class="font-medium">λ{idx + 1}:</span> 
												<span class="font-mono">{formatNumber(multiplier, SIGNIFICANT_DIGITS)}</span>
											</div>
										{/each}
									</div>
									<p class="text-xs text-gray-600 mt-2 italic">
										Lagrange multipliers indicate the sensitivity of the objective function to constraint changes.
									</p>
								</div>
							{/if}

							<!-- Solver status -->
							{#if details.success !== undefined}
								<div class="mb-4">
									<h5 class="text-sm font-medium mb-2 text-gray-700">Solver Status:</h5>
									<div class="text-xs p-2 rounded {details.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}">
										{details.success ? 'Optimization succeeded' : 'Optimization failed'}
									</div>
									{#if details.message}
										<div class="text-xs text-gray-600 mt-1 p-2 bg-gray-50 rounded">
											{details.message}
										</div>
									{/if}
								</div>
							{/if}

							<!-- Additional solver information -->
							{#if details.solver_info}
								<div class="mb-4">
									<h5 class="text-sm font-medium mb-2 text-gray-700">Additional Information:</h5>
									<div class="text-xs text-gray-600 p-2 bg-gray-50 rounded max-h-24 overflow-y-auto">
										<pre class="whitespace-pre-wrap">{JSON.stringify(details.solver_info, null, 2)}</pre>
									</div>
								</div>
							{/if}
						{:else}
							<div class="text-xs text-gray-500 p-2 bg-yellow-50 rounded">
								Detailed information not available for this solution.
							</div>
						{/if}
					{:catch error}
						<div class="text-xs text-red-500 p-2 bg-red-50 rounded">
							Error loading solution details: {error.message}
						</div>
					{/await}

					<!-- Solution interpretation -->
					<div class="mt-4 pt-3 border-t">
						<h5 class="text-sm font-medium mb-2 text-gray-700">Interpretation:</h5>
						<div class="text-xs text-gray-600 leading-relaxed">
							{#if solution.name}
								<p class="mb-1"><strong>Name:</strong> {solution.name}</p>
							{/if}
							<p>This solution represents a trade-off between the objectives based on your preferences. 
							The Lagrange multipliers show how sensitive the solution is to changes in constraints.</p>
						</div>
					</div>
				</div>
			{/each}
		{/if}
	</Sidebar.Content>
	<Sidebar.Rail />
</Sidebar.Root>
