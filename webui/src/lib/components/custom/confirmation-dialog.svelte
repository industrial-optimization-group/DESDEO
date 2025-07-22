<script lang="ts">
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
