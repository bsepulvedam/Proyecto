# Estándares backend

Rutas delgadas; Pydantic valida entrada; services expresan casos de uso; ORM persiste. Una operación empresarial corresponde a una transacción con rollback. No hacer commits parciales ni capturar `Exception` sin registrar contexto seguro y relanzar/traducir. Consultas paginadas y eager loading explícito. Dependencias de dominio en una dirección; configuración validada al inicio. Type hints y nombres existentes en español coherente.
