# Frontend

## Current state

La UI operativa usa Jinja2 en `app/templates`, CSS/JS en `app/static` y navegación común mediante `base.html`, sidebar y topbar. Hay formularios de identidad, administración, asistencia, inventario, productos y OT. `frontend/` contiene login/dashboard estáticos históricos.

## Gaps

[DEUDA_TECNICA] Conviven prototipo y UI real; no hay sistema de componentes formal, pruebas de accesibilidad o navegador, ni pipeline de assets. Estados loading/empty/error y validación cliente no son uniformes. El control visible depende de roles, mientras la seguridad correcta permanece en backend.

## Target and next steps

[PROPUESTO] consolidar patrones Jinja/macros y tokens CSS, documentar el prototipo, aplicar mejora progresiva, foco/labels/contraste y mensajes consistentes. No introducir SPA sin necesidad demostrada.
