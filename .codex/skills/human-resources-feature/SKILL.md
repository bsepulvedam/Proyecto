---
name: human-resources-feature
description: Implement or review a Boliklor human-resources feature while keeping Worker as the labor-data owner and Identity as a separate optional account.
---

# Human Resources feature

Read RRHH docs, worker ownership ADR and privacy/security standards. Confirm which attributes and lifecycle rules are approved; do not convert proposed fields into requirements. Keep worker independent from credentials and expose only the minimum data to Attendance. Model effective dates/history for meaningful labor changes when approved. Define access by capability and scope, not UI visibility. Test worker without account, unique identifiers, activation/termination effects, unauthorized sensitive access and historical integrity.
