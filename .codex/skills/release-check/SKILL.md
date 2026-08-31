---
name: release-check
description: Assess Boliklor release readiness using code, migrations, tests, security, configuration, backup, observability, and rollback evidence without deploying.
---

# Release check

Read production plan/checklist, architecture and relevant ADR. Identify commit/artifact/environment without revealing secrets. Verify clean reviewed diff, dependency/build reproducibility, migration path, suite and smoke tests, fail-closed auth, HTTPS/cookies, storage, backup/restore, readiness/logging/alerts and rollback ownership. Classify blockers, required, recommended and later. Never infer readiness from README alone; cite current evidence. Do not deploy, migrate a real DB or approve production when blockers remain.
