import 'dotenv/config';
import { defineConfig } from 'orval';

// TODO: have something for production
const BASE_URL = process.env.API_BASE_URL;
const VITE_API_URL = process.env.VITE_API_URL;
// TODO: load from env like above
const OPENAPI_URL = 'http://localhost:8000/openapi.json' 

export default defineConfig({
    desdeo: {
        input: OPENAPI_URL,
        output: {
            mode: 'single',
            target: 'src/lib/gen/endpoints',
            schemas: 'src/lib/gen/models',
            client: 'fetch',
            baseUrl: `${BASE_URL}`,
            mock: false,
	    namingConvention: "PascalCase",
            override: {
                mutator: {
                    path: 'src/lib/api/new-client.ts',
                    name: 'customFetch',
                }
            }
        },
        hooks: {
            afterAllFilesWrite: 'prettier --write',
        },
    },
    desdeoZod: {
        input: OPENAPI_URL,
        output: {
            mode: 'single',
            client: 'zod',
            target: 'src/lib/gen/endpoints',
	    namingConvention: "PascalCase",
            fileExtension: 'zod.ts',
        },
        hooks: {
            afterAllFilesWrite: 'prettier --write',
        },
    },
});
