# Contrato de trabajo para Boliklor

## Contexto y alcance

Boliklor es una aplicación web FastAPI/PostgreSQL existente. El alcance prioritario es Identidad y acceso, Recursos Humanos, Asistencia e Inventario. Órdenes de trabajo es funcionalidad heredada existente, pero no debe ampliarse sin una decisión explícita. No diseñar anticipadamente otros módulos ERP.

## Fuentes de verdad y lectura obligatoria

Ante conflicto prevalecen: código ejecutable, configuración real, migraciones, tests y finalmente README. Antes de cambiar algo leer, en este orden: este archivo, `ARCHITECTURE.md`, documentación del módulo, estándares aplicables y ADR relacionados. Clasificar afirmaciones funcionales como `[IMPLEMENTADO]`, `[CONFIRMADO]`, `[PROPUESTO]`, `[PENDIENTE]` o `[DEUDA_TECNICA]`.

## Reglas generales y Git

- Preservar compatibilidad salvo autorización expresa. Investigar primero y limitar el diff al objetivo.
- No mezclar refactors con cambios funcionales. No eliminar ni mover archivos sin revisar consumidores.
- No hacer commit, push, rebase, reset destructivo ni reescribir historial salvo instrucción explícita.
- No versionar `.env`, secretos, documentos cargados, dumps, credenciales ni datos personales.
- Antes de entregar: revisar `git status`, `git diff --stat`, el diff relevante y reportar pruebas y limitaciones.

## Backend y API

- Mantener el monolito modular: rutas delgadas, validación en schemas, casos de uso en services y persistencia ORM.
- Los límites de dominio prevalecen sobre la conveniencia de imports cruzados. Evitar ciclos y consultas SQL en templates.
- Conservar rutas y contratos existentes salvo cambio aprobado; documentar errores y autorización backend.
- Validar entradas en el límite, usar transacciones atómicas y traducir errores esperables sin filtrar detalles internos.

## Frontend

- `app/templates` y `app/static` son la UI operativa; `frontend/` es un prototipo histórico.
- Mantener Jinja2 con mejora progresiva, navegación por permisos y feedback accesible. Ocultar UI nunca sustituye autorización backend.
- No introducir un framework cliente sin una decisión arquitectónica.

## Base de datos y Alembic

- SQLAlchemy describe el uso actual y Alembic el historial desplegable; comprobar su paridad.
- Todo cambio de esquema requiere una revisión Alembic nueva. Nunca editar una revisión ya compartida ni usar `create_all` como migración.
- Revisar upgrade/downgrade, constraints, índices, nulabilidad, FKs, datos existentes y rollback. Aplicar migraciones solo con autorización y contra el entorno confirmado.
- No modificar datos reales ni crear fixtures en PostgreSQL real. Fechas persistidas en UTC; interpretación operacional con `APP_TIMEZONE`.

## Seguridad, privacidad y logging

- Autenticación y autorización se aplican en backend; denegar por defecto en producción.
- No registrar contraseñas, tokens, secretos, archivos laborales, coordenadas precisas ni datos personales innecesarios.
- Tratar geolocalización, asistencia e información laboral como sensibles. Toda política legal o de retención necesita decisión del negocio.
- Mantener CSRF en mutaciones con cookie, cookies seguras en HTTPS y consultas parametrizadas por SQLAlchemy.

## Testing y documentación

- Añadir pruebas proporcionales: unitarias para reglas, integración para DB, API/web para contratos, autorización negativa y regresión de seguridad.
- Tests aislados y deterministas; nunca usar DB real. No reducir controles para hacer pasar pruebas.
- Actualizar documentación afectada y distinguir estado actual, objetivo, brecha y siguiente paso.

## Definición de terminado e informe

Un cambio termina cuando el comportamiento solicitado está implementado, las migraciones y contratos son coherentes, las pruebas relevantes pasan, seguridad/permisos fueron revisados y la documentación quedó vigente. El informe final debe listar resultado, archivos, validaciones, riesgos pendientes y confirmar explícitamente si hubo migraciones, cambios de DB, commit, push o despliegue.

## Continuidad operativa

Antes de comenzar una nueva tarea de desarrollo, revisar `CURRENT.md` junto con el código relacionado. Al finalizar una fase o tarea aprobada, actualizar `CURRENT.md` para reflejar el estado real del repositorio, los tests ejecutados, problemas conocidos y el punto exacto de continuidad. `CURRENT.md` nunca debe declarar como implementado algo que no pueda verificarse en el código.
