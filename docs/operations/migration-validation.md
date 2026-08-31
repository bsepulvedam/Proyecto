# Validación segura de migraciones

## Baseline local

- [IMPLEMENTADO] `tests/test_migration_baseline.py` verifica un único head `20260830_06`, seis revisiones lineales y que las 16 tablas ORM tengan una migración creadora.
- [CONFIRMADO] `python -m alembic heads` y `python -m alembic history` son comprobaciones estáticas y no requieren aplicar cambios.
- [PENDIENTE] Upgrade real desde cero, upgrade desde `20260829_05`, `alembic check` y downgrade deben ejecutarse en PostgreSQL desechable.

## Guardas obligatorias

1. El responsable de infraestructura crea dos bases vacías y descartables, con datos sintéticos y nombres terminados en `_test` o `_ci`.
2. `TEST_DATABASE_URL` nunca puede coincidir con `DATABASE_URL` local/producción.
3. No imprimir URLs, passwords ni secretos. Confirmar host, nombre lógico y owner por un canal seguro antes de ejecutar.
4. No reutilizar una copia con datos personales. No ejecutar estos comandos si falta cualquiera de las confirmaciones.

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
python -m alembic upgrade 20260829_05
python -m alembic upgrade 20260830_06
python -m alembic current
python -m alembic downgrade 20260829_05
python -m alembic upgrade 20260830_06
```

La limpieza de las bases corresponde al owner que las aprovisionó. Nunca automatizar `drop database` desde el repositorio ni sustituir `TEST_DATABASE_URL` por una URL real para completar el checklist.
