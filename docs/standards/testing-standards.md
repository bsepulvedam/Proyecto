# Estándares de testing

Pirámide: unitarias de reglas; integración de services/DB; API/web de contratos; migraciones en PostgreSQL; autorización parametrizada; regresión de seguridad; E2E mínimo. Prioridad: login/CSRF/roles, trabajador, marcaje/geocerca, recepción/salida/stock/lotes/vencimiento/ajuste. Fixtures aisladas, reloj controlado y storage temporal. CI debe ejecutar compile, suite y migración limpia.
