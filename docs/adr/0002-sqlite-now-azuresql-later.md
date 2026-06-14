# 0002 — SQLite for local dev, Azure SQL / PostgreSQL in production

- **Status:** accepted

## Context
SQLite is ideal for a zero-setup local demo, but it is a single-file database whose
locking does not work over network/cloud file shares (OneDrive/SharePoint sync will
corrupt it), and it is not the right multi-user production store for Fervo.

## Decision
Use SQLite locally. The engine reads `DATABASE_URL` (env var); production sets it to an
**Azure SQL Database** or **Azure Database for PostgreSQL** connection string. The
SQLAlchemy model is database-agnostic, so no model changes are required to switch.

## Consequences
- Local demos need no database server.
- Production gets real concurrent multi-user writes, locking, and backups.
- **Never** point a shared deployment at a SQLite file on a file share.
- Connection strings come from Key Vault via Managed Identity, never committed.
