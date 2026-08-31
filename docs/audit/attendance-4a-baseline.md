# Baseline técnico de Asistencia 4A

Fecha: 2026-08-31. Commit base: `c50d3c3`. Alcance: baseline ejecutable, testeable y seguro previo a Asistencia 4B.

## Estado inicial confirmado

- [CONFIRMADO] `main`, working tree limpio y seis migraciones lineales con head `20260830_06`.
- [CONFIRMADO] Python 3.14.7, `.venv` local y `pip check` correcto.
- [DEUDA_TECNICA] 92 tests descubiertos: 91 OK y un error en `WebIntegrationTests.test_dashboard` por uso de la dependencia DB global sin esquema aislado.
- [DEUDA_TECNICA] auth se podía deshabilitar por default sin distinguir entorno.
- [PENDIENTE] No había PostgreSQL desechable autorizada; la base local con datos reales no se utilizó.

## Resultado 4A

- [IMPLEMENTADO] `test_web.py` crea SQLite en memoria, override de `get_db` y restaura estado.
- [IMPLEMENTADO] La suite usa `APP_ENV=test`, auth deshabilitada explícitamente y `DATABASE_URL` SQLite para no contactar PostgreSQL local.
- [IMPLEMENTADO] Auth está activa por defecto; el bypass exige `APP_ENV=development|test`; staging/producción, entorno inválido, booleano inválido o secret ausente fallan al componer la aplicación.
- [IMPLEMENTADO] Tests estáticos verifican un head, seis revisiones lineales y correspondencia de 16 tablas ORM con migraciones creadoras.
- [IMPLEMENTADO] 99 tests ejecutados: 99 OK; compilación y `pip check` correctos.
- [CONFIRMADO] Se consolidaron las decisiones de sesiones, `ENTRADA`/`SALIDA`, timezone, GPS por evento, rango, incidencias, permisos, estados y exportación futura.
- [PENDIENTE] Upgrade desde cero/anterior y downgrade sobre PostgreSQL desechable según `docs/operations/migration-validation.md`.

## Límites respetados

No se añadieron tablas, migraciones, marcajes, GPS, geocercas, incidencias funcionales, calendarios, exportaciones ni remuneraciones. No hubo conexión destructiva a PostgreSQL real, commit, push o despliegue.
