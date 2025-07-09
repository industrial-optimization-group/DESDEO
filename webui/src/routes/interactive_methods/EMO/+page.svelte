<script lang="ts">
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import AdvancedSidebar from '$lib/components/custom/preferences-bar/advanced-sidebar.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import * as Menubar from '$lib/components/ui/menubar/index.js';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import type { components } from '$lib/api/client-types';
	import { onMount } from 'svelte';
	type ProblemInfo = components['schemas']['ProblemInfo'];
	let problem: ProblemInfo | null = $state(null);
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { Combobox } from '$lib/components/ui/combobox';
	import { PREFERENCE_TYPES } from '$lib/constants';

	const { data } = $props<{ data: ProblemInfo[] }>();

	let problemList = data.problems ?? [];
	let selectedTypeSolutions = $state('current');

	let currentPreference = $state({ type: '', value: [] });
	let previousPreference = $state({ type: '', value: [] });
	let selectedSolution = $state<number[]>([]);

	const type_solutions_to_visualize = [
		{ value: 'current', label: 'Current solutions' },
		{ value: 'best', label: 'Best solutions' },
		{ value: 'all', label: 'All solutions' }
	];

	function handleChange(event: { value: string }) {
		selectedTypeSolutions = event.value;
		console.log('Selected type of solutions:', selectedTypeSolutions);
	}

	function handleIterate(event: { preferenceType: string; preferenceValue: any }) {
		console.log('Iterate event:', event);
		previousPreference.type = currentPreference.type;
		previousPreference.value = currentPreference.value;
		currentPreference.type = event.preferenceType;
		currentPreference.value = event.preferenceValue;
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
			preference_types={[
				PREFERENCE_TYPES.ReferencePoint,
				PREFERENCE_TYPES.PreferredRange,
				PREFERENCE_TYPES.PreferredSolution
			]}
			showNumSolutions={true}
			onIterate={handleIterate}
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
								options={type_solutions_to_visualize}
								defaultSelected={selectedTypeSolutions}
								onChange={handleChange}
							/>
						</div>
					</div>

					<div class="h-full w-full">
						<!-- Desktop: two columns, Mobile: two rows -->
						<div class="grid h-full w-full gap-4 xl:grid-cols-1">
							<div class="min-h-[50rem] flex-1 rounded bg-gray-100 p-4">
								<span>Objective space</span>
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

	<AdvancedSidebar />
</div>
