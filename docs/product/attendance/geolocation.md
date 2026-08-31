# Geolocalización

La geolocalización es sensible. [CONFIRMADO] Se solicita únicamente en cada `ENTRADA` o `SALIDA`, nunca mediante tracking continuo. La hora del servidor es autoritativa. El backend evaluará la captura contra el radio configurable de la zona; un evento fuera de rango no se descarta y genera incidencia/revisión.

[IMPLEMENTADO 4B-1] El modelo conserva latitud, longitud, precisión y timestamp opcional capturado, separados de zona, distancia, radio y resultado derivados. El servicio usa Haversine, zona activa configurada más cercana y versión de regla. HTTPS seguirá siendo requisito de la futura captura web.

[CONFIRMADO] GPS será obligatorio para marcar; coordenadas inválidas, `0,0` y precisión no positiva se rechazan. Más de 100 m se registra con `GPS_BAJA_PRECISION`; fuera de rango también se registra. [PENDIENTE] base legal, aviso/consentimiento, retención exacta y alcance UI para coordenadas. Nunca incluir coordenadas exactas en logs generales ni UI no autorizada.
