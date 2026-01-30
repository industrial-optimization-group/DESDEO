import { describe, test, expect, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';

vi.mock('sveltekit-superforms', () => ({
	superForm: () => ({
		form: writable({
			username: '',
			password: ''
		}),
		enhance: () => undefined
	})
}));

describe('/home/+page.svelte', () => {
	test('should render h1', async () => {
		const { default: Page } = await import('./home/+page.svelte');
		render(Page, { data: { form: {} } });
		expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
	}, 10000);
});
