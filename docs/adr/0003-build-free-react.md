# 0003 — Build-free React front end (HTM), FastAPI-served

- **Status:** accepted

## Context
The demo machine has no Node.js, and a citizen developer needs to run the app without
installing a JS toolchain. Conventional React (Vite/CRA) requires Node to build.

## Decision
Write the front end as React using **HTM** (Hyperscript Tagged Markup) with React/ReactDOM
loaded from **vendored** files in `frontend/static/vendor/`. No JSX, no transpile, no
bundler. FastAPI serves `frontend/` as static files.

## Consequences
- Zero front-end build; runs offline (libraries are vendored, not CDN-fetched at runtime).
- Real React (components, hooks, state) — the logic transfers to a conventional project.
- Trade-off: not the standard Vite/JSX structure Fervo devs may expect. Migration path:
  create a Vite app, port `app.js` components to JSX, point it at the same `/api`
  endpoints, and deploy the build output (or keep FastAPI serving it). The API is the
  stable contract.
