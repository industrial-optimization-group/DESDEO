import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, loadEnv } from 'vite';
import path from 'path';

export default defineConfig(({ mode }) => {
  // Load .env into process.env explicitly. Vite's built-in env handling only exposes VITE_-
  // prefixed vars to client code via import.meta.env — it does NOT populate raw process.env for
  // server-side code (e.g. src/lib/api/new-client.ts's `process.env.API_BASE_URL` lookup, used
  // by every server-rendered/server-action API call). Without this, that lookup silently falls
  // back to the wrong default port unless API_BASE_URL happens to already be set in whatever
  // shell launched `npm run dev` — the second (empty-string) argument means "load every var in
  // .env, not just VITE_-prefixed ones", matching what non-VITE_ vars like API_BASE_URL need.
  Object.assign(process.env, loadEnv(mode, process.cwd(), ''));

  return {
    plugins: [tailwindcss(), sveltekit()],
    resolve: {
      alias: {
        $custom: path.resolve('./src/lib/components/custom'),
        // ...other aliases
      }
    },
    optimizeDeps: {
      exclude: ['mathlive']
    }
  };
});
