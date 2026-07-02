import 'dotenv/config';
import { defineConfig } from 'orval';

const BASE_URL = process.env.API_BASE_URL ?? 'http://localhost:8000';
const VITE_API_URL = process.env.VITE_API_URL;
const OPENAPI_URL = process.env.OPENAPI_URL ?? 'http://localhost:8000/openapi.json';

export default defineConfig({
    desdeo: {
        input: OPENAPI_URL,
        output: {
            mode: 'single',
            target: 'src/lib/gen/endpoints',
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
            override: {
                zod: {
                    generate: {
                        body: true,
                        param: true,
                        query: true,
                        header: true,
                        response: true,
                    },
                },
            },
        },
        hooks: {
            afterAllFilesWrite: 'prettier --write',
        },
    },
});
