---
name: testing
description: Add or assess Boliklor tests across business rules, web/API, database, authorization, and security using isolated deterministic environments.
---

# Testing

Read root and `tests/AGENTS.md`, testing standard and module rules. Map risk to the smallest useful layer. Cover positive and negative paths, ownership/roles/CSRF and transaction rollback where applicable. Use disposable DB/storage, restore environment variables, control time and avoid network/real data. Prefer behavioral assertions over implementation details. Run compile and targeted tests, then suite when feasible; report exact commands, counts/failures and environment blockers without claiming unexecuted success.
