<script lang="ts">
	//import { createEventDispatcher } from 'svelte';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import CheckIcon from '@lucide/svelte/icons/check';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';

	//const dispatch = createEventDispatcher();
	//export let preferences: string[] = [];
	//export let selectedPreference: string = preferences[0] || '';
	let {
		preferences,
		defaultPreference,
		onswitch
	}: { preferences: string[]; defaultPreference: string; onswitch: any } = $props();
	let selectedPreference = $state(defaultPreference);

	// Watch for changes and dispatch event
	//$: dispatch('switch', selectedPreference);
</script>

<Sidebar.Menu>
	<Sidebar.MenuItem>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Sidebar.MenuButton
						size="lg"
						class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
						{...props}
					>
						<div class="flex flex-col gap-0.5 leading-none">
							<span class="font-semibold">Preference information</span>
							<span class="text-primary-500">{selectedPreference}</span>
						</div>
						<ChevronsUpDownIcon class="ml-auto" />
					</Sidebar.MenuButton>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content class="w-(--bits-dropdown-menu-anchor-width)" align="start">
				{#each preferences as preference (preference)}
					<DropdownMenu.Item
						onSelect={() => {
							onswitch(preference);
							selectedPreference = preference;
						}}
					>
						{preference}
						{#if preference === selectedPreference}
							<CheckIcon class="ml-auto" />
						{/if}
					</DropdownMenu.Item>
				{/each}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</Sidebar.MenuItem>
</Sidebar.Menu>
