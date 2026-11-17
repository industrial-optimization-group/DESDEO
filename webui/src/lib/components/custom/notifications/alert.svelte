<script lang="ts">
	/**
	 * alert.svelte
	 *
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created September 2025
	 *
	 * @description
	 * This component displays a dismissible error alert as a notification at the top of the page.
	 * It can get its message from the global `errorMessage` store or from a `message` prop.
	 * It can show both error and info messages, with configurable styling and timeout.
	 * The alert automatically dismisses after a timeout and can also be closed manually with its
	 * close button, shown whenever closing has an effect (destructive alerts, or an `onClose`).
	 *
	 * @props
	 * @property {string | undefined} - The title of the alert.
	 * @property {string} [message] - Optional. The message to display. If not provided, it uses the value from the `errorMessage` store.
	 * @property {'default' | 'destructive'} [variant='default'] - The visual style of the alert
	 * @property {number} [timeout=10000] - The duration in milliseconds before the alert automatically closes. Set to 0 to disable auto-close.
	 *
	 * @features
	 * - Displays a styled error alert using the existing UI components.
	 * - Automatically disappears after a configurable timeout.
	 * - Can be used globally (reading from a store) or locally (passing a message prop).
	 *
	 * @dependencies
	 * - $lib/components/ui/alert: For the base alert styling.
	 * - ../../../../stores/error-store: For accessing and clearing the global error message.
	 * - svelte: For onMount lifecycle hook.
	 */
	import { Alert, AlertDescription, AlertTitle } from '$lib/components/ui/alert';
	import { errorMessage } from '../../../../stores/uiState';
	import { onMount } from 'svelte';
	import XIcon from '@lucide/svelte/icons/x';

	export let title: string | undefined = undefined;
	export let variant: 'default' | 'destructive' = 'default';
	export let message: string | undefined = undefined;
	export let timeout = 5000; // 5 seconds
	export let onClose: (() => void) | undefined = undefined;

	// Use the message prop if provided, otherwise fall back to the store's value.
    $: displayMessage = message ?? (variant === 'destructive' ? $errorMessage : null);

	// Closing clears the error store or calls onClose; without either it would do nothing.
	$: closable = variant === 'destructive' || onClose !== undefined;

	function handleClose() {
		if (variant === 'destructive') {
            errorMessage.set(null);
        }
		onClose?.();
	}

	onMount(() => {
		if (timeout > 0) {
			const timer = setTimeout(() => {
				handleClose();
			}, timeout);

			return () => clearTimeout(timer);
		}
	});
</script>

{#if displayMessage}
	<div class="alert-container">
		<Alert {variant} class={closable ? 'pr-10' : ''}>
			{#if title}<AlertTitle>{title}</AlertTitle>{/if}
			<AlertDescription class="whitespace-pre-line">{displayMessage}</AlertDescription>
			{#if closable}
				<button
					type="button"
					class="absolute top-2 right-2 rounded p-1 opacity-70 hover:opacity-100"
					aria-label="Close"
					on:click={handleClose}
				>
					<XIcon class="size-4" />
				</button>
			{/if}
		</Alert>
	</div>
{/if}

<style>
	.alert-container {
		position: fixed;
		top: 1rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 10000;
		box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
		width: auto;
		max-width: 90%;
	}
</style>
