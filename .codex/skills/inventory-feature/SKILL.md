---
name: inventory-feature
description: Implement or review a Boliklor inventory feature involving products, movements, stock, cost, lots, or expiration with ledger integrity and transactional safety.
---

# Inventory feature

Read inventory docs, database standard and stock-ledger ADR. Trace product/unit/company, movement snapshots, signs, transition mode and cost calculation. Confirm business decisions for warehouse, lot, expiry, negative stock, costing and adjustment approval; never invent them. Keep confirmed movements auditable and corrections compensating. Validate availability and write movement atomically, considering concurrency. Test decimal units, cross-company input, insufficient stock, rollback, lot/expiry ordering when applicable and authorization.
