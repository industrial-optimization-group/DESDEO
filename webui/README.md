# DESDEO web-GUI

## Environment variables

For the frontend to work correctly, there are some environment variables that
should be set in a `.env` file at the root of the `webui/` directory. These
variables are:

- `VITE_API_URL` — set to `"/api"` so that client-side code routes requests
  through the SvelteKit catch-all proxy at `src/routes/api/[...path]/+server.ts`:

```bash
VITE_API_URL="/api"
```

- `API_BASE_URL` — the URL of the running DESDEO web-API, used by server-side
  route handlers and by `orval.config.mjs` when generating the OpenAPI client:

```bash
API_BASE_URL=http://localhost:8000
```

A minimal `.env` for local development therefore looks like:

```bash
API_BASE_URL="http://localhost:8000"
VITE_API_URL="/api"
```

> **Note:** `VITE_API_URL` is baked into the client bundle at build time by
> Vite, so changing it after a build has no effect. `API_BASE_URL` is read at
> runtime by the Node.js server process.

## Installing

To install the necessary packages to run the web-GUI locally, run

```bash
npm install
```

## Updating

To update the project's dependencies based on the version specifications in `package.json`, run

```bash
npm update
```

## Upgrading

To upgrade the project's dependencies, first install `npm-check-updates`:

```bash
npm install -g npm-check-updates
```

then run

```bash
ncu -u
```

this will upgrade the project's packages to their latest (mutually) compatible versions. **This can introduce breaking changes!**

## WSL / HTTP note

Auth cookies are set with `secure: !dev`, meaning they require HTTPS only in
production builds. In development mode (`npm run dev`), cookies are sent over
plain HTTP, which is necessary when running through WSL2 on Windows where the
browser may not treat the forwarded address as a secure context.

If you build and preview a production bundle locally over HTTP, authentication
will fail because `secure` cookies are not sent. Use `npm run dev` for local
development, or serve the production build behind HTTPS.

## Developing

Once the project's dependencies have been installed, start a development server:

```bash
npm run dev

# or start the server and open the app in a new browser tab
npm run dev -- --open
```

### Generating OpenAPI clients

When the web-API is updated, it is important to update the OpenAPI clients,
which automatically use the schemas defined in the web-API on the GUI side. To
generate them, make sure the web-API is running at the URL defined in
`OPENAPI_URL` inside `orval.config.mjs` (defaults to
`http://localhost:8000/openapi.json`), and that `API_BASE_URL` is set in your
`.env` file, then run:

```bash
npm run generate:client
```

## Building

To create a production version of your app:

```bash
npm run build
```

You can preview the production build with `npm run preview`.
