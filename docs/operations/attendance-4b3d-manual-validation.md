# Validación manual de Asistencia 4B-3D

Estado: [PENDIENTE EJECUCIÓN MANUAL]. Este checklist está preparado para ejecutarse exclusivamente contra `boliklor_ot_test` en `20260902_09`. No autoriza migrar ni mutar `boliklor_ot`.

## Precondiciones

1. Configurar `APP_ENV=test`, autenticación activa, cookie no segura solo para localhost y `DATABASE_URL` apuntando a la misma URL desechable aprobada en `TEST_DATABASE_URL`.
2. Confirmar que el nombre de base termina en `_test` o `_ci`, que no coincide con la URL real y que `alembic current` informa `20260902_09 (head)`.
3. Usar usuarios de prueba ADMIN, JEFATURA y TRABAJADOR; no copiar cuentas ni datos personales reales.
4. Levantar Uvicorn solo en `127.0.0.1` y conservar registro de los IDs de fixtures para eliminarlos al terminar.

## ADMIN — tarifas

- Abrir `/admin/asistencia/tarifas` y comprobar historial global, monto, vigencia, origen/actor y fecha de creación.
- Crear una nueva vigencia global mediante la confirmación explícita; comprobar mensaje de éxito y que la versión anterior no cambia.
- Abrir un trabajador, comprobar tarifa efectiva/origen y crear un override individual con otra vigencia.
- Volver a Supervisión y comprobar que el total provisional cambia solo desde la fecha efectiva.
- Repetir una vigencia global e individual y comprobar conflicto controlado sin fila adicional.
- Enviar formularios sin CSRF y con token alterado mediante las herramientas del navegador; ambos deben responder 403.

## JEFATURA y TRABAJADOR

- JEFATURA abre Supervisión, ve tarifa efectiva/total y descarga ambos Excel.
- JEFATURA no ve “Tarifas asistencia”; acceso directo GET/POST bajo `/admin/asistencia/tarifas` responde 403.
- TRABAJADOR no ve Supervisión ni tarifas; acceso directo responde 403.
- Una sesión anónima se redirige a login.

## Excel conjunto

- Aplicar período y búsqueda en Supervisión y descargar `asistencia_<desde>_<hasta>.xlsx`.
- Abrirlo en Excel o LibreOffice; comprobar las seis columnas obligatorias, trabajadores filtrados, caracteres especiales, días, jornadas, dobles turnos, incidencias y total.
- Usar un Worker de prueba cuyo nombre/código comience con `=`, `+`, `-` o `@`; comprobar que la celda es texto y no ejecuta una fórmula.

## Excel individual

- Descargar desde el trabajador supervisado y comprobar hojas `Resumen` y `Detalle diario`.
- Verificar período, DIURNO/NOCTURNO, una sesión incompleta, un doble turno, incidencias, tarifa/origen y totales.
- Para una fecha anterior a la primera tarifa, comprobar `Sin tarifa configurada` y ausencia de un total inventado.
- Buscar en ambas hojas `latitud`, `longitud` y coordenadas de fixtures; no debe haber coincidencias.

## Cierre

- Comparar manualmente un Worker/período entre portal y Excel: días trabajados, jornadas pagables, dobles turnos, incidencias y total deben coincidir.
- Eliminar únicamente los fixtures identificados de `boliklor_ot_test` y volver a confirmar `20260902_09 (head)`.
- Registrar fecha, navegador, aplicación de planillas, resultado y desviaciones. No marcar este checklist confirmado sin esa evidencia.
