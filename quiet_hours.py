"""Tungi tanaffus: Toshkent vaqti bilan 00:00 — 07:00 oralig'ida eMaktab'ga
avtomatik kirilmaydi (oraliq config.py / QUIET_START_HOUR, QUIET_END_HOUR
orqali o'zgartiriladi)."""

from datetime import datetime, timedelta, timezone

from config import settings

TASHKENT_TZ = timezone(timedelta(hours=5))


def is_quiet_hours(now: datetime | None = None) -> bool:
    now = now or datetime.now(TASHKENT_TZ)
    h = now.astimezone(TASHKENT_TZ).hour
    start, end = settings.quiet_start_hour, settings.quiet_end_hour
    if start == end:
        return False
    if start < end:
        return start <= h < end
    return h >= start or h < end  # yarim tundan o'tadigan oraliq (masalan 23 -> 6)


QUIET_MESSAGE = (
    "Tizim har kuni soat 00:00 dan 07:00 gacha eMaktab'ga kira olmaydi. "
    "Iltimos, soat 07:00 dan keyin qayta urinib ko'ring."
)
