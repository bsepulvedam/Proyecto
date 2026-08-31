# Geolocalización

La geolocalización es sensible. [CONFIRMADO] Se solicita únicamente en cada `ENTRADA` o `SALIDA`, nunca mediante tracking continuo. La hora del servidor es autoritativa. El backend evaluará la captura contra el radio configurable de la zona; un evento fuera de rango no se descarta y genera incidencia/revisión.

[PROPUESTO] Persistir timestamp, precisión y lugar esperado; separar coordenada capturada de la decisión `dentro_de_rango`; usar una fórmula documentada y conservar versión de la regla/radio. HTTPS es requisito del navegador/producción.

[CONFIRMADO] El acceso a GPS será restringido y se minimizará su exposición. [PENDIENTE] base legal, aviso/consentimiento, precisión máxima aceptada, retención exacta, alcance por rol y tratamiento de dispositivos sin GPS. Nunca incluir coordenadas exactas en logs generales ni UI no autorizada.
