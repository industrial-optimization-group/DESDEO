<script lang="ts">
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import type { components } from '$lib/api/client-types';
	import { onMount } from 'svelte';
	type ProblemInfo = components['schemas']['ProblemInfo'];
	import * as Menubar from '$lib/components/ui/menubar/index.js';
	let problem: ProblemInfo | null = $state(null);

	const { data } = $props<{ data: ProblemInfo[] }>();
	let problemList = data.problems ?? [];

	onMount(() => {
		if ($methodSelection.selectedProblemId) {
			problem = problemList.find(
				(p: ProblemInfo) => String(p.id) === String($methodSelection.selectedProblemId)
			);
		}
		//console.log('problemList:', problem);
	});
</script>

<div class="flex min-h-[calc(100vh-3rem)]">
	<AppSidebar {problem} preference_types={['Reference point']} />

	<div class="flex-1">
		<Resizable.PaneGroup direction="vertical">
			<Resizable.Pane class="p-2">
				<div class="flex-row">
					<div class="flex flex-row items-center justify-between gap-4">
						<div class="font-semibold">Solution explorer</div>
						<div>
							<span>View: </span>
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
				<span>Best candidates</span>
			</Resizable.Pane>
		</Resizable.PaneGroup>
	</div>
</div>
