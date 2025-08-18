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
</script>

<Sidebar.Root side="right" class="fixed right-0 top-12 h-[calc(100vh-3rem)]">
	<Sidebar.Header>
		<span>Solution Explanations</span>
		<p class="mt-1 text-xs font-normal text-gray-500">
			Understand why these solutions were generated and their trade-offs.
			Explanations are only available for solutions from the current iteration.
		</p>
	</Sidebar.Header>
	<Sidebar.Content class="px-4">
		{#each results as result}
			<span>{result.objective_values}
			</span>
		{/each}

	</Sidebar.Content>
	<Sidebar.Rail />
</Sidebar.Root>
