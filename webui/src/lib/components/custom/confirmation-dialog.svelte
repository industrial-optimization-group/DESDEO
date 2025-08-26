<script lang="ts">
	/**
	 * Confirmation Dialog Component
	 * 
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created August 2025
	 * 
	 * @description
	 * A reusable confirmation dialog component that displays a modal with a title,
	 * description, and confirm/cancel buttons.
	 * 
	 * @props
	 * @property {boolean} open - Whether the dialog is open or not. Bindable with Svelte runes.
	 * @property {string} title - The dialog title (default: "Confirm Action")
	 * @property {string} description - The dialog description/message (default: "Are you sure you want to proceed?")
	 * @property {string} confirmText - Text for the confirm button (default: "Confirm")
	 * @property {string} cancelText - Text for the cancel button (default: "Cancel")
	 * @property {Function} onConfirm - Callback function executed when confirm is clicked
	 * @property {Function} onCancel - Optional callback function executed when cancel is clicked
	 * @property {string} confirmVariant - Button variant for confirm button 
	 *                    (default: "default", options: "default", "destructive", "outline", "secondary", "ghost", "link")
	 * 
	 * @example
	 * ```svelte
	 * <ConfirmationDialog
	 *   bind:open={showDialog}
	 *   title="Delete Item"
	 *   description="Are you sure you want to delete this item?"
	 *   confirmText="Delete"
	 *   cancelText="Cancel"
	 *   onConfirm={() => handleDelete(id)}
	 *   confirmVariant="destructive"
	 * />
	 * ```
	 * 
	 * @dependencies
	 * - $lib/components/ui/dialog - UI dialog component
	 * - $lib/components/ui/button - UI button component
	 */
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';

	let {
		open = $bindable(false),
		title = "Confirm Action",
		description = "Are you sure you want to proceed?",
		confirmText = "Confirm",
		cancelText = "Cancel",
		onConfirm,
		onCancel,
		confirmVariant = "default" as "default" | "destructive" | "outline" | "secondary" | "ghost" | "link"
	}: {
		open?: boolean;
		title?: string;
		description?: string;
		confirmText?: string;
		cancelText?: string;
		onConfirm?: () => void;
		onCancel?: () => void;
		confirmVariant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
	} = $props();

	function handleConfirm() {
		onConfirm?.();
		open = false;
	}

	function handleCancel() {
		onCancel?.();
		open = false;
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content>
		<Dialog.Header>
			<Dialog.Title>{title}</Dialog.Title>
			<Dialog.Description>{description}</Dialog.Description>
		</Dialog.Header>
		<Dialog.Footer>
			<Button variant="outline" onclick={handleCancel}>
				{cancelText}
			</Button>
			<Button variant={confirmVariant} onclick={handleConfirm}>
				{confirmText}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
