/**
 * Store for global states that affect the overall UI behavior.
 * For now it includes errorMessage and isLoading, to manage loading states and error messages in http requests
 * using LoadingSpinner and ErrorAlert notification components.
 * @see '../lib/components/custom/notifications/loading-spinner.svelte'
 * @see '../lib/components/custom/notifications/error-alert.svelte'
 */

import { writable } from 'svelte/store';

export const errorMessage = writable<string | null>(null);
export const isLoading = writable(false);
