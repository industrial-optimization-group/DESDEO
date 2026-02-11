<script lang="ts">
	/**
	 * Input Dialog Component
	 *
	 * @author Stina <palomakistina@gmail.com>
	 * @created August 2025
	 *
	 * @description
	 * A general-purpose dialog component for collecting text input from users.
	 * This component is useful for various input collection scenarios such as:
	 * - Renaming items
	 * - Adding descriptions
	 * - Creating new entries
	 * - Collecting simple text input from users
	 *
	 * @props
	 * @property {boolean} open - Controls dialog visibility
	 * @property {string} title - Dialog title
	 * @property {string} description - Dialog description text
	 * @property {string} confirmText - Text for the confirm button (default: "Save")
	 * @property {string} cancelText - Text for the cancel button (default: "Cancel")
	 * @property {string} initialValue - Initial value for the input field
	 * @property {string} placeholder - Placeholder text for the input field
	 * @property {Function} onConfirm - Callback function invoked with input value when confirmed
	 * @property {Function} onCancel - Callback function invoked when canceled
	 *
	 * @example
	 * ```svelte
	 * <InputDialog
	 *   bind:open={showDialog}
	 *   title="Add Title"
	 *   description="Enter a title for this item."
	 *   placeholder="Title"
	 *   initialValue="Default Title"
	 *   onConfirm={(value) => handleConfirm(value)}
	 *   onCancel={() => console.log("Cancelled")}
	 * />
	 * ```
	 */
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';

	let {
		open = $bindable(false),
		title = "Enter Information",
		description = "Please provide the requested information.",
		confirmText = "Save",
		cancelText = "Cancel",
		initialValue = "",
		placeholder = "Enter text",
		onConfirm,
		onCancel
	} = $props<{
		open?: boolean;
		title?: string;
		description?: string;
		confirmText?: string;
		cancelText?: string;
		initialValue?: string;
		placeholder?: string;
		onConfirm?: (value: string) => void;
		onCancel?: () => void;
	}>();

	// Local state for the input field — re-sync when prop changes
	let inputValue = $state("");
	$effect(() => { inputValue = initialValue || ""; });

	function handleConfirm() {
		if (onConfirm) onConfirm(inputValue);
		open = false;
		// Reset the input field after closing
		inputValue = "";
	}

	function handleCancel() {
		if (onCancel) onCancel();
		open = false;
		// Reset the input field after closing
		inputValue = "";
	}

	// When the component opens with a new initialValue, update the local state
	$effect(() => {
		if (open && initialValue !== undefined) {
			inputValue = initialValue;
		}
	});
</script>

<Dialog.Root bind:open>
	<Dialog.Content>
		<Dialog.Header>
			<Dialog.Title>{title}</Dialog.Title>
			<Dialog.Description>{description}</Dialog.Description>
		</Dialog.Header>
		<div class="py-4">
			<Input
				type="text"
				{placeholder}
				bind:value={inputValue}
			/>
		</div>
		<Dialog.Footer>
			<Button variant="outline" onclick={handleCancel}>
				{cancelText}
			</Button>
			<Button variant="default" onclick={handleConfirm}>
				{confirmText}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
