<script lang="ts">
	/**
	 * +page.svelte
	 *
	 * @author Giomara Larraga <glarragw@jyu.fi>
	 * @created June 2025
	 * @updated September 2025
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
	import { methodSelection } from '../../../stores/methodSelection';
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card/index.js';
	import Settings from '@lucide/svelte/icons/settings';
	import Play from '@lucide/svelte/icons/play';
	import Search from '@lucide/svelte/icons/search';
	import LayoutGrid from '@lucide/svelte/icons/layout-grid';
	import LayoutList from '@lucide/svelte/icons/layout-list';
	import type { components } from '$lib/api/client-types';
	type ProblemInfo = components['schemas']['ProblemInfo'];

	type PreferenceType =
		| 'reference point'
		| 'classification'
		| 'preferred ranges'
		| 'preferred solutions';

	interface Method {
		name: string;
		path: string;
		description: string;
		preferencesType: PreferenceType[];
		supportsGroups?: boolean;  // NEW: Optional flag for GDM methods
	}

	// Base methods without group parameters
	const baseMethods: Method[] = [
		{
			name: 'NIMBUS',
			path: '/interactive_methods/NIMBUS',
			description: 'NIMBUS method for MOO.',
			preferencesType: ['classification']
		},
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
			name: 'Reference Point',
			path: '/interactive_methods/reference-point',
			description: 'Reference Point method for MOO.',
			preferencesType: ['reference point']
		},
		{
			name: 'Group NIMBUS',
			path: '/interactive_methods/GNIMBUS',
			description: 'Group NIMBUS method for collaborative MOO.',
			preferencesType: ['classification'],
			supportsGroups: true
		},
		{
			name: 'GDM-SCORE-bands',
			path: '/interactive_methods/GDM-SCORE-bands',
			description: 'SCORE bands for GDM.',
			preferencesType: ['preferred ranges'],
			supportsGroups: true
		},
	];

	// Add group parameter to paths when needed
	const methods = $derived(
		baseMethods.map(method => ({
			...method,
			path: method.supportsGroups && data.groupId 
				? `${method.path}?group=${data.groupId}` 
				: method.path
		}))
	);

	type MethodFilterType = PreferenceType | 'all';

	let problemId: number | null = $state(null);
	let problem: ProblemInfo | null = $state(null);
	let searchQuery = $state('');
	let selectedPreferenceType = $state<MethodFilterType>('all');
	let isCompactView = $state(false);
	let selectedSessionId: number | null = $state(null);
	let selectedSessionInfo: string | null = $state(null);

	const { data } = $props<{
			data: {
				problems: ProblemInfo[],
				groupId?: string // This exists only in GDM when user comes to this page through group selecting page.
			} 
		}>();
	let problemList = data.problems ?? [];

	const preferenceTypes = [...new Set(baseMethods.flatMap((m) => m.preferencesType))];

	let selectedSessionLabel = $derived.by(() => {
		if (!selectedSessionId) return 'None';
		const info = selectedSessionInfo?.trim();
		return info && info.length > 0
			? `#${selectedSessionId} — ${info}`
			: `#${selectedSessionId}`;
	});

	let filteredMethods = $derived(
		methods.filter((method) => {
			const matchesSearch =
				searchQuery === '' ||
				method.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
				method.description.toLowerCase().includes(searchQuery.toLowerCase());

			const matchesPreference =
				selectedPreferenceType === 'all' || method.preferencesType.includes(selectedPreferenceType);
			
			const matchesGroupMode = data.groupId ? method.supportsGroups === true : method.supportsGroups !== true;

			return matchesSearch && matchesPreference && matchesGroupMode;
		})
	);

	// Button enable logic: for group methods, enable if groupId exists; for individual methods, enable if problem exists
	const isMethodEnabled = (method: Method) => {
		if (method.supportsGroups && data.groupId) {
			// Group method: enable if we have a groupId (DM users can access group problems they don't own)
			return true;
		} else {
			// Individual method: enable only if problem exists in user's problem list
			return !!problem;
		}
	};

	onMount(() => {
		problemId = $methodSelection.selectedProblemId;
		selectedSessionId = $methodSelection.selectedSessionId;
		selectedSessionInfo = $methodSelection.selectedSessionInfo;

		if (problemId) {
			problem = problemList.find((p: ProblemInfo) => String(p.id) === String(problemId));
		}
});
</script>

<div class="container mx-auto px-4 py-8">
	<div class="mb-8 space-y-4">
		<div class="flex items-center justify-between">
			<h1 class="text-3xl font-bold tracking-tight">Optimization Methods</h1>
			<div class="flex items-center gap-2">
				<Button
					variant="ghost"
					size="icon"
					class="hover:text-primary"
					onclick={() => (isCompactView = !isCompactView)}
				>
					{#if isCompactView}
						<LayoutGrid class="size-5" />
					{:else}
						<LayoutList class="size-5" />
					{/if}
				</Button>
			</div>
		</div>

		{#if problem}
			<div class="bg-secondary/20 flex items-center justify-between rounded-lg px-4 py-2">
				<p class="text-sm">
					Selected problem: <span class="text-primary font-bold">{problem.name}</span>
				</p>
				<Button variant="outline" size="sm" href="/problems">Change</Button>
			</div>
			<div class="bg-secondary/20 flex items-center justify-between rounded-lg px-4 py-2">
				<p class="text-sm">
					Selected session:
					<span class="text-primary font-bold">{selectedSessionLabel}</span>
				</p>
				<Button variant="outline" size="sm" href="/methods/sessions">Change</Button>
			</div>
		{:else if data.groupId}
			<div class="bg-info/10 flex items-center justify-between rounded-lg px-4 py-2">
				<p class="text-sm">
					Group mode: <span class="text-primary font-bold">Group ID {data.groupId}</span> 
					- Group methods are available for collaborative decision making
				</p>
				<Button variant="outline" size="sm" href="/groups">Back to Groups</Button>
			</div>
		{:else}
			<div class="bg-warning/10 flex items-center justify-between rounded-lg px-4 py-2">
				<p class="text-sm">Please select a problem to see suitable optimization methods</p>
				<Button variant="default" size="sm" href="/problems">Select problem</Button>
			</div>
		{/if}

		<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
			<div class="flex-1/2 max-w-sm">
				<div class="relative isolate">
					<!-- Added isolate to create a new stacking context -->
					<Search
						class="text-muted-foreground pointer-events-none absolute left-3 top-1/2 z-[1] size-4 -translate-y-1/2"
					/>
					<input
						type="text"
						placeholder="Search methods..."
						class="focus:ring-primary relative w-full rounded-md border py-2 pl-10 pr-4 text-sm focus:outline-none focus:ring-2"
						bind:value={searchQuery}
					/>
				</div>
			</div>
			<div class="flex flex-wrap gap-2">
				<Button
					variant={selectedPreferenceType === 'all' ? 'default' : 'outline'}
					size="sm"
					onclick={() => (selectedPreferenceType = 'all')}
				>
					All
				</Button>
				{#each preferenceTypes as type}
					<Button
						variant={selectedPreferenceType === type ? 'default' : 'outline'}
						size="sm"
						onclick={() => (selectedPreferenceType = type)}
					>
						{type}
					</Button>
				{/each}
			</div>
		</div>
	</div>

	{#if filteredMethods.length === 0}
		<div class="py-12 text-center">
			<p class="text-muted-foreground text-lg">No methods found matching your criteria</p>
		</div>
	{:else if isCompactView}
		<div class="space-y-2">
			{#each filteredMethods as method}
				<div
					class="hover:border-primary flex items-center justify-between rounded-lg border p-4 transition-colors"
				>
					<div class="flex-1">
						<h2 class="font-semibold">{method.name}</h2>
						<p class="text-muted-foreground text-sm">{method.description}</p>
					</div>
					<div class="flex items-center gap-2">
						<Button
							variant="outline"
							size="sm"
							disabled={!isMethodEnabled(method)}
							href={`${method.path}`}
							onclick={() => methodSelection.setMethod(method.name)}
							class={!isMethodEnabled(method) ? 'opacity-50' : 'hover:bg-secondary/90'}
						>
							<Play class="mr-2 size-4" />
							Use
						</Button>
					</div>
				</div>
			{/each}
		</div>
	{:else}
		<div class="grid gap-6 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
			{#each filteredMethods as method}
				<Card.Root class={`flex flex-col transition-all duration-300 hover:shadow-lg`}>
					<Card.Header class="space-y-2">
						<div class="flex items-center justify-between">
							<h2 class="text-primary text-2xl font-semibold">{method.name}</h2>
							<Button variant="ghost" size="icon" aria-label="Settings" class="hover:text-primary">
								<Settings class="size-4" strokeWidth={1.5} />
							</Button>
						</div>
						<p class="text-muted-foreground">{method.description}</p>
					</Card.Header>

					<Card.Content class="flex-grow space-y-4">
						{#if method.preferencesType}
							<div class="space-y-2">
								<h3 class="text-primary/80 font-semibold">Preference Types</h3>
								<div class="flex flex-wrap gap-2">
									{#each method.preferencesType as type}
										<span
											class="bg-secondary/20 text-secondary-foreground inline-block rounded px-2 py-1 text-xs font-semibold"
										>
											{type}
										</span>
									{/each}
								</div>
							</div>
						{/if}
					</Card.Content>

					<Card.Footer class="pt-4">
						<Button
							variant="default"
							disabled={!isMethodEnabled(method)}
							href={`${method.path}`}
							onclick={() => methodSelection.setMethod(method.name)}
							class="w-full justify-center {!isMethodEnabled(method) ? 'opacity-50' : 'hover:bg-primary/90'}"
						>
							<Play class="mr-2" size={18} />
							Use {method.name}
						</Button>
					</Card.Footer>
				</Card.Root>
			{/each}
		</div>
	{/if}
</div>
