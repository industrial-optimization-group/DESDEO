<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import PreferenceSwitcher from './preference-switcher.svelte';
	import { writable } from 'svelte/store';
	import type { components } from '$lib/api/client-types';

	type ProblemInfo = components['schemas']['ProblemInfo'];

	export let ref: HTMLElement | null = null;
	export let preference_types: string[] = ['Reference point', 'Ranges', 'Preferred solution'];
	export let problem: ProblemInfo | null = null;

	// Store for the currently selected preference type
	const selectedPreference = writable(preference_types[0]);
</script>

<Sidebar.Root
	bind:ref
	collapsible="none"
	class="top-12 flex h-[calc(100vh-6rem)] min-h-[calc(100vh-3rem)]"
>
	<Sidebar.Header>
		{#if preference_types.length > 1}
			<PreferenceSwitcher
				preferences={preference_types}
				defaultPreference={preference_types[0]}
				onswitch={(e: string) => selectedPreference.set(e)}
			/>
		{:else}
			<Sidebar.MenuButton
				size="lg"
				class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
			>
				<div class="flex flex-col gap-0.5 leading-none">
					<span class="font-semibold">Preference information</span>
					<span class="text-primary-500">{$selectedPreference}</span>
				</div>
			</Sidebar.MenuButton>
		{/if}
	</Sidebar.Header>
	<Sidebar.Content class="h-full px-4">
		{#if $selectedPreference === 'Reference point'}
			<p class="mb-2 text-sm text-gray-500">Provide one desirable value for each objective.</p>
			{problem?.objectives}
			<!-- 			{#each problem?.objectives as item}
				<div class="mb-1">
					<span>{item.name} (Ideal: {item.ideal}, Nadir: {item.nadir})</span>
				</div>
			{/each} -->
		{:else if $selectedPreference === 'Ranges'}
			<p class="mb-2 text-sm text-gray-500">
				Provide a range for each objective, indicating the minimum and maximum acceptable values.
			</p>
			<!-- 			{#each objectives as item}
				<div class="mb-1">
					<span>{item.name} (Min: {item.ideal}, Max: {item.nadir})</span>
				</div>
			{/each} -->
		{:else if $selectedPreference === 'Preferred solution'}
			<p class="mb-2 text-sm text-gray-500">Select one or multiple preferred solutions.</p>
			<!-- 			{#each objectives as item}
				<div class="mb-1">
					<span>{item.name}</span>
				</div>
			{/each} -->
		{:else}
			<p>Select a preference type to view options.</p>
		{/if}
	</Sidebar.Content>
	<Sidebar.Rail />
</Sidebar.Root>
