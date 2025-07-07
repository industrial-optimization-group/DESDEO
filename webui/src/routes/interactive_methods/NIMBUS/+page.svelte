<script lang="ts">
	/**
	 * +page.svelte (NIMBUS method)
	 *
	 * @author Stina (Functionality) <palomakistina@gmail.com>
	 * @author Giomara Larraga (Base structure)<glarragw@jyu.fi>
	 * @created July 2025
	 *
	 * @description
	 * This page implements the NIMBUS interactive multiobjective optimization method in DESDEO.
	 * It displays a sidebar with problem information, a solution explorer with a combobox to select solution types,
	 * and a resizable pane layout for visualizing the objective and decision spaces, as well as solution tables.
	 *
	 * @props
	 * @property {Object} data - Contains a list of optimization problems fetched from the server.
	 * @property {ProblemInfo[]} data.problems - List of problems.
	 *
	 * @features
	 * - Sidebar with problem information and preference types.
	 * - Solution explorer with a combobox to select between "Current", "Best", and "All" solutions.
	 * - Responsive, resizable layout using PaneGroup and Pane components.
	 * - Visualization placeholders for objective and decision spaces.
	 * - Tabbed interface for numerical values and saved solutions.
	 *
	 * @dependencies
	 * - AppSidebar: Sidebar component for preferences and problem info.
	 * - Combobox: Custom combobox component for solution type selection.
	 * - Resizable: UI components for resizable panes.
	 * - Tabs: UI components for tabbed content.
	 * - methodSelection: Svelte store for the currently selected problem.
	 * - OpenAPI-generated ProblemInfo type.
	 *
	 * @notes
	 * - The selected problem is determined from the methodSelection store.
	 * - Visualization and table content are placeholders and should be implemented as needed.
	 */
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import type { components } from '$lib/api/client-types';
	import { onMount } from 'svelte';
	import { Combobox } from '$lib/components/ui/combobox';
	type ProblemInfo = components['schemas']['ProblemInfo'];
	let problem: ProblemInfo | null = $state(null);
	import * as Tabs from '$lib/components/ui/tabs/index.js';

	const { data } = $props<{ data: ProblemInfo[] }>();
	let problemList = data.problems ?? [];
	let selectedTypeSolutions = 'current';

	// State for preferences and numSolutions - ready for your HTTP request button
	let currentPreference: number[] = $state([]);
	let currentNumSolutions: number = $state(1);

	const frameworks = [
		{ value: 'current', label: 'Current solutions' },
		{ value: 'best', label: 'Best solutions' },
		{ value: 'all', label: 'All solutions' }
	];

	function handleChange(event: { value: string }) {
		selectedTypeSolutions = event.value;
		console.log('Selected type of solutions:', selectedTypeSolutions);
	}

	function handlePreferenceChange(event: { value: string; preference: number[]; numSolutions: number }) {
		currentPreference = event.preference;
		currentNumSolutions = event.numSolutions;
		console.log('Updated preference:', currentPreference);
		console.log('Updated numSolutions:', currentNumSolutions);
		// This is where you can add other logic when preferences change
	}

	onMount(() => {
		if ($methodSelection.selectedProblemId) {
			problem = problemList.find(
				(p: ProblemInfo) => String(p.id) === String($methodSelection.selectedProblemId)
			);
		}
	});
</script>

<div class="flex min-h-[calc(100vh-3rem)]">
	{#if problem}
		<AppSidebar 
			{problem} 
			preference_types={['Classification']} 
			showNumSolutions={true} 
			bind:preference={currentPreference}
			bind:numSolutions={currentNumSolutions}
			minNumSolutions={1}
			maxNumSolutions={4}
			onChange={handlePreferenceChange}
		/>
	{/if}

	<div class="flex-1">
		<Resizable.PaneGroup direction="vertical">
			<Resizable.Pane class="p-2">
				<div class="flex-row">
					<div class="flex flex-row items-center justify-between gap-4 pb-2">
						<div class="font-semibold">Solution explorer</div>
						<div>
							<span>View: </span>
							<Combobox
								options={frameworks}
								defaultSelected={selectedTypeSolutions}
								onChange={handleChange}
							/>
						</div>
					</div>

					<div class="h-full w-full">
						<!-- Desktop: two columns, Mobile: two rows -->
						<div class="grid h-full w-full gap-4 xl:grid-cols-2">
							<div class="min-h-[50rem] flex-1 rounded bg-gray-100 p-4">
								<span>Objective space</span>
							</div>
							<div class="min-h-[50rem] flex-1 rounded bg-gray-100 p-4">
								<span>Decision space</span>
							</div>
						</div>
					</div>
				</div>
			</Resizable.Pane>
			<Resizable.Handle />
			<Resizable.Pane class="p-2">
				<Tabs.Root value="numerical-values">
					<Tabs.List>
						<Tabs.Trigger value="numerical-values">Numerical values</Tabs.Trigger>
						<Tabs.Trigger value="saved-solutions">Saved solutions</Tabs.Trigger>
					</Tabs.List>
					<Tabs.Content value="numerical-values">Table of solutions</Tabs.Content>
					<Tabs.Content value="saved-solutions">Visualize saved solutions</Tabs.Content>
				</Tabs.Root>
			</Resizable.Pane>
		</Resizable.PaneGroup>
	</div>
</div>
