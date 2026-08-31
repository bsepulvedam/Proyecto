# Recursos Humanos

RRHH es la fuente maestra del trabajador. [IMPLEMENTADO] `trabajadores` contiene identificador, cuenta opcional, empresa, código, nombres, apellidos y activo. [DEUDA_TECNICA] vive dentro del modelo/administración de identidad. [PROPUESTO] cargo, área, equipo, supervisor, estado laboral, ingreso/salida, jornada, contrato, centro, contacto e historial pertenecen a RRHH. [PENDIENTE] documentos, vacaciones, licencias, permisos y observaciones requieren definición de proceso y privacidad.

Identidad posee credenciales; RRHH puede asociar una cuenta sin exigirla. Asistencia referencia `trabajador_id` y no replica su ficha.
