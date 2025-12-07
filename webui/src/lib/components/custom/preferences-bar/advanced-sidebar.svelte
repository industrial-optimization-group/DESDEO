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
	import type { ProblemInfo, Solution, SolutionType, MethodMode, PeriodKey } from '$lib/types';

	interface Props {
		problem: ProblemInfo;
		preferenceValues: number[];
		solutions: Array<Solution>;
		multipliers: Array<Record<string, number> | null>; // Fixed: Remove nested array
		selectedSolutions?: Array<number>;
		handleObjectiveClick?: (index: number) => void;
		ref?: HTMLElement | null;
	}

	let {
		problem,
		preferenceValues,
		solutions,
		multipliers,
		selectedSolutions,
		handleObjectiveClick,
		ref = null
	}: Props = $props();
	// Store for solution details including Lagrange multipliers
	let solutionDetails: Record<string, any> = $state({});
</script>

<Sidebar.Root side="right" class="fixed right-0 top-12 h-[calc(100vh-3rem)]">
	<Sidebar.Header>
		<span>Solution Analysis</span>
		<p class="mt-1 text-xs font-normal text-gray-500">
			Detailed analysis of the selected solution ({selectedSolutions
				? selectedSolutions.join(', ')
				: 'none'}).
		</p>
	</Sidebar.Header>
	<Sidebar.Content class="px-4">
		{#if solutions.length === 0}
			<div class="py-8 text-center text-sm text-gray-500">No solutions available to analyze.</div>
		{:else if selectedSolutions == null || selectedSolutions.length === 0}
			<div class="py-8 text-center text-sm text-gray-500">
				Please select a solution to view its analysis.
			</div>
		{:else}
			<div class="mb-6 rounded-lg border bg-white p-4 shadow-sm">
				<h4 class="mb-3 text-lg font-semibold">
					{solutions[selectedSolutions[0]].name == null
						? 'Solution ' + (selectedSolutions[0] + 1)
						: solutions[selectedSolutions[0]].name}
				</h4>

				<!-- Objective values -->
				<div class="mb-4">
					<h5 class="mb-2 text-sm font-medium text-gray-700">Objective Values:</h5>
					<div class="space-y-1">
						{#if multipliers && multipliers[0]}
							<div class="mb-4">
								<h5 class="mb-2 text-sm font-medium text-gray-700">Lagrange Multipliers:</h5>
								<div class="space-y-1">
									{#each Object.entries(multipliers[0] ?? {}) as [objName, value]}
										<div class="flex justify-between rounded bg-blue-50 p-2 text-xs">
											<span class="font-medium">{objName}:</span>
											<span class="font-mono"
												>{formatNumber(Number(value), SIGNIFICANT_DIGITS)}</span
											>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	</Sidebar.Content>
	<Sidebar.Rail />
</Sidebar.Root>
