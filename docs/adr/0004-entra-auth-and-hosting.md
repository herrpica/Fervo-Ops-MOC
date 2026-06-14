# 0004 — Entra ID authentication and Azure hosting (planned)

- **Status:** proposed

## Context
The prototype has no authentication — it is single-user/local for demos. Production must
authenticate Fervo employees, enforce roles (Initiator, MOC Coordinator, Endorser,
Approver), and keep an auditable record (OSHA PSM; potential BCSI under NERC CIP).

## Decision (target)
- Host on **Azure App Service** (or Container Apps) reachable on Fervo's private network.
- Authenticate with **Microsoft Entra ID** — App Service Easy Auth or MSAL in front of
  the API. No second IdP, no local accounts.
- Enforce **role-based authorization** server-side (not just client-side UI gating).
- Add an **immutable audit trail** and **identity-backed electronic sign-offs**
  (recorded with the signer's Entra identity + timestamp, locked after signing).
- **Self-sign-off only.** Every endorsement/approval is stamped with *who* recorded it
  (`signed_by` / `signed_by_email`) and *when* (`decision_at`). Today the prototype takes
  the signer from the "View as" selector (unverified). With Entra, the server takes the
  signer from the validated token and **rejects (403) any attempt to sign on behalf of
  another person** — you can record only your own endorsement/approval. (Optional future
  allowances: a configured delegate/backup, or coordinator-on-behalf, each audit-logged.)
- Data services (Azure SQL/PostgreSQL, Key Vault) on **Private Endpoints**; secrets via
  **Managed Identity**; CI/CD from **Fervo GitHub Enterprise** via GitHub Actions with
  federated credentials.

## Consequences
- Closes the prototype's single-writer and identity gaps.
- Requires IT/security involvement and a **NERC CIP / BCSI** review before launch.
- Until then, the app stays a local, single-maintainer demo tool.
