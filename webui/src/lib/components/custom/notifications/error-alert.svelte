<script lang="ts">
	/**
	 * error-alert.svelte
	 *
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created September 2025
	 *
	 * @description
	 * This component displays a dismissible error alert as a notification at the top of the page.
	 * It can get its message from the global `errorMessage` store or from a `message` prop.
	 * The alert automatically dismisses after a timeout and can also be closed manually.
	 *
	 * @props
	 * @property {string} [title='Error'] - The title of the alert.
	 * @property {string} [message] - Optional. The error message to display. If not provided, it uses the value from the `errorMessage` store.
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

	export let title = 'Error';
	export let message: string | undefined = undefined;
	export let timeout = 5000; // 5 seconds

	// Use the message prop if provided, otherwise fall back to the store's value.
	const displayMessage = message ?? $errorMessage;

	function handleClose() {
		errorMessage.set(null);
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
	<div class="error-alert">
		<Alert variant="destructive">
			<AlertTitle>{title}</AlertTitle>
			<AlertDescription>{displayMessage}</AlertDescription>
		</Alert>
	</div>
{/if}

<style>
	.error-alert {
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
