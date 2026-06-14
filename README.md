# Fervo OMOC — Operations Management of Change

A staged (TurboTax-style) workflow + dashboard application for Fervo's Operations
Management of Change process. Replaces the Excel-based OMOC form with a shared,
multi-user-ready system: a 7-step gated wizard, a management dashboard (active /
completed MOCs, late action items, late sign-offs), automatic risk scoring and
approval routing, and per-person sign-off tracking.

> **Status:** working prototype, ready to demo locally and to deploy to Azure.
> Built from `Fervo_MOC_Form_v2` and seeded with four real Project Red O&M MOCs.

## What it is

- **Backend:** FastAPI (Python) REST API, SQLite via SQLAlchemy (relational).
- **Front end:** React (loaded build-free via CDN-style vendored files + HTM — **no Node/npm required**), served by FastAPI.
- **Business logic is server-authoritative:** OMOC-required determination,
  Emergency/Temporary flags, Severity × Likelihood risk scoring, approval routing
  (VP Operations vs CEO), PHA level (What-If vs HAZOP), risk level, priority,
  endorser auto-population, and late detection all live in `backend/logic.py`.

## Run it locally (no toolchain beyond Python)

**Windows:**
```powershell
.\run.ps1
```
**macOS / Linux:**
```bash
./run.sh
```
The script creates a virtual environment, installs dependencies, starts the app at
**http://127.0.0.1:8000**, and opens your browser. The SQLite database is created and
seeded automatically on first run.

Manual start (if you prefer):
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # (.venv/bin/python on mac/linux)
.venv/Scripts/python -m uvicorn backend.main:app --reload --port 8000
```

## Run in a browser via GitHub Codespaces (no local install)

For a cloud instance you open in the browser — useful if you don't want to install Python:

1. On the GitHub repo, click **Code ▸ Codespaces ▸ Create codespace on main**.
2. The dev container installs dependencies automatically. In the Codespace terminal, run:
   ```bash
   uvicorn backend.main:app --port 8000
   ```
3. A "port forwarded" notification appears — click **Open in Browser** (port 8000).

Codespaces is a *personal, ephemeral* cloud dev environment (it uses Codespaces quota and
still has the prototype's no-login / single-writer limits). For a **shared, persistent URL**
for the whole team, deploy to Azure — see "Deploying to Azure" below.

## How it works & OSHA PSM alignment

The app has a built-in **How to Use** guide (top-right link in the app) that explains the
7-step workflow, the approval state machine, and how each part supports the Management of
Change element of the OSHA PSM standard, **29 CFR 1910.119(l)**:

| 1910.119(l) requirement | Where the tool supports it |
|---|---|
| (l)(1) Manage changes except "replacement in kind" | Step 1 Checklist screens whether an MOC is required; flags Emergency/Temporary |
| (l)(2)(i) Technical basis for the change | Step 2 Change Request — Description & Justification |
| (l)(2)(ii) Impact on safety and health | Step 3 Risk & Stakeholders — Severity × Likelihood assessment; PHA level (What-If/HAZOP) auto-flagged |
| (l)(2)(iii) Modifications to operating procedures | Step 4 action items + Step 7 closure verification |
| (l)(2)(iv) Necessary time period | Date Requested, action-item due dates, Temporary reversion date |
| (l)(2)(v) Authorization requirements | Step 6 risk-based routing (VP Operations / CEO) + endorsement workflow; authorization enforced before implementation |
| (l)(3) Affected employees informed & trained before start-up | Step 7 closure item "required training completed and documented"; training action items |
| (l)(4) Update process safety information | Step 7 closure item "affected P&IDs, drawings, technical documents updated" |
| (l)(5) Update operating procedures | Step 7 closure item "affected operating procedures updated and approved" |

> **Scope note:** the tool *documents, routes, and tracks* the MOC; it does not itself deliver
> training or update PSI/procedures — those happen in your systems, and the tool records that
> they were addressed. It is decision-support, not a compliance guarantee; confirm against your
> site PSM program. Identity-based authorization and a tamper-evident audit trail arrive with the
> Entra ID / Azure deployment (see `docs/adr/0004`).

## Project layout

```
backend/
  main.py        FastAPI app, REST routes, static serving
  models.py      SQLAlchemy relational model (MOC + 9 child tables)
  logic.py       Server-authoritative rules + serialization
  reference.py   Checklist / risk / closure questions, departments
  seed.py        Four real Project Red MOCs (seeds an empty DB)
  database.py    Engine/session (swap DATABASE_URL for Azure SQL / Postgres)
frontend/
  index.html     Loads React + app.js
  static/app.js  React app (HTM, no build step)
  static/styles.css
  static/vendor/ Vendored React/ReactDOM/HTM (offline-capable)
docs/adr/        Architecture Decision Records
```

## API (under `/api`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/dashboard` | Counts, late action items, late sign-offs, MOC summaries |
| GET | `/api/mocs` | All MOCs (summary) |
| GET | `/api/mocs/{id}` | Full MOC with children + computed fields |
| POST | `/api/mocs` | Create a new blank MOC |
| PUT | `/api/mocs/{id}` | Update a MOC (fields + children) |
| DELETE | `/api/mocs/{id}` | Delete a MOC |
| GET | `/api/reference` | Question text, labels, SLA |

Interactive API docs: **http://127.0.0.1:8000/docs** (FastAPI/Swagger).

## Deploying to Azure (target architecture)

This runs as a single Python web app — deploy to **Azure App Service** or **Azure
Container Apps**, behind **Microsoft Entra ID** authentication, with code in **Fervo
GitHub Enterprise** and CI/CD via **GitHub Actions** (federated credentials, no stored
secrets). For multi-user durability, set the `DATABASE_URL` environment variable to an
**Azure SQL Database** or **PostgreSQL** connection string — no model changes required
(SQLite is for local development only; do not run shared SQLite over a file share).
See `docs/adr/` for the reasoning.

## Owner & help

- **Owner:** Tim Pica — PSM / MOC Coordinator.
- **Source of truth for the form:** `Fervo_MOC_Form_v2.xlsx`.

## Compliance posture

MOC records may contain **BES Cyber System Information (BCSI)** (control-system, ESD,
and network/firewall changes) — a **NERC CIP** review is required before shared/cloud
deployment. The contact directory contains minor **PII** (names/emails) — apply Purview
labels, encryption, and a retention policy. Not in SOX scope (does not feed financial
reporting). An MOC is an OSHA PSM record: the production system needs an immutable audit
trail and identity-backed electronic sign-offs.
