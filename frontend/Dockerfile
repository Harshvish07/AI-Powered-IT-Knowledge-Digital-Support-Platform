# Multi-stage: `deps` (installed once, shared), `dev` (used by the root
# docker-compose.yml — hot reload via the bind-mounted source), `builder`
# (production build), `production` (a minimal runtime image using Next.js's
# standalone output — no node_modules, no source, no dev tooling). See
# docs/deployment.md for build/run instructions and an important note about
# NEXT_PUBLIC_API_BASE_URL needing to be set at *build* time, not run time.

FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install


FROM deps AS dev
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]


FROM deps AS builder
WORKDIR /app
# NEXT_PUBLIC_* variables are inlined into the client-side JS bundle at build
# time — setting this only at `docker run` time (as an environment variable)
# would have no effect on already-built client code. Pass it as a build arg:
#   docker build --target production --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.example.com .
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
COPY . .
RUN npm run build


FROM node:20-slim AS production
WORKDIR /app
ENV NODE_ENV=production
# node:20-slim already ships a non-root `node` user (uid 1000) — reused here
# rather than creating a second one, which would collide on the same uid.

COPY --from=builder /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

USER node
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/', r => process.exit(r.statusCode < 500 ? 0 : 1)).on('error', () => process.exit(1))"

CMD ["node", "server.js"]
