# How to deploy DESDEO on OpenShift (Kubernetes)

## Overview

This guide walks through deploying the full DESDEO stack, FastAPI backend,
SvelteKit web UI, and PostgreSQL database, on an OpenShift/OKD cluster. [CSC
Rahti](https://rahti.csc.fi/) is used as the concrete example throughout; values
specific to Rahti (hostnames, API endpoint, image registry URL) are marked so
readers on other OpenShift clusters can substitute their own.

Two approaches are documented:

- **CLI approach**: uses YAML manifests and the `oc` CLI (command-line interface)
  exclusively. Every step is reproducible and version-controlled. The bulk of
  this guide follows this approach.
- **Web console approach**: uses the Rahti web interface. Described under
  [Alternative web console approach](#web-console-approach) for
  users who prefer a graphical interface.

OpenShift is a Kubernetes distribution with extra features layered on top. This
guide uses OpenShift-specific objects (BuildConfig, ImageStream, Route) that do
not exist in vanilla Kubernetes. If you are deploying on plain Kubernetes,
consult your platform's documentation instead.

The files you will work with live in two places in the DESDEO repository:

- `deploy/`: all OpenShift manifests (ImageStreams, BuildConfigs, Deployments,
  StatefulSet, Routes, Job).
- Several application-level files added or modified to support production
  deployment, described under [Repository preparation](#repository-preparation).

## Prerequisites

- A CSC account with an active computing project.
- Rahti access enabled for that project. Apply via
  [MyCSC](https://my.csc.fi) -> your project -> Services -> Rahti -> Apply for
  access. See [Rahti access](https://docs.csc.fi/cloud/rahti/access/) for
  details.
- A Rahti project created in the [Rahti web console](https://console-openshift-console.apps.2.rahti.csc.fi/).
  When creating the project, include your CSC computing project number in the
  description field using the format `csc_project:#######`.
- `oc` CLI installed (see [Using the Rahti CLI](https://docs.csc.fi/cloud/rahti/usage/cli/)).
- Logged in to the cluster:
  ```bash
  oc login https://api.2.rahti.csc.fi:6443 --token=<token>
  ```
- Switched to your project:
  ```bash
  oc project <your-project>
  ```
- A fork or branch of the [DESDEO repository](https://github.com/industrial-optimization-group/DESDEO)
  with the `deploy/` files committed and pushed.

!!! note
    Newly created CSC computing projects can take some time to become visible
    to Rahti. If project creation fails with an error, wait a few minutes and
    try again.

## Architecture

Four components are deployed and wired together:

1. **`desdeo-api` Deployment**: FastAPI served by gunicorn+uvicorn, listening on
   port 8080. Built in-cluster using OpenShift's Source-to-Image (S2I) strategy
   from a custom Python builder image that includes COIN-OR solvers.

2. **`desdeo-webui` Deployment**: SvelteKit with adapter-node, listening on port
   3000. Built using the Docker strategy from `webui/Dockerfile`. All browser API
   calls are routed through a `/api/[...path]` proxy route baked into the
   SvelteKit app. This keeps cookies same-origin and avoids CORS complications.

3. **`desdeo-postgres` StatefulSet**: PostgreSQL running on the built-in OpenShift
   image, backed by a PersistentVolumeClaim. Alternatively, [CSC Pukki DBaaS](#option-b-pukki-dbaas)
   can be used instead.

4. **OpenShift Routes**: TLS-terminated at Rahti's HAProxy ingress. Certificates
   for `*.rahtiapp.fi` are provisioned automatically.

### URL environment variables

Two env vars control how the API is reached, and they intentionally point to
different targets:

| Variable | Value | Used by |
|---|---|---|
| `VITE_API_URL` | `/api` | Baked into the client-side Javascript bundle at build time. Browser requests go to `<webui-host>/api/...`, which the SvelteKit proxy handles. |
| `API_BASE_URL` | `http://desdeo-api:8080` | Set at runtime on the webui pod. SvelteKit's server-side proxy uses the internal cluster DNS name to reach the API, never exposed to the browser. |

!!! warning
    Do not set `VITE_API_URL` to the API's external Route URL. The proxy
    architecture means the browser never talks directly to the API. Doing so
    causes cross-origin cookie issues that prevent authentication from working.

## Repository preparation

The following files must be present in the repository before deploying. All
manifests live under `deploy/`.

| File | Purpose |
|---|---|
| `deploy/secrets-template.yaml` | Template for creating credentials (never commit real values) |
| `deploy/postgres.yaml` | StatefulSet, Service, and PVC for PostgreSQL |
| `deploy/builder-imagestream.yaml` | ImageStream that tracks the custom S2I builder image |
| `deploy/builder-buildconfig.yaml` | BuildConfig: Docker strategy, builds the solver-enabled S2I builder image |
| `deploy/api-imagestream.yaml` | ImageStream that tracks built API images |
| `deploy/webui-imagestream.yaml` | ImageStream that tracks built webui images |
| `deploy/api-buildconfig.yaml` | BuildConfig: S2I using `desdeo-builder:latest`, GitHub webhook trigger |
| `deploy/webui-buildconfig.yaml` | BuildConfig: Docker strategy, GitHub webhook trigger |
| `deploy/api-deployment.yaml` | Deployment, Service, and Route for the API |
| `deploy/webui-deployment.yaml` | Deployment, Service, and Route for the web UI |
| `deploy/db-init-job.yaml` | One-shot Job that creates tables and seeds the initial user |

In addition, several application-level files are required:

- `.s2i/bin/assemble`: Custom S2I assemble script that uses `uv sync --frozen`
  to install Python dependencies. The default assemble script uses pip, which
  does not understand uv's `--group` flag.

- `.s2i/environment`: Sets S2I environment variables such as `APP_MODULE`,
  `GUNICORN_CMD_ARGS`, and the port.

- `desdeo/api/db_init_prod.py`: Production database initialisation script. The
  `db_init.py` debug branch does nothing in production mode; this separate script
  creates all SQLModel tables and seeds the initial analyst user.

- `webui/Dockerfile`: Multi-stage Node 24 build. The `NPM_RUN=start:production`
  env var selects the adapter-node start script via `svelte.config.js`.

- `webui/src/routes/api/[...path]/+server.ts`: The SvelteKit proxy route. It
  forwards all `/api/*` requests to the API using `event.fetch`, so the
  `handleFetch` hook in `hooks.server.ts` can intercept 401 responses and handle
  token refresh transparently.

- `desdeo-s2i-buildimage.Dockerfile`: Builds the custom S2I builder image that
  extends the Python 3.12 UBI8 base with COIN-OR solvers (`bonmin`, `ipopt`,
  `cbc`).

## Step 1: Prepare secrets

All credentials are stored in a Secret named `desdeo-secrets`.
Two options are available, choose one and skip the other.

Key reference of the stored secrets:

| Key | Description |
|---|---|
| `POSTGRES_USER` / `DB_USER` | PostgreSQL application user name |
| `POSTGRES_PASSWORD` / `DB_PASSWORD` | Password for the above (same value) |
| `DB_HOST` | Kubernetes Service name: `desdeo-postgres` (or Pukki hostname) |
| `DB_PORT` | `5432` |
| `DB_NAME` | Database name |
| `AUTHJWT_SECRET` | JWT signing key, generate fresh, never reuse between deployments|
| `DESDEO_ADMIN_USERNAME` | Initial analyst account username |
| `DESDEO_ADMIN_PASSWORD` | Initial analyst account password |
| `WEBHOOK_SECRET_API` | GitHub webhook secret for the API BuildConfig |
| `WEBHOOK_SECRET_WEBUI` | GitHub webhook secret for the webui BuildConfig |

!!! note
    `DESDEO_PRODUCTION=true` is set directly in the Deployment manifest, not
    as a Secret, because it is not sensitive.

### Options A: From `secrets.yaml`

Copy the template, fill in the values, then apply it:

```bash
cp deploy/secrets-template.yaml deploy/secrets.yaml
# Edit deploy/secrets.yaml, replace every <CHANGE_ME> accordingly
oc apply -f deploy/secrets.yaml
```

!!! warning
    Make __absolutely sure__ that the file `secrets.yaml` is __never__ committed to git!

### Option B: From literals
Create the secret and the two dedicated webhook secrets using `oc create secret
generic`:

```bash
# Main application secret
oc create secret generic desdeo-secrets \
  --from-literal=POSTGRES_USER=desdeo \
  --from-literal=POSTGRES_PASSWORD=<password> \
  --from-literal=DB_HOST=desdeo-postgres \
  --from-literal=DB_PORT=5432 \
  --from-literal=DB_NAME=desdeo \
  --from-literal=DB_USER=desdeo \
  --from-literal=DB_PASSWORD=<password> \
  --from-literal=AUTHJWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(64))") \
  --from-literal=DESDEO_ADMIN_USERNAME=admin \
  --from-literal=DESDEO_ADMIN_PASSWORD=<admin-password> \
  --from-literal=WEBHOOK_SECRET_API=$(python3 -c "import secrets; print(secrets.token_hex(24))") \
  --from-literal=WEBHOOK_SECRET_WEBUI=$(python3 -c "import secrets; print(secrets.token_hex(24))")

# Dedicated webhook secrets. OpenShift's secretReference requires the key
# to be named exactly 'WebHookSecretKey'. Use the same values as above.
oc create secret generic desdeo-webhook-api \
  --from-literal=WebHookSecretKey=<same value as WEBHOOK_SECRET_API>
oc create secret generic desdeo-webhook-webui \
  --from-literal=WebHookSecretKey=<same value as WEBHOOK_SECRET_WEBUI>
```

## Step 2: Deploy PostgreSQL

Two options are available. Choose one and skip the other.

### Option A: In-cluster PostgreSQL (default)

```bash
oc apply -f deploy/postgres.yaml
oc rollout status statefulset/desdeo-postgres
```

The StatefulSet uses the built-in Rahti PostgreSQL image. To check available
tags on your cluster:

```bash
oc get is postgresql -n openshift -o jsonpath='{.spec.tags[*].name}'
```

Data is stored at `/var/lib/pgsql/data` in the PVC.

!!! note
    The env vars that initialize the database are `POSTGRESQL_USER`,
    `POSTGRESQL_PASSWORD`, and `POSTGRESQL_DATABASE` (note the `POSTGRESQL_`
    prefix). The manifests map these from the Secret keys `POSTGRES_USER`,
    `POSTGRES_PASSWORD`, and the hardcoded value `desdeo`.

### Option B: Pukki DBaaS

[Pukki](https://pukki.dbaas.csc.fi) is CSC's managed PostgreSQL service. It
removes the need to deploy `deploy/postgres.yaml` entirely — skip that step if
using Pukki.

**Prerequisites**: add the Pukki service to your CSC computing project via
MyCSC → your project → Services → Pukki → Apply for access.

**Setup:**

1. Log in to [pukki.dbaas.csc.fi](https://pukki.dbaas.csc.fi).
2. Click **Launch Instance**. Give it a name. Default Volume Size, Datastore,
   and Flavor settings are fine for most deployments.
3. Under **Database Access**, add the Rahti egress IP: `86.50.229.150/32`.
4. Under **Initialize Databases**, create a database (e.g. `desdeo`) and set
   an admin username and password. These become `DB_USER`, `DB_PASSWORD`, and
   `DB_NAME` in the Secret.
5. Once the instance is running, copy the hostname from the Pukki dashboard.
   This becomes `DB_HOST` in the Secret instead of `desdeo-postgres`.

Update the secret with the Pukki hostname:

```bash
oc create secret generic desdeo-secrets \
  ... \
  --from-literal=DB_HOST=<pukki-hostname> \
  ...
```

Skip `oc apply -f deploy/postgres.yaml`. All subsequent steps are identical
regardless of which option you chose.

!!! warning
    The Rahti egress IP `86.50.229.150/32` must be added to the Pukki access
    list before deploying. Without it the API pod cannot reach the database and
    will crash on startup.

## Step 3: Create ImageStreams and BuildConfigs

An ImageStream is an OpenShift object that tracks versions of a container image.
When a BuildConfig pushes a new image to an ImageStream, any Deployment watching
that stream automatically triggers a rolling update, no external registry or CI
system required.

Apply the ImageStreams first:

```bash
oc apply -f deploy/builder-imagestream.yaml
oc apply -f deploy/api-imagestream.yaml
oc apply -f deploy/webui-imagestream.yaml
```

Before applying the BuildConfigs, open each file and substitute `<DEPLOY_BRANCH>`
with the branch you want to build from (e.g. `master`). Ensure the git URI uses
HTTPS, not SSH, because build pods do not have SSH credentials.

The API BuildConfig uses the S2I strategy with `desdeo-builder:latest` as its
builder image, the custom image built from `desdeo-s2i-buildimage.Dockerfile`
that includes COIN-OR solvers. The webui BuildConfig uses the Docker strategy
with `webui/Dockerfile`. The build arg `VITE_API_URL=/api` is passed explicitly.
This is intentional, as browser requests go through the SvelteKit proxy rather
than directly to the API.

```bash
oc apply -f deploy/builder-buildconfig.yaml
oc apply -f deploy/api-buildconfig.yaml
oc apply -f deploy/webui-buildconfig.yaml
```

## Step 4: Trigger first builds

The builder image must be ready before the API build can start, as
`api-buildconfig.yaml` references `desdeo-builder:latest` as its S2I base.

```bash
# Build the solver-enabled builder image first (takes a few minutes).
# --follow does not always work, Rahti's web-based interface can also be
# used for monitoring progress.
oc start-build desdeo-builder --follow

# Then build the API and webui (can run in parallel once the builder is done)
oc start-build desdeo-api --follow
oc start-build desdeo-webui --follow
```

The first build takes longer than subsequent ones because there is no layer
cache. Expect roughly a few minutes for the builder, and anther few minutes for
both the API and the webui.

Once the API pod is running, verify the solvers are present:

```bash
oc exec deployment/desdeo-api -- which bonmin ipopt cbc
```

All three should return paths under `/opt/solver_binaries/`.

!!! warning
    If the webui build fails with `exit status 137`, the build pod ran out of
    memory. Increase the build pod memory limit in `webui-buildconfig.yaml`:
    ```yaml
    spec:
      resources:
        limits:
          memory: 4Gi
    ```
    Also ensure `NODE_OPTIONS=--max-old-space-size=3072` is set in
    `dockerStrategy.env`, then re-apply and re-trigger the build.

## Step 5: Deploy API and web UI

```bash
oc apply -f deploy/api-deployment.yaml
oc apply -f deploy/webui-deployment.yaml
oc rollout status deployment/desdeo-api
oc rollout status deployment/desdeo-webui
```

!!! warning
    Rahti enforces a maximum CPU limit-to-request ratio of 5:1. If
    `resources.limits.cpu` divided by `resources.requests.cpu` exceeds this,
    the ReplicaSet will silently fail to create pods. The error does not appear
    in pod logs, look in the ReplicaSet events:
    ```bash
    oc describe replicaset <name>
    ```
    The manifests in `deploy/` are set within the allowed ratio. If you
    customize resource settings, check the ratio before applying.

The following env vars must be present on the API pod at runtime:

| Variable | Source |
|---|---|
| `DESDEO_PRODUCTION` | Set to `true` directly in the Deployment manifest |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | From `desdeo-secrets` |
| `AUTHJWT_SECRET` | From `desdeo-secrets` |
| `CORS_ORIGINS` | Set in the Deployment to `["https://your-webui.rahtiapp.fi"]` |

!!! note
    `COOKIE_DOMAIN` is intentionally not set. With the SvelteKit proxy
    architecture, cookies are owned by the webui host and forwarded
    server-side — the API does not need to set a shared cookie domain.

## Step 6: Initialize the database

`db_init_prod.py` creates all SQLModel tables and seeds the initial analyst
user defined by `DESDEO_ADMIN_USERNAME` and `DESDEO_ADMIN_PASSWORD`. It is
safe to re-run — tables that already exist are not touched.

Before applying, open `deploy/db-init-job.yaml` and replace `<PROJECT>` with
your Rahti project name.

```bash
oc apply -f deploy/db-init-job.yaml
oc logs -f job/desdeo-db-init
```

Expected output:

```
[db-init] Tables ready.
[db-init] Created user 'admin' (role=analyst, group=admin).
[db-init] Done.
```

Once the job completes successfully, delete it:

```bash
oc delete job desdeo-db-init
```

!!! note
    Warnings about missing solvers (`bonmin`, `cbc`, `ipopt`) in the init job
    logs are harmless if the solver builder image has not been used. Once the
    API is rebuilt using `desdeo-builder:latest`, the warnings will disappear.

### Resetting the database

To re-run the init job on an existing database (e.g. after adding new tables
in a release), simply apply the job again. Existing data is not affected.

To wipe the database entirely and start fresh, **all users, problems, and
session data will be permanently deleted**:

```bash
# Drop and recreate the public schema
oc exec -it statefulset/desdeo-postgres -- \
  psql -U desdeo -d desdeo -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Re-run the init job
oc apply -f deploy/db-init-job.yaml
oc logs -f job/desdeo-db-init
oc delete job desdeo-db-init
```

!!! warning
    The schema drop is irreversible. All data will be permanently lost.

## Step 7: Verify

```bash
curl https://your-api.rahtiapp.fi/health
# -> {"status":"ok"}

curl -I https://your-webui.rahtiapp.fi/
# -> HTTP/2 200
# (a 307 redirect to /home is also normal)
```

Routes are TLS-terminated at Rahti's HAProxy ingress. Certificates for
`*.rahtiapp.fi` are provisioned automatically, no manual certificate work is
required.

## Step 8: Set up GitHub webhooks

BuildConfigs include GitHub webhook triggers. Once configured, every push to the
deploy branch triggers a rebuild of the affected component, which then rolls out
automatically via the ImageStream trigger on the Deployment.

Retrieve the webhook secret values from the dedicated webhook secrets:

```bash
oc get secret desdeo-webhook-api -o jsonpath='{.data.WebHookSecretKey}' | base64 -d
oc get secret desdeo-webhook-webui -o jsonpath='{.data.WebHookSecretKey}' | base64 -d
```

Construct the webhook URLs:

```
https://api.2.rahti.csc.fi:6443/apis/build.openshift.io/v1/namespaces/<project>/buildconfigs/desdeo-api/webhooks/<secret>/github
https://api.2.rahti.csc.fi:6443/apis/build.openshift.io/v1/namespaces/<project>/buildconfigs/desdeo-webui/webhooks/<secret>/github
```

In GitHub, go to your repository: **Settings -> Webhooks -> Add webhook**

- Payload URL: the URL constructed above
- Content type: `application/json`: required; `x-www-form-urlencoded` will be rejected
- Secret: leave blank (the secret is embedded in the URL)
- Events: Just the push event

Add one webhook per BuildConfig.

!!! note
    `oc describe bc/desdeo-api` always shows `<secret>` as a placeholder in
    the webhook URL, this is a display-only mask. Always retrieve the actual
    secret value from the Secret object as shown above.

At this point, the desdei web-API and webui should be running on Rahti, and they should automatically
update when new commits are pushed to the deployment branch.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| API pod crashes with `ValidationError: authjwt_secret_key` | `AUTHJWT_SECRET` env var missing or key name wrong | Verify key names in the Secret match the Deployment's `secretKeyRef` fields |
| API pod crashes with DB connection error | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, or `DB_PASSWORD` missing or incorrect | Run `oc describe secret desdeo-secrets` and compare key names |
| API pod crashes with connection timeout to Pukki | Rahti egress IP not whitelisted in Pukki access list | Add `86.50.229.150/32` to the Pukki instance's Database Access settings |
| Webui pod never starts; `FailedCreate` in ReplicaSet events | CPU limit-to-request ratio exceeds 5:1 | Adjust `resources.requests.cpu` so that `limits.cpu / requests.cpu ≤ 5` |
| Login returns 500; logs show `TypeError: Invalid URL` | `API_BASE_URL` env var not set on the webui pod | Set `API_BASE_URL=http://desdeo-api:8080` in the webui Deployment |
| Build fails with `exit status 137` | Build pod out of memory | Set `spec.resources.limits.memory: 4Gi` in the BuildConfig |
| Build fails with `pip install --group` error | Default S2I assemble script used instead of the custom one | Ensure `.s2i/bin/assemble` is present in the repo and uses `uv sync --frozen` |
| `uv sync` fails with lockfile conflict | `uv.lock` is out of sync with `pyproject.toml` | Run `uv lock` locally and commit the updated lockfile |
| Database init job fails with import errors | `DESDEO_PRODUCTION` not set; API falls back to SQLite mode | Ensure `DESDEO_PRODUCTION=true` is set in the Job env |
| GitHub webhook returns 401 | Wrong content type or secret mismatch | Set content type to `application/json`; verify webhook secret matches `WebHookSecretKey` in the dedicated Secret |

## Known limitations

- **Schema migrations**: `db_init_prod.py` uses `SQLModel.metadata.create_all`,
  which creates missing tables but does not ALTER existing ones. If the data
  model changes in a later release, tables must be migrated manually or via,
  e.g., Alembic, before redeploying.

- **WebSocket connections**: The GDM-SCORE-bands and GNIMBUS features use
  `VITE_API_URL` directly for `ws://` connections and are not proxied through
  the SvelteKit `/api` route. These require separate handling not covered in
  this guide.

---

## Web console approach

The steps above use the `oc` CLI and YAML manifests. Rahti also provides a web
console at [console-openshift-console.apps.2.rahti.csc.fi](https://console-openshift-console.apps.2.rahti.csc.fi/)
that lets you accomplish the same tasks through a graphical interface. This
section documents the web console approach as an alternative.

!!! note
    The web console approach is less reproducible than the CLI approach and
    requires more manual steps on each redeployment. It is recommended for
    one-shot deploymnets or first-time exploration, not for ongoing deployments.

### Getting started

Log in to the Rahti web console. Look for the **Create Project** button (you
may need to switch to the Administrator perspective to see it). Fill in the
project name and description. Include your CSC computing project number in the
description in the format `csc_project:#######`.

### Deploying the API

Navigate to **+Add -> Import from Git**. Enter the repository URL and branch
under **Show advanced Git options -> Git reference**.

Under **Build**, add the following environment variables:

```
DESDEO_PRODUCTION = true
DB_HOST            = <database hostname or service name>
DB_PORT            = 5432
DB_NAME            = desdeo
DB_USER            = <db username>
DB_PASSWORD        = <db password>
AUTHJWT_SECRET     = <64-char hex>
CORS_ORIGINS       = ["https://your-webui.rahtiapp.fi"]
```

The builder image should be set to `python:3.12-ubi9`. The S2I assemble script
(`.s2i/bin/assemble`) uses `uv sync --frozen` to install dependencies.

Store sensitive values in an OpenShift Secret and reference them in the Build
configuration rather than entering them as plain text.

### Deploying the web UI

Add another resource via **+Add -> Import from Git** using the same repository
and branch. Under **Advanced Git Options**, set the **Context Dir** to `/webui`.

Select **Docker build** as the build strategy (not S2I). The `webui/Dockerfile`
handles the Node 24 build internally.

Set these build arguments and environment variables:

```
VITE_API_URL  = /api
API_BASE_URL  = http://<api-service-name>:8080
```

!!! warning
    Do not set `VITE_API_URL` to the API's public Route URL. Browser requests
    must go through the SvelteKit `/api` proxy, not directly to the API.

If the build fails with `exit status 137`, increase the build memory limit in
the BuildConfig YAML:

```yaml
spec:
  resources:
    limits:
      memory: 4000Mi
```

### PostgreSQL

Use either Pukki DBaaS or a PostgreSQL image from the Rahti developer catalog.

For Pukki, see [Option B: Pukki DBaaS](#option-b-pukki-dbaas) above,
the setup steps are the same regardless of whether you use the CLI or web console.

For in-cluster PostgreSQL, navigate to **+Add -> Developer Catalog** and find
the PostgreSQL template. The correct env var names for the OpenShift image are
`POSTGRESQL_USER`, `POSTGRESQL_PASSWORD`, and `POSTGRESQL_DATABASE`.

### Database initialization

Once the API is running, use `db_init_prod.py` to create tables and seed the
initial user. The recommended approach is to run it as a Kubernetes Job using
the manifest in `deploy/db-init-job.yaml` (see [Step 6](#step-6-initialize-the-database)).

Alternatively, you can exec into the API pod directly:

```bash
oc exec -it deployment/desdeo-api -- python desdeo/api/db_init_prod.py
```
