# Flujos de Asistencia

Actual: trabajador consulta calendario → abre Registrar asistencia → visualiza sesión/turno → pulsa ENTRADA o SALIDA → autoriza GPS puntual → recibe resultado seguro. También crea justificaciones y consulta/descarga su archivo. ADMIN administra lugares y asignaciones.

[IMPLEMENTADO 4B-2A] calendario personal → consultar sesiones del Worker autenticado dentro del mes → agrupar por fecha operacional → comprobar sesión cerrada con entrada/salida → derivar trabajado/revisión/fuera de rango/neutral → desplegar turno, horas, duración, cantidad e incidencias. No se expone GPS ni se calcula pago.

[IMPLEMENTADO 4B-1 backend] resolver Worker y turno → validar GPS → abrir con `ENTRADA` → impedir duplicado → cerrar con `SALIDA` después de 5 minutos → impedir salida duplicada → permitir otra sesión. Un turno nocturno cruza medianoche sin cierre automático; `APP_TIMEZONE` fija el día operacional.

[IMPLEMENTADO EN ÁRBOL 4B-2B backend] validar evidencia → cargar/cachear el catálogo comunal versionado → evaluar todas las zonas `RADIO`/`COMUNA` activas → ordenar por estado, prioridad, margen e ID → persistir evidencia y snapshot de evaluación → abrir incidencia por fuera de rango o baja precisión. `DENTRO_TOLERANCIA` no abre incidencia. [IMPLEMENTADO 4B-2 web] solicitar GPS únicamente al pulsar el botón → enviar evidencia con CSRF → resolver Worker autenticado → invocar el servicio. Fallos GPS o falta de marcaje no se convierten automáticamente en ausencia.

[IMPLEMENTADO EN ÁRBOL 4B-3A dominio] adaptar hechos de sesión → conservar turno y fecha operacional → derivar situación horaria/actividad/incompleto → agrupar una jornada pagable por turno factual y fecha → resolver tarifa individual/global vigente → calcular total provisional sin persistir agregados. Calendario personal reutiliza la proyección de sesión y explicita los incompletos.

[IMPLEMENTADO EN ÁRBOL 4B-3B backend] completar SALIDA administrativa → bloquear sesión → revalidar ENTRADA/ausencia de SALIDA → validar hora/mínimo/motivo → crear SALIDA sin GPS ficticio → crear intervención auditable → cerrar sesión → commit único. Decidir incidencia → bloquear/revalidar `PENDIENTE` → persistir `APROBADA` o `RECHAZADA` con actor/fecha/comentario. Las tarifas se versionan por fecha operacional y se adaptan al resolvedor común de 4B-3A.

[PENDIENTE 4B-3C+] ADMIN/JEFATURA lista y filtra trabajadores/período → abre calendario individual → revisa sesiones, incidencias y jornadas pagables → invoca las acciones administrativas protegidas → consulta tarifa efectiva → exporta un trabajador o todos en Excel. Permanecen pendientes portal, rutas/CSRF/RBAC finales, exportación, horas/días extra y detalle de errores/offline.
