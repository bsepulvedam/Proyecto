from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import app_timezone_name


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def app_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(app_timezone_name())
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(f"Zona horaria no válida: {app_timezone_name()}") from exc


def local_datetime(value: datetime) -> datetime:
    aware = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(app_timezone())
