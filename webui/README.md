# DESDEO web-GUI

## Environment variables

For the frontend to work correctly, there are some environmental variables
that should be set in an`.env` file at the root level. These variables are:

- `VITE_API_URL` which should be defined to be '/api' for the proxy to work correctly. I.e.:

```bash
VITE_API_URL="/api"
```

- `API_URL` which should be defined to be 'http://localhost:8000 or the path of the server'

```bash
API_URL=http://localhost:8000
```

Check also the file `vite.config.ts`, where in the server setting

```toml
	server: {
		proxy: {
			'/api': {
				target: 'http://127.0.0.1:8000',
				changeOrigin: true,
				secure: false,
				rewrite: (path) => path.replace(/^\/api/, '')
			}
		}
	}
```

the `target` should point to the local URL that can be used to access the DESDEO web-API.

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

## Developing

Once the project's dependencies have been installed, start a development server:

```bash
npm run dev

# or start the server and open the app in a new browser tab
npm run dev -- --open
```

### Generating OpenAPI clients

When the web-API is updated, it is important to update the OpenAPI clients, which automatically use the schemas defined in the web-API
on the GUI side. To generate them, make sure the web-API is running, and issue the command:

```bash
npm run generate:client
```

## Building

To create a production version of your app:

```bash
npm run build
```

You can preview the production build with `npm run preview`.
