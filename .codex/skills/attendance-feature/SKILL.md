---
name: attendance-feature
description: Implement or review a Boliklor attendance feature with worker ownership, event traceability, geolocation privacy, and explicit business-rule decisions.
---

# Attendance feature

Read attendance docs, geolocation ADR and security standard. Use RRHH worker identity; do not duplicate the worker. Confirm event, schedule, tolerance, location/radius, precision, exception, approval and retention rules before encoding them. Separate captured evidence from derived status and retain rule/version needed for audit. Capture location only when required, minimize exposure and never log exact coordinates. Enforce ownership/role backend. Test permission denial, missing/inaccurate GPS, boundary distance, timezone/day transitions, duplicate/reordered events and rollback.
