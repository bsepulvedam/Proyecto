# Reglas de `app/`

Aplican además las reglas raíz. Mantener dependencias `web/api -> services -> models/database`; `core` solo contiene capacidades transversales. Evitar reglas de negocio en rutas y templates. Cerrar sesiones mediante `get_db`, hacer rollback ante fallos y no confirmar parcialmente un caso de uso. Toda ruta mutante conserva CSRF y autorización backend. Un trabajador laboral pertenece conceptualmente a RRHH; asistencia solo lo referencia. Inventario es dueño de productos, movimientos y stock.
