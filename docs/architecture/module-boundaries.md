# Límites y ownership de módulos

| Módulo | Propietario de | Puede referenciar | No debe poseer |
|---|---|---|---|
| Identidad | Usuario, rol, sesión, credencial | Trabajador opcional | Datos laborales |
| Recursos Humanos | Trabajador, ciclo y estructura laboral futuros | Usuario opcional | Sesiones o marcajes |
| Asistencia | Lugar, asignación, justificación y futuros eventos | Trabajador | Copia completa del trabajador |
| Inventario | Empresa operativa, unidad, producto, movimiento, lote futuro | Identidad para auditoría futura | Datos laborales |

[IMPLEMENTADO] `Trabajador` se relaciona 0..1 con `Usuario`; asistencia usa FK a trabajador. [DEUDA_TECNICA] `Trabajador` reside en `app/models/identity.py` y la administración combina ambos conceptos. [PROPUESTO] mover ownership conceptual primero mediante contratos y documentación; cualquier cambio físico posterior será incremental.

Regla de dependencia: Identidad no depende de Asistencia; RRHH puede enlazar una cuenta; Asistencia depende de la identidad laboral de RRHH; Inventario permanece independiente salvo actor de auditoría. Prohibidos imports circulares y duplicación de nombres/estado laboral en asistencia.
