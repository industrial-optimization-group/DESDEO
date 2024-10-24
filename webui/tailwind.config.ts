import type { Config } from 'tailwindcss';

import { join } from 'path';
import forms from '@tailwindcss/forms';
import { skeleton } from '@skeletonlabs/skeleton/plugin';
import * as themes from '@skeletonlabs/skeleton/themes';

/** @type {import('tailwindcss').Config} \*/
export default {
	darkMode: "selector",
	content: [
		'./src/**/*.{html,js,svelte,ts}',
		join(require.resolve('@skeletonlabs/skeleton-svelte'), '../**/*.{html,js,svelte,ts}')
	],

	theme: {
		extend: {}
	},

	plugins: [
		forms,
		skeleton({
			themes: [themes.hamlindigo]
		})
	]
} as Config;
