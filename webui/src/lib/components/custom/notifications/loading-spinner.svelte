<script lang="ts">
	/**
	 * loading-spinner.svelte
	 *
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created September 2025
	 *
	 * @description
	 * This component displays a full-screen loading overlay with a spinner and optional text.
	 * It is used to indicate that a background process is running and to prevent user interaction with the page content.
	 *
	 * @props
	 * @property {string} [text=''] - Optional text to display next to the spinner. Defaults to 'Calculating...' if empty.
	 *
	 * @features
	 * - Full-screen overlay to block UI interaction.
	 * - CSS-based spinner animation.
	 * - Customizable text.
	 */
	export let text = '';
</script>

<div class="loading-overlay">
	<div class="loading-box">
		<div class="spinner"></div>
		{text}
	</div>
</div>

<style>
	.loading-overlay {
		position: fixed;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		justify-content: center;
		align-items: center;
		z-index: 9999;
		cursor: wait;
	}

	.loading-box {
		background-color: white;
		padding: 2rem;
		border-radius: 8px;
		box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
		display: flex;
		align-items: center;
		gap: 1rem;
		font-size: 1.2rem;
		color: #333;
	}

	.spinner {
		border: 4px solid rgba(0, 0, 0, 0.1);
		width: 24px;
		height: 24px;
		border-radius: 50%;
		border-left-color: #09f;
		animation: spin 1s ease infinite;
	}

	@keyframes spin {
		0% {
			transform: rotate(0deg);
		}
		100% {
			transform: rotate(360deg);
		}
	}
</style>
