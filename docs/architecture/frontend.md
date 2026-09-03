# Frontend

## Current state

La UI operativa usa Jinja2 en `app/templates`, CSS/JS en `app/static` y navegación común mediante `base.html`, sidebar y topbar. Hay formularios de identidad, administración, asistencia, inventario, productos y OT. [IMPLEMENTADO 4B-2] el marcaje personal solicita GPS con JavaScript solo después de una acción explícita y deja reglas, ownership y geocerca en backend. [IMPLEMENTADO 4B-2A] el calendario personal presenta fecha trabajada, revisión, fuera de rango o neutral y permite desplegar turno/horas/duración/incidencias sin mostrar GPS exacto. `frontend/` contiene login/dashboard estáticos históricos.

## Gaps

[DEUDA_TECNICA] Conviven prototipo y UI real; no hay sistema de componentes formal, pruebas de accesibilidad o navegador, ni pipeline de assets. Estados loading/empty/error y validación cliente no son uniformes. El control visible depende de roles, mientras la seguridad correcta permanece en backend.

## Target and next steps

[PROPUESTO] consolidar patrones Jinja/macros y tokens CSS, documentar el prototipo, aplicar mejora progresiva, foco/labels/contraste y mensajes consistentes. No introducir SPA sin necesidad demostrada.

[IMPLEMENTADO EN ÁRBOL 4B-3D] La UI Jinja añade descargas XLSX en Supervisión y administración de tarifas en la navegación ADMIN. Las nuevas versiones exigen una confirmación explícita en el formulario; JEFATURA no recibe controles de tarifas y las rutas mantienen autorización backend.
