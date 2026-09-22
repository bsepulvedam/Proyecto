"""Genera el par (token, digest) de la API key de servicio del bot.

El token en claro se imprime una sola vez y el ERP no lo guarda en ninguna
parte: va a la variable de entorno de N8N. El servidor sólo conserva el digest
en ``BOT_SERVICE_KEY_HASH``, así que perder el token obliga a regenerar el par,
no a recuperarlo.

Uso: python -m app.scripts.generate_bot_service_key
"""

import secrets

from app.core.service_auth import SERVICE_KEY_HEADER, service_key_digest


def main() -> None:
    token = secrets.token_urlsafe(48)
    print("Token para N8N (no se vuelve a mostrar, no lo guardes en el repo):")
    print(f"  {SERVICE_KEY_HEADER}: {token}")
    print()
    print("Digest para el .env del ERP:")
    print(f"  BOT_SERVICE_KEY_HASH={service_key_digest(token)}")


if __name__ == "__main__":
    main()
