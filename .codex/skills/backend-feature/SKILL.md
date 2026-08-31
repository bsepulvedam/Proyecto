---
name: backend-feature
description: Implement or revise a Boliklor FastAPI backend feature while preserving domain boundaries, transactions, authorization, and existing contracts.
---

# Backend feature

Read root `AGENTS.md`, `ARCHITECTURE.md`, the module docs and relevant ADR. Establish current route/schema/service/model behavior and classify the requested rule. Plan the smallest compatible change. Keep routes thin, validate at the boundary, place rules in the owning module/service, and make one atomic transaction. Preserve backend authorization and CSRF. Add success, validation, authorization and rollback tests. Review ORM/Alembic impact, documentation and full relevant diff. Report validations and any unconfirmed business decision; never deploy or mutate a real DB without explicit authorization.
