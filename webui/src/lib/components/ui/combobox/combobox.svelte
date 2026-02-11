<script lang="ts">
	/**
	 * Combobox.svelte
	 *
	 * @author Giomara Larraga <glarragw@jyu.fi>
	 * @created June 2025
	 *
	 * @description
	 * A reusable combobox (dropdown select) component with search/filter support.
	 * Uses Popover and Command UI primitives for accessibility and keyboard navigation.
	 *
	 * @props
	 * - options: { value: string; label: string }[] — List of selectable options.
	 * - placeholder?: string — Optional placeholder text.
	 * - defaultSelected?: string — Optional default selected value.
	 * - onChange: (event: { value: string }) => void — Callback fired when selection changes.
	 * - showSearch?: boolean — Whether to show the search input (default: false).
	 */

	import CheckIcon from '@lucide/svelte/icons/check';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import { tick } from 'svelte';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { cn } from '$lib/utils.js';

	const {
		options,
		placeholder = 'Select an option...',
		defaultSelected,
		onChange,
		showSearch = false
	} = $props<{
		options: { value: string; label: string }[];
		placeholder?: string;
		defaultSelected?: string;
		onChange: (event: { value: string }) => void;
		showSearch?: boolean;
	}>();

	let open = $state(false);
	let triggerRef: HTMLButtonElement | null = $state(null);
	let selected = $state('');

	// Sync with defaultSelected prop
	$effect(() => {
		selected = defaultSelected ?? '';
	});

	/**
	 * Returns the label of the currently selected value.
	 */
	const selectedValue = () => options.find((f: any) => f.value === selected)?.label;

	/**
	 * Closes the popover and focuses the trigger button.
	 */
	function closeAndFocusTrigger() {
		open = false;
		tick().then(() => {
			triggerRef?.focus();
		});
	}

	/**
	 * Handles selection of a value.
	 * @param val - The selected value.
	 */
	function selectValue(val: string) {
		selected = val;
		onChange({ value: val });
		closeAndFocusTrigger();
	}
</script>

<Popover.Root bind:open>
	<Popover.Trigger bind:ref={triggerRef}>
		<Button
			variant="outline"
			class="w-[200px] justify-between"
			role="combobox"
			aria-expanded={open}
		>
			{selectedValue() || placeholder}
			<ChevronsUpDownIcon class="opacity-50" />
		</Button>
	</Popover.Trigger>

	<Popover.Content class="w-[200px] p-0">
		<Command.Root>
			{#if showSearch}
				<Command.Input placeholder="Search..." />
			{/if}
			<Command.List>
				<Command.Empty>No results found.</Command.Empty>
				<Command.Group value="options">
					{#each options as option (option.value)}
						<Command.Item value={option.value} onSelect={() => selectValue(option.value)}>
							<CheckIcon class={cn(selected !== option.value && 'text-transparent')} />
							{option.label}
						</Command.Item>
					{/each}
				</Command.Group>
			</Command.List>
		</Command.Root>
	</Popover.Content>
</Popover.Root>
