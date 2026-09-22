"""Autenticación por API key de servicio para la API del bot de Telegram.

Deliberadamente separada de ``app.core.security``: ese módulo autentica
personas (sesión por cookie + CSRF, pensada para navegador) y éste autentica un
sistema. Un token de servicio no es un usuario del ERP — no tiene rol
ADMIN/JEFATURA/TRABAJADOR, no pasa por ``user_has_permission`` y su único
alcance son las rutas donde se monta esta dependencia
(``/api/bot/inventario/*``). Ver ``BOLIKLOR_BOT_API_DESIGN.md`` §4.
"""

import hashlib
import hmac
import logging

from fastapi import HTTPException, Request, status

from app.core.config import bot_service_key_hash

logger = logging.getLogger(__name__)

SERVICE_KEY_HEADER = "X-Service-Key"
SERVICE_CLIENT_BOT = "BOT_TELEGRAM"
_INVALID_KEY_DETAIL = "API key de servicio inválida o ausente"


def service_key_digest(token: str) -> str:
    """Digest SHA-256 (hex) del token de servicio.

    No se usa Argon2 (el patrón de contraseñas de ``auth_service``) a
    propósito: Argon2 está diseñado para secretos de baja entropía elegidos por
    humanos y aquí costaría 64 MiB de memoria por verificación, es decir, por
    cada request del bot — un vector de agotamiento de recursos en el propio
    chequeo de autenticación. El token es aleatorio de 48 bytes, así que no hay
    diccionario que atacar y un digest directo es suficiente.

    Tampoco se reutiliza el HMAC con ``session_secret()`` que ``auth_service``
    aplica a los tokens de sesión: eso ataría la vida de la integración del bot
    a la rotación del secreto de sesiones web, y rotar ese secreto dejaría al
    bot sin acceso en silencio, sin que nadie lo note hasta que falle una
    recepción.
    """
    return hashlib.sha256(token.encode()).hexdigest()


async def require_service_key(request: Request) -> str:
    """Exige un ``X-Service-Key`` válido. Deniega por defecto.

    Si ``BOT_SERVICE_KEY_HASH`` no está configurado, la API del bot queda
    cerrada por completo en vez de abierta.
    """
    expected = bot_service_key_hash()
    if not expected:
        # Se responde 401 y no 503 para no revelar al llamador si la
        # integración del bot está provisionada en este entorno.
        logger.warning(
            "Llamada a la API del bot con BOT_SERVICE_KEY_HASH sin configurar: %s",
            request.url.path,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_KEY_DETAIL)
    provided = request.headers.get(SERVICE_KEY_HEADER, "")
    if not provided or not hmac.compare_digest(service_key_digest(provided), expected):
        # Nunca se registra el token recibido, ni siquiera truncado.
        logger.warning("API key de servicio rechazada en %s", request.url.path)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_KEY_DETAIL)
    request.state.service_client = SERVICE_CLIENT_BOT
    return SERVICE_CLIENT_BOT
