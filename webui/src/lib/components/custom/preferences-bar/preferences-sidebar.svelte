<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import type { ComponentProps } from 'svelte';
	import PreferenceSwitcher from './preference-switcher.svelte';

	export let ref: HTMLElement | null = null;
	// Add any other props you want to accept here

	// sample data
	const data = {};
	const preference_types = ['Reference point', 'Ranges', 'Preferred solution'];
	const problem_name = 'Sample Problem';
	const objectives = [
		{ name: 'Drag', direction: 'minimize', ideal: 0.1, nadir: 1.0 },
		{ name: 'Weight', direction: 'minimize', ideal: 100, nadir: 500 },
		{ name: 'Energy Consumption', direction: 'minimize', ideal: 50, nadir: 300 }
	];
</script>

<Sidebar.Root
	bind:ref
	collapsible="none"
	class="top-12 flex h-[calc(100vh-6rem)]   min-h-[calc(100vh-3rem)]"
>
	<Sidebar.Header>
		<PreferenceSwitcher versions={preference_types} defaultVersion={preference_types[0]} />

		<!-- 		<span>Preference information</span>
		<p class="mt-1 text-xs font-normal text-gray-500">
			Here you can review and adjust your preferences for the selected problem and its objectives.
		</p> -->
	</Sidebar.Header>
	<Sidebar.Content class="h-full px-4">
		<!-- We create a Sidebar.Group for each parent. -->

		{#each objectives as item}
			<span>{item.name}</span>
		{/each}
	</Sidebar.Content>
	<Sidebar.Rail />
</Sidebar.Root>
