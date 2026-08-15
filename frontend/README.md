# WhyNotGrace — Frontend

Vite + React 19 + TypeScript SPA for the WhyNotGrace restaurant/hotel POS
backend. Talks to the FastAPI backend (`../backend`) over its `/api/v1`
REST API; API types in `src/types/api.ts` are generated from the
backend's live OpenAPI schema, never hand-written.

## Requirements

- Node.js 20+
- A running instance of the backend (`../backend` — see its README)

## Local development

```bash
cp .env.example .env
# point VITE_API_URL at your running backend, e.g. http://localhost:8000
npm install
npm run dev
```

Opens at `http://localhost:5173`.

## Build / lint

```bash
npm run build   # tsc -b && vite build -> dist/
npm run lint    # oxlint
```

## Regenerating API types

After any backend schema change, regenerate `src/types/api.ts` against a
**live** running backend (never hand-edit this file):

```bash
npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts
```

Then update `src/types/models.ts` if any new field needs one of the
documented default-value/optionality overrides (see comments at the top
of that file for the two recurring openapi-typescript quirks it works
around).

## Docker

```bash
docker build --build-arg VITE_API_URL=http://localhost:8000 -t whynotgrace-frontend .
docker run -p 3000:8080 whynotgrace-frontend
```

(nginx inside the container listens on 8080, not 80 — it runs as a
non-root user, which can't bind a port under 1024.)

Or via the backend's `docker-compose.yml` (`docker compose up --build`
from `../backend`), which builds and runs this alongside PostgreSQL and
the API. `VITE_API_URL` is baked into the JS bundle at **build** time
(Vite convention — it is not read from the container's environment at
runtime), so it must be supplied as a build arg, not a runtime env var.

**Not required**: the frontend has no server-side component of its own —
the Docker image just serves the static build via nginx. Any static host
(Vercel, Netlify, S3+CloudFront, GitHub Pages) works equally well.

## Architecture

```
src/
  api/          Axios client + one wrapper module per backend resource
  features/     One directory per product area (menu, orders, pos, qr, ...)
  components/   Shared UI primitives (Button, Dialog, Input, ...)
  routes/       ProtectedRoute / RoleRoute / FeatureRoute route guards
  stores/       Zustand stores (auth, cart) — access token kept in memory
                only; refresh token persisted to localStorage
  types/        api.ts (generated) + models.ts (ergonomic aliases/overrides)
  i18n/         en/hi/mr locale JSON, react-i18next config
```

Route guards mirror the backend's RBAC and feature-flag enforcement
exactly (`src/config/navigation.ts` + `src/routes/*.tsx`), but the
backend is always the actual enforcement point — hiding a nav item or
route client-side is a UX nicety, never the security boundary.
