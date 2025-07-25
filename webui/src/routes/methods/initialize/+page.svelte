<script lang="ts">
	/**
	 * +page.svelte
	 *
	 * @author Giomara Larraga <glarragw@jyu.fi>
	 * @created June 2025
	 * @updated July 2025
	 *
	 * @description
	 * This page displays a list of available optimization methods in DESDEO and allows the user to select a method for a specific problem.
	 * If a problem is selected (via the problemId from the methodSelection store), the page highlights methods suitable for that problem.
	 * Each method card shows its name, description, preference types, and problem types.
	 * The "Use" button is enabled only if a problem is selected.
	 *
	 * @props
	 * @property {Object} data - Contains a list of optimization problems fetched from the server.
	 * @property {ProblemInfo[]} data.problems - List of problems.
	 *
	 * @features
	 * - Lists all available optimization methods with details.
	 * - Highlights and enables method selection only when a problem is selected.
	 * - Allows navigation back to problem selection.
	 * - Displays preference and problem types for each method.
	 *
	 * @dependencies
	 * - Card, Button: UI components.
	 * - Play, Settings: Lucide icons.
	 * - ProblemInfo: OpenAPI-generated type.
	 * - methodSelection: Svelte store for the currently selected problem.
	 *
	 * @notes
	 * - The page expects the selected problemId to be set in the methodSelection store.
	 * - If the problemId does not match any problem, the user is prompted to select a problem.
	 * - The method list can be extended by modifying the `methods` array.
	 * - The page does not use the $page store; instead, it relies on the methodSelection store for the selected problem.
	 * - TODO: Update the methods list dynamically from the server in the future.
	 * - TODO: Add variants for each method, similar to : https://github.com/giomara-larraga/DESDEO/blob/temp/webui/src/routes/(app)/method/%2Bpage.svelte
	 * - TODO: Fetch the methods that are suitable for the selected problem from the server (based on the properties of the problem).
	 * - TODO: Enable the settings button to configure method.
	 */

	import type { PageProps } from './$types';
	import { methodSelection } from '../../../stores/methodSelection';

	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card/index.js';
	import Settings from '@lucide/svelte/icons/settings';
	import Play from '@lucide/svelte/icons/play';
	import type { components } from '$lib/api/client-types';
	type ProblemInfo = components['schemas']['ProblemInfo'];

	let problemId: number | null = $state(null);
	let problem: ProblemInfo | null = $state(null);

	const { data } = $props<{ data: ProblemInfo[] }>();
	let problemList = data.problems ?? [];

	export const methods: any[] = [
		{
			name: 'E-NAUTILUS',
			path: '/interactive_methods/E-NAUTILUS',
			description: 'Evolutionary NAUTILUS method for MOO.',
			preferencesType: ['reference point']
		},
		{
			name: 'Evolutionary method',
			path: '/interactive_methods/EMO',
			description: 'Interactive evolutionary method for MOO.',
			preferencesType: ['reference point', 'preferred ranges', 'preferred solutions']
		},
		{
			name: 'NIMBUS',
			path: '/interactive_methods/NIMBUS',
			description: 'NIMBUS method for MOO.',
			preferencesType: ['reference point']
		},
		{
			name: 'Reference Point',
			path: '/interactive_methods/reference-point',
			description: 'Reference Point method for MOO.',
			preferencesType: ['reference point'],
			problemtypes: ['linear', 'nonlinear']
		}
	];
	onMount(() => {
		problemId = $methodSelection.selectedProblemId;
		if (problemId) {
			problem = problemList.find((p: ProblemInfo) => String(p.id) === String(problemId));
		}
	});
</script>

<div class="px-8">
	<h1 class="primary mb-2 text-pretty pt-4 text-left text-lg font-semibold lg:text-xl">
		Optimization Methods
	</h1>

	{#if problem}
		<p class="text-md mb-2 text-justify text-gray-700">
			You are currently viewing methods suitable for the selected problem:
			<span class="text-accent-foreground font-semibold">{problem.name}</span>
		</p>
		<Button variant="secondary" href="/problems">Change selected problem</Button>
	{:else}
		<p class="text-md mb-2 text-justify text-gray-700">
			You are seeing the list of methods available in DESDEO. Please select a problem if you want to
			use any of the methods.
		</p>
		<Button variant="secondary" href="/problems">Select a problem</Button>
	{/if}

	<div class="mt-4 grid grid-cols-3 gap-8 sm:grid-cols-1 lg:grid-cols-3">
		{#each methods as method}
			<Card.Root>
				<Card.Header class="flex items-start justify-between pb-1">
					<h2 class="text-lg font-semibold">{method.name}</h2>
				</Card.Header>
				<Card.Content class="text-left">
					<div>
						{#if method.preferencesType}
							<span class="font-medium">Preference types:</span>
							<ul class="ml-4 list-inside list-disc">
								{#each method.preferencesType as type}
									<li>{type}</li>
								{/each}
							</ul>
						{/if}
						{#if method.problemtypes}
							<span class="font-medium">Problem types:</span>
							<ul class="ml-4 list-inside list-disc">
								{#each method.problemtypes as type}
									<li>{type}</li>
								{/each}
							</ul>
						{/if}
					</div>
				</Card.Content>
				<Card.Footer class="mt-auto flex items-center justify-end gap-2">
					<Button variant="default" disabled={!problem} href={`${method.path}`}>
						<Play class="mr-1 inline" />
						Use {method.name}
					</Button>

					<Button variant="ghost" size="icon" aria-label="Settings">
						<Settings class="size-4" strokeWidth={1} />
					</Button>
				</Card.Footer>
			</Card.Root>
		{/each}
	</div>
</div>
