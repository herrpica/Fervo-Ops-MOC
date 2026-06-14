# Deployment Q&A — for the Azure deployment discussion

Answers to IT's scoping questions for deploying the OMOC app to Azure. Items marked
**[confirm]** are business/IT decisions to finalize; the rest follow from how the app is built.

## 1. Who accesses it, and on what devices?
**Fervo employees only — internal tool.** Users are initiators, MOC coordinators, endorsers,
and approvers. No external/public access is required.

- Recommended posture: **Microsoft Entra ID** sign-in, **internal/private** network access, and
  **Conditional Access** limiting use to **Fervo-managed devices**.
- **[confirm]** Edge case: the Historian MOC lists a **PowerCo** approver (Quinn Woodard). If
  PowerCo / Ormat or any outside party ever needs to endorse or approve, that is an Entra **B2B
  guest** invitation — not a public login, and not required for the initial rollout.

## 2. What database?
A **relational SQL database via SQLAlchemy.**

- **Local/dev:** SQLite (demo only).
- **Azure:** **Azure SQL Database** (or Azure Database for PostgreSQL), selected by setting the
  `DATABASE_URL` environment variable — **no code or schema changes**. See `docs/adr/0002`.
- Recommended: **Azure SQL Database** (PaaS; Entra auth; Private Endpoint; point-in-time restore).

## 3. Integrated systems?
**None today** — the app is self-contained (its own database, no external API calls).
Integrations needed/likely at deployment:

- **Entra ID** — authentication (required).
- **Microsoft Graph / Exchange Online**, or **Power Automate** — sign-off reminder emails.
- **SharePoint / OneDrive** *(optional)* — attachment storage (attachments are currently links).
- **Power BI** *(optional)* — cross-MOC reporting.

No transactional integration with other business systems is planned.

## 4. Uptime SLA?
**[confirm with the business.]** This is an internal workflow/records tool — **not a real-time
operational or control system** — so an outage delays MOC processing but does not affect plant
operations.

- Recommended target: **~99.5%, business-hours support, single region**; add redundancy later if
  usage grows.
- **Data durability and retention matter more than uptime here** (see #5), because it is a
  compliance record.

## 5. Data backup?
An MOC is an **OSHA PSM record (29 CFR 1910.119(l))** — durability and retention are the priority.

- **Azure SQL automated backups** with **point-in-time restore**, plus **long-term retention (LTR)**.
- **Geo-redundant** backup storage.
- Attachments backed up per their store (Azure Blob / SharePoint).
- **[confirm]** Required **retention period** for MOC records, per Fervo's PSM / records-retention
  policy — this drives the LTR configuration.

## Flags to raise with IT / compliance
- **NERC CIP / BCSI review.** MOC content includes control-system, ESD, and firewall/network
  changes, which may be **BES Cyber System Information**. Review before hosting.
- **Architecture reference.** `README.md` and `docs/adr/` describe the target architecture (Entra
  auth, Azure SQL, private networking, Key Vault, GitHub Actions CI/CD with federated credentials).
- **Auth & audit are the next build items** — the prototype records authorizations but does not yet
  enforce them by verified identity or keep a tamper-evident audit trail; both arrive with the Entra
  ID / Azure deployment (`docs/adr/0004`).
