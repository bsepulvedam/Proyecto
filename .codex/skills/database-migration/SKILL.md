---
name: database-migration
description: Design and validate a Boliklor SQLAlchemy/Alembic schema change without editing migration history or touching a real database implicitly.
---

# Database migration

Read root and `alembic/AGENTS.md`, database architecture/standard and domain model. Compare ORM, migration head and data invariants. Decide nullability, defaults, FK deletion, constraints, indexes and compatibility with existing rows. Create one new revision; never edit shared revisions. Keep application/schema rollout compatible where practical. Validate upgrade from previous head, fresh upgrade, downgrade when safe and ORM parity on a disposable PostgreSQL database. Do not apply to any real environment without explicit confirmation. Document operational/locking risks and rollback.
