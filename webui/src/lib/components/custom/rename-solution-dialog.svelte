<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';

	let {
		open = $bindable(false),
		title = "Rename Solution",
		description = "Enter a new name for this solution.",
		confirmText = "Save",
		cancelText = "Cancel",
		initialName = "",
		onConfirm,
		onCancel
	} = $props<{
		open?: boolean;
		title?: string;
		description?: string;
		confirmText?: string;
		cancelText?: string;
		initialName?: string;
		onConfirm?: (name: string) => void;
		onCancel?: () => void;
	}>();

	// Local state for the input field
	let solutionName = $state(initialName || "");

	function handleConfirm() {
		if (onConfirm) onConfirm(solutionName);
		open = false;
		// Reset the input field after closing
		solutionName = "";
	}

	function handleCancel() {
		if (onCancel) onCancel();
		open = false;
		// Reset the input field after closing
		solutionName = "";
	}

	// When the component opens with a new initialName, update the local state
	$effect(() => {
		if (open && initialName !== undefined) {
			solutionName = initialName;
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
				placeholder="Solution name"
				bind:value={solutionName}
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
