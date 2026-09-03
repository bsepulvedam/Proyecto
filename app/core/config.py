import os
import re
import secrets
from datetime import time

_DEVELOPMENT_SESSION_SECRET = secrets.token_urlsafe(48)
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_VALID_ENVIRONMENTS = {"development", "test", "staging", "production"}
_AUTH_BYPASS_ENVIRONMENTS = {"development", "test"}


def env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    value = raw_value.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise RuntimeError(f"{name} debe ser un booleano válido")


def app_environment() -> str:
    environment = os.getenv("APP_ENV", "production").strip().lower()
    if environment not in _VALID_ENVIRONMENTS:
        raise RuntimeError(
            "APP_ENV debe ser development, test, staging o production"
        )
    return environment


def auth_enforced() -> bool:
    environment = app_environment()
    enforced = env_bool("AUTH_ENFORCED", True)
    if not enforced and environment not in _AUTH_BYPASS_ENVIRONMENTS:
        raise RuntimeError(
            "AUTH_ENFORCED=false solo está permitido en development o test"
        )
    return enforced


def cookie_secure() -> bool:
    return env_bool("COOKIE_SECURE", False)


def session_secret() -> str:
    configured = os.getenv("SESSION_SECRET", "").strip()
    if configured:
        return configured
    if auth_enforced():
        raise RuntimeError("SESSION_SECRET debe configurarse cuando AUTH_ENFORCED=true")
    return _DEVELOPMENT_SESSION_SECRET


def validate_security_config() -> None:
    if auth_enforced():
        session_secret()


def session_hours() -> int:
    try:
        return max(1, int(os.getenv("SESSION_HOURS", "12")))
    except ValueError:
        return 12


def app_timezone_name() -> str:
    return os.getenv("APP_TIMEZONE", "America/Santiago").strip() or "America/Santiago"


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} debe ser un entero positivo") from exc
    if value <= 0:
        raise RuntimeError(f"{name} debe ser un entero positivo")
    return value


def attendance_min_session_minutes() -> int:
    return _positive_int("ATTENDANCE_MIN_SESSION_MINUTES", 5)


def attendance_max_gps_accuracy_meters() -> int:
    return _positive_int("ATTENDANCE_MAX_GPS_ACCURACY_METERS", 100)


def attendance_commune_boundary_tolerance_meters() -> int:
    return _positive_int("ATTENDANCE_COMMUNE_BOUNDARY_TOLERANCE_METERS", 100)


def _time_value(name: str, default: str) -> time:
    raw_value = os.getenv(name, default).strip()
    if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", raw_value) is None:
        raise RuntimeError(f"{name} debe usar formato HH:MM")
    return time.fromisoformat(raw_value)


def attendance_day_shift_start() -> time:
    return _time_value("ATTENDANCE_DAY_SHIFT_START", "09:00")


def attendance_day_shift_end() -> time:
    return _time_value("ATTENDANCE_DAY_SHIFT_END", "18:00")


def attendance_night_shift_start() -> time:
    return _time_value("ATTENDANCE_NIGHT_SHIFT_START", "19:00")


def attendance_night_shift_end() -> time:
    return _time_value("ATTENDANCE_NIGHT_SHIFT_END", "05:00")


def attendance_late_tolerance_minutes() -> int:
    return _positive_int("ATTENDANCE_LATE_TOLERANCE_MINUTES", 10)


def justification_storage_dir() -> str:
    return os.getenv("JUSTIFICATION_STORAGE_DIR", "storage/justificaciones").strip()


def justification_max_bytes() -> int:
    try:
        return max(1, int(os.getenv("JUSTIFICATION_MAX_MB", "8"))) * 1024 * 1024
    except ValueError:
        return 8 * 1024 * 1024
