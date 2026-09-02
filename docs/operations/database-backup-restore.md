# Backup y restore de PostgreSQL

## Estado y alcance

[IMPLEMENTADO] Este procedimiento manual protege la base PostgreSQL de Boliklor antes de una migración y comprueba que el artefacto puede restaurarse. Usa el formato custom de PostgreSQL (`pg_dump -Fc`), conserva el backup fuera del repositorio y ensaya el restore exclusivamente en una base desechable.

[PENDIENTE] La automatización, almacenamiento externo, cifrado administrado, monitoreo, retención definitiva, RPO/RTO y owner operacional permanente requieren una decisión de infraestructura. Un ensayo local correcto no sustituye una política de backups productivos ni ofrece recuperación a un punto en el tiempo.

## Responsabilidades

- El operador del gate confirma origen, destino, versión, espacio disponible y resultado de cada comando.
- El responsable de infraestructura custodia credenciales y backups, limita sus permisos y autoriza su eliminación según la política vigente.
- [PENDIENTE_DE_DEFINICION] Asignar owner nominal, frecuencia automática, RPO, RTO, retención y ubicación externa.
- Nadie restaura sobre `boliklor_ot` como prueba ni ejecuta una migración si el backup o su restore no están validados.

## Requisitos y tratamiento de secretos

1. Usar herramientas cliente PostgreSQL de versión igual o posterior al servidor y registrar ambas versiones.
2. Obtener host, puerto, usuario y nombre de base desde la configuración aprobada. Mostrar solamente host, puerto y nombre de base.
3. No escribir passwords, URLs completas ni secretos en comandos, documentación, logs o Git. En ejecución manual, `-W` solicita la contraseña sin incluirla en el historial. Para automatización futura se debe usar un almacén de secretos o `pgpass.conf` con ACL restringida.
4. Guardar los backups fuera del repositorio. Ruta local recomendada en Windows:

   ```text
   C:\Users\<operador>\Documents\Boliklor\Backups\PostgreSQL
   ```

5. Restringir esa carpeta al operador y a la cuenta de respaldo. El dump contiene datos personales y laborales aunque use formato binario.

Comprobar las ACL tanto del directorio como del archivo con `Get-Acl`. En el entorno Windows local validado se permiten únicamente reglas explícitas de control total para el propietario, `SYSTEM` y `Administradores`; no deben quedar grupos generales con lectura. Ajustar identidades equivalentes si el backup corre bajo una cuenta de servicio.

## Precheck obligatorio

Definir solo metadatos no secretos en la sesión y comprobar las herramientas:

```powershell
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGUSER = "<usuario_aprobado>"
$env:PGDATABASE = "boliklor_ot"

pg_dump --version
pg_restore --version
psql --version
psql -W --dbname postgres --command "select version();"
psql -W --dbname $env:PGDATABASE --command "select current_database();"
psql -W --dbname $env:PGDATABASE --command "select version_num from alembic_version;"
```

Abortar si `current_database()` no devuelve exactamente `boliklor_ot`, si el origen esperado es distinto o si no existe un único estado Alembic conocido. No ejecutar `alembic upgrade` como parte de este procedimiento.

## Crear el backup

Crear la carpeta fuera del repositorio y un nombre único en UTC:

```powershell
$backupRoot = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Boliklor\Backups\PostgreSQL'
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd_HHmmssZ')
$backupFile = Join-Path $backupRoot "boliklor_ot_pre_migration_$stamp.dump"

pg_dump -W --host $env:PGHOST --port $env:PGPORT --username $env:PGUSER `
  --dbname $env:PGDATABASE --format=custom --file $backupFile
if ($LASTEXITCODE -ne 0) { throw "pg_dump falló con código $LASTEXITCODE" }
```

Validar inmediatamente estructura, tamaño y hash:

```powershell
pg_restore --list $backupFile | Out-Null
if ($LASTEXITCODE -ne 0) { throw "El catálogo del backup no es legible" }
$backupItem = Get-Item -LiteralPath $backupFile
if ($backupItem.Length -le 0) { throw "El backup está vacío" }
Get-FileHash -Algorithm SHA256 -LiteralPath $backupFile
```

Registrar fecha UTC, motivo, base, host, puerto, revisión Alembic, versiones cliente/servidor, nombre, tamaño, SHA-256 y código de salida. No registrar credenciales.

## Ensayo de restore desechable

El nombre debe terminar en `_restore_test`. Confirmar que no existe antes de crearlo; si existe, no reutilizarlo ni borrarlo sin conocer su owner.

```powershell
$restoreDatabase = 'boliklor_ot_restore_test'
if ($restoreDatabase -notmatch '_restore_test$') { throw 'Nombre de restore inseguro' }

psql -W --dbname postgres --tuples-only --no-align `
  --command "select 1 from pg_database where datname = '$restoreDatabase';"
# Continuar solo si la consulta no devuelve filas.

createdb -W --host $env:PGHOST --port $env:PGPORT --username $env:PGUSER `
  --maintenance-db postgres --template template0 --encoding UTF8 $restoreDatabase
if ($LASTEXITCODE -ne 0) { throw "createdb falló con código $LASTEXITCODE" }

pg_restore -W --host $env:PGHOST --port $env:PGPORT --username $env:PGUSER `
  --dbname $restoreDatabase --exit-on-error --no-owner --no-privileges $backupFile
if ($LASTEXITCODE -ne 0) { throw "pg_restore falló con código $LASTEXITCODE" }
```

Validar antes de eliminar la base desechable:

- `current_database()` devuelve exactamente el nombre desechable.
- La revisión de `alembic_version` coincide con el origen.
- El conjunto de tablas públicas coincide con el origen.
- Los conteos de filas por tabla coinciden con el origen.
- Las constraints y claves foráneas quedaron creadas; no hay filas huérfanas en relaciones críticas.
- La aplicación no usó la base restaurada durante el ensayo y la base real no recibió escrituras.

Eliminar solo después de registrar el éxito y volver a validar el nombre literal:

```powershell
if ($restoreDatabase -ne 'boliklor_ot_restore_test') { throw 'Destino de limpieza inesperado' }
dropdb -W --host $env:PGHOST --port $env:PGPORT --username $env:PGUSER `
  --maintenance-db postgres --if-exists $restoreDatabase
if ($LASTEXITCODE -ne 0) { throw "dropdb falló con código $LASTEXITCODE" }
```

Si falla la creación, el restore o una comprobación, detenerse. No ejecutar un downgrade, no tocar `boliklor_ot` y no eliminar la base desechable fallida hasta diagnosticarla.

## Recuperación real conceptual

Una recuperación real requiere incidente declarado, owner y ventana de mantenimiento. El flujo recomendado es detener escrituras, conservar la base dañada, restaurar el último backup aprobado en una base nueva y aislada, validar revisión/esquema/conteos/integridad, ejecutar smoke tests y solo entonces cambiar la conexión de la aplicación mediante el mecanismo de infraestructura. Nunca usar el ensayo anterior para sobreescribir la base real ni hacer `dropdb boliklor_ot`.

Si se necesita un punto posterior al dump, este backup lógico no basta: la infraestructura debe implementar backups base y archivado WAL/PITR, con restauraciones periódicas verificadas.

## Frecuencia y retención

- [PROPUESTO] Crear y restaurar un backup inmediatamente antes de cada migración real.
- [PROPUESTO] Mientras no exista automatización, realizar al menos un backup diario cuando haya operación, siempre con verificación y copia fuera del equipo.
- [PENDIENTE_DE_DEFINICION] Retención, rotación, cifrado, copia externa, RPO y RTO. Hasta definirlos, no eliminar automáticamente backups pre-migración validados.

## Evidencia mínima del gate

El gate queda aprobado solo cuando existe evidencia de `pg_dump` con salida 0, catálogo legible, tamaño y SHA-256; `pg_restore` con salida 0 en una base desechable; comparación satisfactoria de revisión, tablas, conteos e integridad; y eliminación confirmada únicamente de la base desechable. La migración real sigue siendo una acción separada y requiere autorización explícita.

## Evidencia local validada el 2026-09-02

- [CONFIRMADO] Cliente y servidor PostgreSQL `18.6`; origen efectivo `boliklor_ot` en `localhost:5432`, revisión Alembic `20260831_07`.
- [CONFIRMADO] `pg_dump -Fc` terminó con exit code `0`; `pg_restore --list` terminó con exit code `0` y leyó 254 entradas.
- [CONFIRMADO] Backup fuera del repositorio: `C:\Users\soporte\Documents\Boliklor\Backups\PostgreSQL\boliklor_ot_pre_4b2b_20260902_143950Z.dump`, 105041 bytes, SHA-256 `bdae960d9d7e0e96b2cede78d5df8f627723d2e67112000abc3d0f7b07c0110e`.
- [CONFIRMADO] Directorio y archivo quedaron con ACL no heredadas: control total únicamente para el propietario local, `SYSTEM` y `Administradores`; el hash no cambió después del ajuste.
- [CONFIRMADO] Restore con exit code `0` en `boliklor_ot_restore_test`. Origen y restore coincidieron en revisión, 23 tablas públicas, conteos por tabla, 88 índices y 24 secuencias.
- [CONFIRMADO] Se comprobaron 28 claves foráneas sin filas huérfanas; las 244 filas totales comparadas incluyeron Identidad/RRHH, Asistencia, Inventario y OT.
- [CONFIRMADO] La base desechable se eliminó después de aprobar las validaciones. `boliklor_ot` permaneció en `20260831_07`; no se ejecutó Alembic ni se aplicó `20260901_08`.
