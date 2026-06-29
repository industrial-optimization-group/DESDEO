import { defineConfig } from '@playwright/test';

export default defineConfig({
	webServer: {
		command: 'npm run build && npm run preview',
		port: 4173
	},
	testDir: '.',
	testMatch: ['e2e/**/*.test.ts', 'tests/**/*.spec.ts'],
	use: {
		launchOptions: {
			args: ['--start-maximized']
		}
	},
	projects: [
		{
			name: 'setup',
			testMatch: 'tests/auth.setup.ts'
		},
		{
			name: 'gdm-score',
			testMatch: 'tests/**/*.spec.ts',
			dependencies: ['setup']
		},
		{
			name: 'e2e',
			testMatch: 'e2e/**/*.test.ts'
		}
	]
});
