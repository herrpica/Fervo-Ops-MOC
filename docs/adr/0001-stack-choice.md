# 0001 — FastAPI + SQLite + build-free React

- **Status:** accepted

## Context
We need a runnable OMOC app that (a) a citizen developer can launch on a Windows PC
for Teams demos with minimal setup, and (b) pushes cleanly to Fervo GitHub Enterprise
and deploys to Azure. The demo machine has Python but **not Node.js**.

## Decision
- **FastAPI** for the API (Pythonic, auto OpenAPI docs, easy Azure hosting).
- **SQLite via SQLAlchemy** for a real relational store with zero local setup.
- **React via vendored UMD + HTM**, served by FastAPI — **no Node/npm build step**.

## Consequences
- Runs with Python alone (`run.ps1`); one process serves API + UI.
- Deploys to Azure App Service / Container Apps as a single Python app.
- Trade-off: the front end is build-free React (HTM template literals), not a
  conventional Vite/JSX project. The dev team may migrate it to Vite/JSX later —
  the REST API contract is unchanged. See ADR 0003.
