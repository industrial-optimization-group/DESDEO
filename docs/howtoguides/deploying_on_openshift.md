# How to deploy DESDEO on OpenShift

## Overview

This guide walks through deploying the full DESDEO stack: FastAPI backend,
SvelteKit web UI, and PostgreSQL, on an OpenShift/OKD cluster. [CSC
Rahti](https://rahti.csc.fi/) is used as the concrete example throughout; values
specific to Rahti (hostnames, API endpoint, image registry URL) are marked so
readers on other OpenShift clusters can substitute their own.

This guide uses YAML manifests and the `oc` CLI exclusively. Every deployment
step is reproducible and version-controlled. OpenShift is a Kubernetes
distribution with extra features layered on top, this guide uses
OpenShift-specific objects (BuildConfig, ImageStream, Route) that do not exist
in vanilla Kubernetes. If you are deploying on plain Kubernetes, consult your
platform's CI/CD documentation instead.

The files you will work with live in two places in the DESDEO repository:

- `deploy/`: all OpenShift manifests (ImageStreams, BuildConfigs, Deployments,
  StatefulSet, Routes, Job).
- Several application-level files added or modified to support production
  deployment, described under [Repository preparation](#repository-preparation)

## Prerequisites

- A CSC account with an active Rahti project (see [Rahti access](https://docs.csc.fi/cloud/rahti/access/))
- `oc` CLI installed (see [Using the Rahti CLI](https://docs.csc.fi/cloud/rahti/usage/cli/))
- Logged in to the cluster:
  ```bash
  oc login https://api.2.rahti.csc.fi:6443 --token=<token>
  ```
- Switched to your project:
  ```bash
  oc project <your-project>
  ```
- A fork or branch of the [DESDEO
  repository](https://github.com/industrial-optimization-group/DESDEO) with the
  `deploy/` files committed and pushed

## Architecture

Four components are deployed and wired together:

1. `desdeo-api` Deployment: FastAPI served by gunicorn+uvicorn, listening on
    port 8080. Built in-cluster using OpenShift's Source-to-Image (S2I) strategy
    from a Python builder image.

2. `desdeo-webui` Deployment: SvelteKit with adapter-node, listening on port 3000.
    Built using the Docker strategy from `webui/Dockerfile`. All browser API
    calls are routed through a `/api/[...path]` proxy route baked into the
    SvelteKit app, this keeps cookies same-origin and avoids CORS complications.

3. `desdeo-postgres` StatefulSet: PostgreSQL running on the built-in Rahti image,
    backed by a PersistentVolumeClaim.

4. OpenShift Routes: TLS-terminated at Rahti's HAProxy ingress. Certificates for
   `*.rahtiapp.fi` are provisioned automatically.

### URL environment variables

Two env vars control how the API is reached, and they intentionally point to different targets:

| Variable | Value | Used by |
|---|---|---|
| `VITE_API_URL` | `/api` | Baked into the client-side JS bundle at build time. Browser requests go to `<webui-host>/api/...`, which the SvelteKit proxy handles. |
| `API_BASE_URL` | `http://desdeo-api:8080` | Set at runtime on the webui pod. SvelteKit's server-side proxy uses the internal cluster DNS name to reach the API, never exposed to the browser. |

Do not set `VITE_API_URL` to the API's external Route URL. The proxy architecture means the browser never talks directly to the API.

## Repository preparation

The following files must be present in the repository before deploying. All manifests live under `deploy/`.
These ar provided in the master branch.

| File | Purpose |
|---|---|
| `deploy/postgres.yaml` | StatefulSet, Service, and PVC for PostgreSQL |
| `deploy/builder-imagestream.yaml` | ImageStream that tracks the custom S2I builder image |
| `deploy/builder-buildconfig.yaml` | BuildConfig — Docker strategy, builds the solver-enabled S2I builder image |
| `deploy/api-imagestream.yaml` | ImageStream that tracks built API images |
| `deploy/webui-imagestream.yaml` | ImageStream that tracks built webui images |
| `deploy/api-buildconfig.yaml` | BuildConfig: S2I using `desdeo-builder:latest`, GitHub webhook trigger |
| `deploy/webui-buildconfig.yaml` | BuildConfig: Docker strategy, GitHub webhook trigger |
| `deploy/api-deployment.yaml` | Deployment, Service, and Route for the API |
| `deploy/webui-deployment.yaml` | Deployment, Service, and Route for the web UI |
| `deploy/db-init-job.yaml` | One-shot Job that creates tables and seeds the initial user |

In addition, several non-manifest files are required:

- `.s2i/bin/assemble`: Custom S2I assemble script that uses `uv sync --frozen`.

- `.s2i/environment`: Sets S2I environment variables such as `APP_MODULE`, `GUNICORN_CMD_ARGS`, and the port.

- `desdeo/api/db_init_prod.py`: Production database initialization script. The
  `db_init.py` debug branch is a no-no in production mode; this separate script
  creates all SQLModel tables and seeds the initial analyst user.

- `webui/Dockerfile`: Multi-stage Node 24 build. The `NPM_RUN=start:production`
  build arg selects the adapter-node start script.

- `webui/src/routes/api/[...path]/+server.ts`: The SvelteKit proxy route. It
  forwards all `/api/*` requests to the API using `event.fetch`, so the
  `handleFetch` hook in `hooks.server.ts` can intercept 401 responses and handle
  token refresh transparently.

- `desdeo-s2i-buildimage.Dockerfile`: Builds the custom S2I builder image that
  extends the Python 3.12 UBI8 base with COIN-OR solvers (`bonmin`, `ipopt`, `cbc`).

## Step 1: Prepare secrets

All credentials are stored in a single Secret named `desdeo-secrets` (NOT under
version control). Create it with `oc create secret generic` rather than from a
YAML file. This avoids ever writing credentials to disk or committing them to
the repository.

```bash
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
```

Key reference:

| Key | Description |
|---|---|
| `POSTGRES_USER` / `DB_USER` | PostgreSQL application user name |
| `POSTGRES_PASSWORD` / `DB_PASSWORD` | Password for the above |
| `DB_HOST` | Kubernetes Service name, always `desdeo-postgres` |
| `DB_PORT` | `5432` |
| `DB_NAME` | Database name |
| `AUTHJWT_SECRET` | JWT signing key, generate a fresh value, never reuse |
| `DESDEO_ADMIN_USERNAME` | Initial analyst account username |
| `DESDEO_ADMIN_PASSWORD` | Initial analyst account password |
| `WEBHOOK_SECRET_API` | GitHub webhook secret for the API BuildConfig |
| `WEBHOOK_SECRET_WEBUI` | GitHub webhook secret for the webui BuildConfig |

!!! note
    `DESDEO_PRODUCTION=true` is set directly in the Deployment manifest, not in
    this Secret, because it is not sensitive.

## Step 2: Deploy PostgreSQL

```bash
oc apply -f deploy/postgres.yaml
oc rollout status statefulset/desdeo-postgres
```

The StatefulSet uses the built-in Rahti PostgreSQL image:

```
image-registry.openshift-image-registry.svc:5000/openshift/postgresql:16-el10
```

To check which tags are available on your cluster:

```bash
oc get is postgresql -n openshift -o jsonpath='{.spec.tags[*].name}'
```

Data is stored at `/var/lib/pgsql/data` in the PVC.

!!! note
    The env vars that initialize the database are `POSTGRESQL_USER`,
    `POSTGRESQL_PASSWORD`, and `POSTGRESQL_DATABASE` (the `POSTGRESQL_` prefix,
    not `POSTGRES_`). The manifests map these from the Secret keys `DB_USER`,
    `DB_PASSWORD`, and `DB_NAME`.

!!! note
    An alternative to in-cluster PostgreSQL is [CSC Pukki
    DBaaS](https://docs.csc.fi/cloud/dbaas/), a managed PostgreSQL service.
    Pukki removes the operational overhead of managing the database yourself but
    adds setup steps not covered in this guide.

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

Before applying the BuildConfigs, open each file and substitute the placeholder
`<DEPLOY_BRANCH>` with the branch you want to build from (e.g. `master`). Ensure
the git URI uses HTTPS, not SSH, the build pod does not have SSH credentials.

The API BuildConfig uses the S2I strategy with `desdeo-builder:latest` as its
builder image — the custom image built from `desdeo-s2i-buildimage.Dockerfile`
that includes COIN-OR solvers. The webui BuildConfig uses the Docker strategy
with `webui/Dockerfile`. The build arg `VITE_API_URL=/api` is passed explicitly,
this is intentional, as browser requests go through the SvelteKit proxy rather
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
# Build the solver-enabled builder image first
oc start-build desdeo-builder --follow

# Then build the API and webui (can run in parallel once the builder is done)
oc start-build desdeo-api --follow
oc start-build desdeo-webui --follow
```

The first build takes longer than subsequent ones because there is no layer
cache. Expect roughly 6 minutes for the builder, 4 minutes for the API, and
5 minutes for the webui.

Once the API pod is running, verify the solvers are present:

```bash
oc exec deployment/desdeo-api -- which bonmin ipopt cbc
```

All three should return paths under `/opt/solver_binaries/`.

!!! warning
    If the webui build fails with `exit status 137`, the build pod ran out of memory. Increase the build pod memory limit in `webui-buildconfig.yaml`:
    ```yaml
    spec:
      resources:
        limits:
          memory: 4Gi
    ```
    Also add `NODE_OPTIONS=--max-old-space-size=3072` to `dockerStrategy.env` in the same file, then re-apply and re-trigger the build.
---

## Step 5: Deploy API and web UI

```bash
oc apply -f deploy/api-deployment.yaml
oc apply -f deploy/webui-deployment.yaml
oc rollout status deployment/desdeo-api
oc rollout status deployment/desdeo-webui
```

!!! warning
    Rahti enforces a maximum CPU limit-to-request ratio of 5:1. If your
    `resources.limits.cpu` divided by `resources.requests.cpu` exceeds this, the
    ReplicaSet will silently fail to create pods. The error does not appear
    in pod logs, look in the ReplicaSet events:
    ```bash
    oc describe replicaset <name>
    ```
    The manifests in `deploy/` are set within the allowed ratio. If you
    customize resource settings, check the ratio before applying.

The following env vars must be present on the API pod at runtime (sourced from `desdeo-secrets` via `secretKeyRef` in the Deployment):

| Variable | Source |
|---|---|
| `DESDEO_PRODUCTION` | Set to `true` directly in the Deployment manifest |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | From `desdeo-secrets` |
| `AUTHJWT_SECRET` | From `desdeo-secrets` |
| `CORS_ORIGINS` | Set in the Deployment to `["https://your-webui.rahtiapp.fi"]` |

!!! note
    With the SvelteKit proxy architecture, `COOKIE_DOMAIN` on the API is
    irrelevant. Cookies are owned by the webui host and forwarded server-side.
    Leave `COOKIE_DOMAIN` unset.

## Step 6: Initialize the database

`db_init_prod.py` creates all SQLModel tables and seeds the initial analyst user
defined by `DESDEO_ADMIN_USERNAME` and `DESDEO_ADMIN_PASSWORD`. Safe to re-run if needed.

The script runs as a one-shot Kubernetes Job using the API image. Before
applying, open `deploy/db-init-job.yaml` and replace `<PROJECT>` with your Rahti
project name (used to construct the image pull reference).

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


## Step 7: Verify

```bash
curl https://your-api.rahtiapp.fi/health
# → {"status":"ok"}

curl -I https://your-webui.rahtiapp.fi/
# → HTTP/2 200
# (a 307 redirect to /home is also normal)
```

Routes are TLS-terminated at Rahti's HAProxy ingress. Certificates for
`*.rahtiapp.fi` are provisioned automatically, no manual certificate work is
required.

## Step 8: Set up GitHub webhooks

BuildConfigs include GitHub webhook triggers. Once configured, every push to the
deploy branch triggers a rebuild of the affected component, which then rolls out
automatically via the ImageStream trigger on the Deployment.

Retrieve the webhook URLs. The webhook secret is embedded in the URL itself,
the GitHub "Secret" field should be left blank:

```bash
oc get bc/desdeo-api -o jsonpath='{.spec.triggers}' | python3 -m json.tool
```

Find the `github` trigger entry and copy the `secret` value. Then construct the
full webhook URL:

```
https://api.2.rahti.csc.fi:6443/apis/build.openshift.io/v1/namespaces/<project>/buildconfigs/desdeo-api/webhooks/<secret>/github
```

In GitHub, go to your fork: **Settings → Webhooks → Add webhook**

- Payload URL: the URL constructed above
- Content type: `application/json`, this is required; the default `x-www-form-urlencoded` will be rejected by OpenShift
- Secret: leave blank
- Events: Just the push event

Repeat for `desdeo-webui` using `bc/desdeo-webui`.

!!! note
    `oc describe bc/desdeo-api` always shows `<secret>` as a placeholder in the
    webhook URL regardless of how the secret is stored, this is a display-only
    mask. Always use `oc get bc -o jsonpath` as shown above to retrieve the
    actual secret value.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| API pod crashes on startup with `ValidationError: authjwt_secret_key` | `AUTHJWT_SECRET` env var missing or key name wrong | Verify the key name in the Secret matches exactly what the Deployment references |
| API pod crashes with DB connection error | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, or `DB_PASSWORD` missing or incorrect | Run `oc describe secret desdeo-secrets` and compare key names with the Deployment's `secretKeyRef` fields |
| Webui pod never starts; `FailedCreate` in ReplicaSet events | CPU limit-to-request ratio exceeds 5:1 | Adjust `resources.requests.cpu` so that `limits.cpu / requests.cpu ≤ 5` |
| Login returns 500; logs show `TypeError: Invalid URL` | `API_BASE_URL` env var not set on the webui pod | Set `API_BASE_URL=http://desdeo-api:8080` in the webui Deployment |
| Build fails with `exit status 137` | Build pod out of memory | Set `spec.resources.limits.memory: 4Gi` in the BuildConfig and add `NODE_OPTIONS=--max-old-space-size=3072` to `dockerStrategy.env` |
| Build fails with `pip install --group` error | Default S2I assemble script used instead of the custom one | Ensure `.s2i/bin/assemble` is present in the repo and uses `uv sync --frozen` |
| `uv sync` fails with lockfile conflict | `uv.lock` is out of sync with `pyproject.toml` | Run `uv lock` locally and commit the updated lockfile |
| Database init job fails with import errors | `DESDEO_PRODUCTION` not set, API falls back to SQLite debug mode | Ensure `DESDEO_PRODUCTION=true` is set in the Job's env spec |
| GitHub webhook returns 401 | Content type set to `application/x-www-form-urlencoded` | Change content type to `application/json` in the GitHub webhook settings |


## Known limitations

Schema migrations:`db_init_prod.py` uses `SQLModel.metadata.create_all`,
which creates missing tables but does not ALTER existing ones. If the data
model changes in a later release, tables must be migrated manually or via, e.g.,
Alembic before redeploying.
