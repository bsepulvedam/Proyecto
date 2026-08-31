# Estándares de logging

Logs estructurados en UTC con nivel, evento, request ID, ruta, duración, resultado y actor interno cuando sea necesario. Eventos: inicio/fin de request, fallo de dependencia, autenticación sin username sensible, denegación, migración/release y errores de negocio agregables. Nunca passwords, hashes, tokens, cookies, secretos, archivos, coordenadas exactas ni PII innecesaria. Separar auditoría inmutable de negocio.
