# DESDEO web-GUI
## Environment variables

For the frontend to work correctly, there are some environmental variables
that should be set in an`.env` file at the root level. These variables are:

- `PUBLIC_API_URL`: the url that points to DESDEO's web-API.

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

this will upgrade the project's packages to their latest (mutually) compatible versions. __This can introduce breaking changes!__


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
