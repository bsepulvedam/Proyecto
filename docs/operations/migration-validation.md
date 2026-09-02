# Validación segura de migraciones

## Baseline local

- [IMPLEMENTADO EN ÁRBOL 4B-2B] `tests/test_migration_baseline.py` verifica un único head `20260901_08`, ocho revisiones lineales, 22 tablas ORM con migración creadora y hashes intactos de las seis revisiones históricas.
- [CONFIRMADO] `python -m alembic heads` y `python -m alembic history` son comprobaciones estáticas y no requieren aplicar cambios.
- [CONFIRMADO GATE 4B-1 2026-08-31] En `boliklor_ot_test` se validaron upgrade real desde cero, downgrade `20260831_07` → `20260830_06`, re-upgrade, 22 tablas de aplicación, constraints, FKs `RESTRICT`, índice parcial, bloqueo, concurrencia y rollback transaccional.
- [CONFIRMADO 2026-08-31] `alembic check` devuelve `No new upgrade operations detected.` La metadata ORM declara explícitamente `ix_detalle_movimientos_movimiento_id` e `ix_detalle_movimientos_producto_id`, iguales a PostgreSQL y a `20260827_03`; la revisión histórica permaneció intacta y no se creó una migración nominal.
- [CONFIRMADO GATE 4B-2B 2026-09-01] En `boliklor_ot_test` se validaron `empty → 20260901_08`, esquema real, paridad ORM, 13 comunas, backfill RADIO no ambiguo, constraints, FKs, índice parcial concurrente, downgrade/re-upgrade y rechazo atómico del downgrade con evaluaciones COMUNA. `alembic check` terminó sin operaciones pendientes y la base desechable quedó en head con solo sus seeds.

## Gate operacional previo a 4B-2B

- [IMPLEMENTADO] El procedimiento reproducible y sus guardas están en [Backup y restore de PostgreSQL](database-backup-restore.md).
- [CONFIRMADO 2026-09-02] Se creó un backup custom (`pg_dump -Fc`) de solo lectura de `boliklor_ot` en revisión `20260831_07`, fuera del repositorio; `pg_dump` y la lectura del catálogo finalizaron con exit code `0`.
- [CONFIRMADO 2026-09-02] El backup se restauró con exit code `0` exclusivamente en `boliklor_ot_restore_test`. Revisión, 23 tablas públicas, conteos por tabla, constraints, 88 índices y 24 secuencias coincidieron; 28 FKs no presentaron filas huérfanas.
- [CONFIRMADO 2026-09-02] La base desechable fue eliminada únicamente después de validar. La base real permaneció en `20260831_07` y la migración `20260901_08` sigue pendiente.

## Gate final real de 4B-2B

- [CONFIRMADO 2026-09-02] El precheck reconfirmó `boliklor_ot` en `localhost:5432`, revisión `20260831_07`, único head `20260901_08`, ausencia de conexiones activas y backup protegido de 105041 bytes con SHA-256 `bdae960d9d7e0e96b2cede78d5df8f627723d2e67112000abc3d0f7b07c0110e`.
- [CONFIRMADO 2026-09-02] `alembic upgrade head` terminó con salida `0`; `current` y `heads` quedaron en `20260901_08 (head)` y `alembic check` informó `No new upgrade operations detected`.
- [CONFIRMADO 2026-09-02] Los 14 IDs históricos de lugares y los conteos/IDs del resto de dominios permanecieron. La base quedó con 15 lugares: 13 COMUNA activas/CUT únicos y Base/Taller sin geocerca; La Pintana aparece una vez, no hay duplicados comunales activos ni zonas RADIO históricas pendientes de reclasificación.
- [CONFIRMADO 2026-09-02] Se validaron siete constraints y tres índices 4B-2B, ocho columnas nuevas/modificadas, 28 FKs y cero huérfanos. Uvicorn inició contra la base real; `/health` y `/login` respondieron 200 y `/admin/lugares` conservó la protección 303 sin sesión. El listado real se renderizó estructuralmente sin mutaciones.
- [CONFIRMADO 2026-09-02] Suite focalizada de Asistencia 75/75, suite completa 168/168, `compileall`, `pip check` y `git diff --check` aprobados. No hubo downgrade, restore automático, fixtures reales, `git add`, commit, push ni deploy.

## Guardas obligatorias para tests de migración

1. El responsable de infraestructura crea dos bases vacías y descartables, con datos sintéticos y nombres terminados en `_test` o `_ci`.
2. `TEST_DATABASE_URL` nunca puede coincidir con `DATABASE_URL` local/producción.
3. No imprimir URLs, passwords ni secretos. Confirmar host, nombre lógico y owner por un canal seguro antes de ejecutar.
4. No reutilizar una copia con datos personales para pruebas destructivas de migración. El restore de un backup real se rige por el procedimiento operacional enlazado, permanece protegido y nunca se usa como fixture. No ejecutar estos comandos si falta cualquiera de las confirmaciones.

Comprobación local previa, sin conectar:

```powershell
if (-not $env:TEST_DATABASE_URL) { throw "TEST_DATABASE_URL no configurada" }
$localDatabaseUrl = $env:DATABASE_URL
if ($localDatabaseUrl -and $env:TEST_DATABASE_URL -eq $localDatabaseUrl) {
    throw "La base de pruebas coincide con DATABASE_URL"
}
$testDatabaseName = ([System.Uri]$env:TEST_DATABASE_URL.Replace('postgresql+psycopg', 'postgresql')).AbsolutePath.TrimStart('/')
if ($testDatabaseName -notmatch '(_test|_ci)$') { throw "La base no cumple la convención desechable" }
```

## Procedimiento autorizado futuro

Usar una base vacía para el upgrade completo:

```powershell
$env:DATABASE_URL = $env:TEST_DATABASE_URL
python -m alembic current
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

Usar una segunda base vacía para comprobar el salto desde la revisión previa:

```powershell
$env:DATABASE_URL = $env:TEST_DATABASE_URL
python -m alembic upgrade 20260830_06
python -m alembic upgrade 20260831_07
python -m alembic current
python -m alembic downgrade 20260830_06
python -m alembic upgrade 20260831_07
```

La limpieza de las bases corresponde al owner que las aprovisionó. Nunca automatizar `drop database` desde el repositorio ni sustituir `TEST_DATABASE_URL` por una URL real para completar el checklist.
