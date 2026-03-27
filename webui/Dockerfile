# Multi-stage Dockerfile for the DESDEO web UI.
# Build context: webui/   (set via BuildConfig contextDir: webui)
#
# Two URL variables control how the frontend talks to the backend API:
#
#   VITE_API_URL  (build-time ARG / ENV)
#       Baked into the client-side JavaScript bundle by Vite.
#       Used by browser code: import.meta.env.VITE_API_URL
#       Must be the *public* HTTPS route of the API.
#       Default: https://gialmisi-desdeo-api.rahtiapp.fi
#
#   API_URL  (runtime ENV in the container / Deployment env)
#       Used by SvelteKit server-side route handlers (+server.ts) that
#       proxy requests to the backend.
#       Should point to the *internal cluster* service so traffic stays
#       inside the cluster and avoids the public ingress.
#       Default here: http://desdeo-api:8080
#       Override in the Deployment manifest if the service name differs.

# ---------------------------------------------------------------------------
# Stage 1 – build
# ---------------------------------------------------------------------------
FROM node:24-alpine AS build

WORKDIR /app

# Install dependencies first for layer-cache efficiency.
COPY package*.json ./
RUN npm ci

# Copy the rest of the source.
COPY . .

# VITE_API_URL is baked into the bundle at build time.
ARG VITE_API_URL=https://gialmisi-desdeo-api.rahtiapp.fi
ENV VITE_API_URL=$VITE_API_URL

# NPM_RUN=start:production makes svelte.config.js select adapter-node.
RUN NPM_RUN=start:production npm run build

# Prune devDependencies so we can copy node_modules into the runtime stage.
RUN npm prune --omit=dev

# ---------------------------------------------------------------------------
# Stage 2 – runtime
# ---------------------------------------------------------------------------
FROM node:24-alpine

WORKDIR /app

# Copy the compiled adapter-node output and the pruned dependencies.
COPY --from=build /app/build           ./build
COPY --from=build /app/node_modules    ./node_modules
COPY --from=build /app/package.json    ./package.json

# OpenShift runs containers with an arbitrary UID in GID 0 (root group).
# Setting group ownership to 0 with group-write allows the process to run
# under any UID without permission errors.
RUN chgrp -R 0 /app && chmod -R g=u /app

# adapter-node default port; can be overridden at runtime via PORT env.
EXPOSE 3000
ENV PORT=3000

# Server-side proxy routes use this to reach the backend inside the cluster.
ENV API_URL=http://desdeo-api:8080

# Run as a non-root UID (required by Rahti / OpenShift SCC).
USER 1001

CMD ["node", "build"]
