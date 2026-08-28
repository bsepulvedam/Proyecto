import os
import secrets

_DEVELOPMENT_SESSION_SECRET = secrets.token_urlsafe(48)


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def auth_enforced() -> bool:
    return env_bool("AUTH_ENFORCED", False)


def cookie_secure() -> bool:
    return env_bool("COOKIE_SECURE", False)


def session_secret() -> str:
    configured = os.getenv("SESSION_SECRET", "").strip()
    if configured:
        return configured
    if auth_enforced():
        raise RuntimeError("SESSION_SECRET debe configurarse cuando AUTH_ENFORCED=true")
    return _DEVELOPMENT_SESSION_SECRET


def session_hours() -> int:
    try:
        return max(1, int(os.getenv("SESSION_HOURS", "12")))
    except ValueError:
        return 12


def app_timezone_name() -> str:
    return os.getenv("APP_TIMEZONE", "America/Santiago").strip() or "America/Santiago"


def justification_storage_dir() -> str:
    return os.getenv("JUSTIFICATION_STORAGE_DIR", "storage/justificaciones").strip()


def justification_max_bytes() -> int:
    try:
        return max(1, int(os.getenv("JUSTIFICATION_MAX_MB", "8"))) * 1024 * 1024
    except ValueError:
        return 8 * 1024 * 1024
