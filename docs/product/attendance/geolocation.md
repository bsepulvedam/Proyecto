# Geolocalización

La geolocalización es sensible. [CONFIRMADO] Se solicita únicamente en cada `ENTRADA` o `SALIDA`, nunca mediante tracking continuo. La hora del servidor es autoritativa. El backend evalúa la captura contra todas las geocercas activas; un evento fuera de rango no se descarta y genera incidencia/revisión.

[IMPLEMENTADO 4B-1] El modelo conserva latitud, longitud, precisión y timestamp opcional capturado, separados de zona, distancia, radio y resultado derivados. El servicio usa Haversine, zona activa configurada más cercana y versión de regla. [IMPLEMENTADO 4B-2] el navegador usa `getCurrentPosition` solo al pulsar ENTRADA/SALIDA, no usa `watchPosition` ni almacenamiento cliente y envía inmediatamente la evidencia al backend. HTTPS es requisito de despliegue para que la geolocalización web opere fuera de contextos locales seguros.

[CONFIRMADO] GPS será obligatorio para marcar; coordenadas inválidas, `0,0` y precisión no positiva se rechazan. Más de 100 m se registra con `GPS_BAJA_PRECISION`; fuera de rango también se registra. [PENDIENTE] base legal, aviso/consentimiento, retención exacta y alcance UI para coordenadas. Nunca incluir coordenadas exactas en logs generales ni UI no autorizada.

[IMPLEMENTADO EN ÁRBOL 4B-2B] `RADIO` conserva distancia al centro y radio. `COMUNA` usa polígonos SUBDERE DPA 2023 transformados de EPSG:5360 a EPSG:4326 y seleccionados exclusivamente por `CUT_COM`; la distancia al borde se calcula en una proyección UTM local cacheada. El borde pertenece a la comuna y los primeros 100 m exteriores son `DENTRO_TOLERANCIA`.

[IMPLEMENTADO EN ÁRBOL 4B-2B] El GeoJSON reducido, validado y versionado contiene solo 13 comunas. El catálogo y sus geometrías métricas se cargan una vez por ruta/versión de proceso mediante cache en memoria; un archivo ausente, corrupto, con CRS inesperado, geometría inválida o código desconocido produce un error seguro y revierte el marcaje.
