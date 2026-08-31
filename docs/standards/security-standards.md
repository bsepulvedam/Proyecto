# Estándares de seguridad

Producción fail-closed: auth obligatoria, secreto fuerte, cookie Secure y HTTPS. Autorización/ownership en backend y CSRF en mutaciones con cookies. Argon2id y tokens opacos; rotar/revocar al cambiar credenciales. Limitar intentos de login en proxy/app. Validar uploads por tamaño, contenido, nombre y storage privado. Minimizar PII/GPS y aplicar least privilege. Revisar dependencias y cabeceras antes de release.
