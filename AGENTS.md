# AGENTS.md — Fervo OMOC

Operational guide for AI coding agents working in this repository. (Humans: see `README.md`.)

## Project overview

A FastAPI + SQLite (SQLAlchemy) + build-free React application implementing Fervo's
Operations Management of Change workflow: a 7-step gated wizard and a management
dashboard. FastAPI serves both the REST API (`/api/*`) and the static React front end.
Business rules are server-authoritative in `backend/logic.py`.

## Tech stack

- Python 3.11+ (developed on 3.14), FastAPI, SQLAlchemy 2.x, Uvicorn.
- React 18 + HTM, loaded from vendored files in `frontend/static/vendor/` — **no Node, no build step.**
- SQLite locally; Azure SQL / PostgreSQL in production via the `DATABASE_URL` env var.

## Commands

- Run locally: `./run.ps1` (Windows) or `./run.sh` (mac/linux). App on `http://127.0.0.1:8000`.
- Manual: `.venv/Scripts/python -m uvicorn backend.main:app --reload --port 8000`.
- API docs: `/docs`. Reset local data: delete `backend/omoc.db` (re-seeds on next start).
- No test suite yet; add `pytest` under `tests/` if you introduce one.

## Code conventions

- Keep all MOC business rules (risk scoring, approval/PHA routing, late detection,
  step completion) in `backend/logic.py` — the API and front end must not re-derive
  them authoritatively. The front end mirrors them only for live UI feedback.
- Relational model in `backend/models.py`: one `MOC` with cascading child tables.
  Add new fields as columns or child tables, not JSON blobs.
- Front end is plain React via HTM tagged templates (`html\`...\``). No JSX/transpile.
- Reference data (questions, departments) lives in `backend/reference.py`.

## Architectural constraints (do not violate)

- **Authentication is Microsoft Entra ID.** Do not add a second identity provider or
  local password accounts. (Auth is not yet wired in the prototype; it goes in front
  of the app at deploy time — App Service Easy Auth / MSAL.)
- **Secrets come from Azure Key Vault via Managed Identity** — never commit secrets;
  never hard-code connection strings (use `DATABASE_URL`).
- **Data services use Private Endpoints** in production; do not enable public network access.
- **Host on Azure** (App Service / Container Apps). Do **not** introduce Vercel, Netlify,
  Render, Heroku, Supabase, Firebase, Auth0, or similar — see the avoid list in Fervo's
  app architecture standard.
- **Do not run shared SQLite over a file share / OneDrive** — single-writer corruption.
  SQLite is local-dev only; production uses Azure SQL / PostgreSQL.

## Boundaries

- Do not modify `docs/adr/` without explicit human approval.
- Do not commit `backend/omoc.db`, `.venv/`, or any secret.

## More

Read `docs/adr/` for the reasoning behind the stack, storage, and front-end choices.
