# Auditoría técnica y funcional — Fase 0

## Executive Summary

Boliklor es funcional como aplicación interna en desarrollo y tiene una base mejor que un prototipo: persistencia, migraciones, servicios, autenticación robusta básica, CSRF, RBAC, inventario transaccional inicial y estructura de asistencia. No está demostrado como listo para producción. Bloquean esa declaración la autenticación opt-out, ausencia de infraestructura/TLS/backups/restore/CI/observabilidad, asistencia sin marcajes ni GPS, inventario sin lotes/vencimientos/salidas operativas completas y validación no ejecutable en este equipo.

## Repository Baseline

Rama `main`, HEAD `8e8c487bf7b91173d6a1a5825a90e61f2620065f` (`8e8c487`), seguimiento `origin/main` y working tree inicial limpio. La sincronía remota se infiere del estado Git local; no se hizo fetch. No se inspeccionó ni modificó una DB.

## Current Architecture and Stack

Monolito por capas: FastAPI/Uvicorn, Pydantic, SQLAlchemy 2, Psycopg 3, PostgreSQL, Alembic, Jinja2, HTML/CSS/JS, Argon2, OpenPyXL y `unittest`. Rutas web/API llaman servicios que usan ORM. Archivos privados de justificación viven fuera de estáticos.

## Repository Structure

`app/api`, `core`, `database`, `models`, `schemas`, `services`, `web`, `templates`, `static`, `scripts`; `alembic/versions`; `tests`; `docs`; y `frontend/` histórico. No había AGENTS, ADR, CI, contenedores ni manifiestos de despliegue.

## Authentication Assessment

[IMPLEMENTADO] separación usuario/trabajador, Argon2id, temporal obligatoria, sesiones revocables, CSRF y protección router. [IMPLEMENTADO 4A] auth activa por defecto y bypass ADMIN limitado a `APP_ENV=development|test`. [DEUDA_TECNICA] RBAC hardcodeado; sin rate limit/MFA/recuperación/auditoría privilegiada.

## Human Resources Assessment

[IMPLEMENTADO] trabajador con nombres, apellidos, código, empresa, estado y cuenta opcional; CRUD administrativo. [DEUDA_TECNICA] está empaquetado con identidad y carece de ciclo laboral, cargo, área, supervisor, fechas, jornada, contrato e historial. Estos campos son propuestas, no requisitos confirmados.

## Attendance Assessment

[IMPLEMENTADO] lugares, radios/coordenadas opcionales, asignaciones históricas, turnos catálogo, calendario neutro, justificaciones y descarga con ownership. [PENDIENTE] evento de marcaje, GPS del navegador, Haversine/geocerca, atraso/ausencia, planificación, alertas y revisión completa. La ubicación es dato sensible; retención/precisión/base legal están pendientes.

## Inventory Assessment

[IMPLEMENTADO] empresas, unidades, productos, importación, recepciones, ledger de movimientos, snapshots, stock derivado, costo promedio e inicialización/transición legacy. [PENDIENTE] no hay bodega, lote, vencimiento, proveedor, reservas ni auditor; las salidas/ajustes no tienen flujo completo equivalente. El cálculo carga movimientos completos y el promedio incluye entradas históricas sin valorar consumo por lote.

## Database Assessment

Seis migraciones lineales y 16 tablas con FKs, uniques, checks e índices. No se verificó contra una instancia PostgreSQL. Riesgos: timestamps actualizados por ORM, esquema de estados distribuido, falta de auditoría y futura escalabilidad del stock calculado al vuelo. No se encontraron migraciones divergentes evidentes en revisión estática.

## API Assessment

API JSON pequeña (`/api/productos/buscar`, `/api/ordenes`) y mayoría de interfaz server-rendered. Autorización modular en routers. Faltan versionado futuro, paginación, schemas/error uniforme y documentación exhaustiva. `/health` es liveness superficial.

## Frontend Assessment

UI activa coherente en Jinja/static y prototipo duplicado en `frontend/`. Sin evidencias de tests de navegador, accesibilidad sistemática o design system. Validación, loading, errores y empty states requieren estandarización.

## Testing Assessment

La auditoría original identificó diez archivos y 92 métodos `test_`, pero no pudo ejecutarlos por falta de Python disponible en ese momento. [IMPLEMENTADO 4A] La `.venv` actual con Python 3.14.7 ejecuta 99 tests en SQLite aislada: 92 heredados y 7 nuevos de configuración/migraciones. [PENDIENTE] Faltan PostgreSQL desechable, concurrencia, seguridad de cabeceras y E2E.

## Security Assessment

Fortalezas: hashes modernos, tokens opacos hasheados, CSRF, cookies HttpOnly/SameSite, SQLAlchemy y control de ownership de archivos. Debilidades: modo auth inseguro por defecto, sin rate limit/cabeceras proxy/auditoría/gestión de secreto productiva y configuración Secure dependiente del operador. No se realizó explotación.

## Infrastructure, DevOps and Documentation Assessment

No hay evidencia versionada de hosting, HTTPS, proxy, backup, restore, CI/CD, Docker o monitorización. README es detallado pero reporta estado manual. La documentación previa se limita al README y decisiones de asistencia.

## Technical Debt, Risks and Scalability

Code scale: capas compartidas crecerán acopladas. Feature scale: ownership de RRHH difuso. Data scale: stock y búsquedas cargan colecciones. User scale: sesiones escriben `last_seen_at` en cada request. Team scale: faltaban contratos/estándares. Operations scale: sin automatización, readiness ni runbooks. Mantener monolito modular; no se justifican microservicios.

## Findings Matrix

| ID | Área | Hallazgo y evidencia | Severidad | Impacto | Recomendación | Estado |
|---|---|---|---|---|---|---|
| AUD-SEC-001 | Seguridad | [RESUELTO 4A] auth activa por defecto; bypass exige `APP_ENV=development|test` y se valida al componer la app | CRÍTICO original | exposición total evitada por fail-closed | mantener pruebas y configuración productiva explícita | CERRADO 4A |
| AUD-OPS-001 | Operaciones | no existen CI/proxy/TLS/backups/restore/deploy en árbol | ALTO | release y recuperación no demostrables | plataforma mínima y restore probado | RIESGO P1 |
| AUD-ATT-001 | Asistencia | README, `web/attendance.py` y modelos no contienen marcajes | ALTO | MVP de asistencia incompleto | diseñar eventos/GPS tras cerrar reglas | GAP P1 |
| AUD-INV-001 | Inventario | modelos solo movimiento/detalle; no lote/vencimiento/bodega | ALTO | trazabilidad y FEFO imposibles | definir y migrar ledger por lote | GAP P1 |
| AUD-INV-002 | Inventario | `calculate_stock_from_movements` recorre todo el ledger | MEDIO | latencia creciente | agregación SQL/proyección tras medir | DEUDA_TECNICA P2 |
| AUD-AUTH-001 | Identidad | `ROLE_PERMISSIONS` está en `auth_service.py` | MEDIO | cambios dispersos/no auditables | catálogo y matriz RBAC central | DEUDA_TECNICA P2 |
| AUD-DB-001 | DB | no hay prueba automatizada ORM–Alembic/PostgreSQL | ALTO | drift y fallos al desplegar | CI con upgrade desde cero y smoke | RIESGO P1 |
| AUD-OBS-001 | Observabilidad | `/health` solo retorna JSON; logging puntual | ALTO | incidentes invisibles | readiness, logs estructurados y alertas | GAP P1 |
| AUD-TEST-001 | Testing | [RESUELTO 4A] Python 3.14.7, `pip check` y 99 tests OK | MEDIO original | baseline local reproducida | agregar CI y PostgreSQL desechable | CERRADO LOCAL / CI PENDIENTE |
| AUD-HR-001 | RRHH | `Trabajador` está en `models/identity.py` y tiene datos mínimos | MEDIO | ownership y evolución confusos | módulo RRHH incremental | DEUDA_TECNICA P2 |
| AUD-UX-001 | UX | `frontend/` duplica conceptualmente UI activa | BAJO | confusión de mantenimiento | mantenerlo explícitamente histórico o retirar con aprobación | DEUDA_TECNICA P3 |
| AUD-PRIV-001 | Privacidad | coordenadas/justificaciones sensibles sin política documentada | ALTO | sobreexposición/retención indebida | decisiones de acceso, minimización y retención | PENDIENTE P1 |

## Production Readiness

No listo. Ver `docs/plans/active/early-production.md`. Es necesario asegurar configuración, completar flujos MVP, probar PostgreSQL/migraciones, incorporar backups/restore, HTTPS, logging, auditoría mínima y pruebas automatizadas.

## Proposed Target Architecture and Module Boundaries

Monolito modular: Identidad → vínculo opcional con RRHH → Asistencia; Inventario independiente; seguridad/config/logging/auditoría transversales. Un solo despliegue y PostgreSQL. Detalle en `ARCHITECTURE.md` y `module-boundaries.md`.

## Recommended Roadmap

Primero gates de seguridad/entorno y CI; luego identidad/RRHH base; después Asistencia MVP; Inventario MVP con salidas/lotes según necesidad; finalmente producción controlada. El hosting no debe esperar al final: staging debe acompañar los flujos.

## Open Business Questions

Quién puede ver/revisar asistencia; reglas de jornada/atraso/ausencia; precisión y retención GPS; centros y radios autorizados; política de inventario (bodegas, FEFO, costos, ajustes); roles reales; RPO/RTO; propiedad de datos y soporte.
