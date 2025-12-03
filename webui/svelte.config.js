import { mdsvex } from 'mdsvex';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

let adapter;

// We dynamically set the adapter, so we can use a different one for the production version.
if (process.env.NPM_RUN === 'start:production') {
  const { default: node } = await import('@sveltejs/adapter-node');
  adapter = node();
} else {
  const { default: auto } = await import('@sveltejs/adapter-auto');
  adapter = auto();
}

const config = {
  preprocess: [vitePreprocess(), mdsvex()],
  kit: { adapter },
  extensions: ['.svelte', '.svx']
};

export default config;
