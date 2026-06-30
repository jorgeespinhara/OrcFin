"""MEI calendar helpers — export DAS reminders as .ics (local)."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from pathlib import Path

from core.db.repositories.mei import get_mei_config
from core.domain.entities.mei_profile import MeiProfile
from core.services.mei_service import das_payment_exists

_EXPORT_DIR = Path(__file__).parent.parent / "exports"


def _ics_date(d: date) -> str:
    return d.strftime("%Y%m%d")


def export_das_ics(profile_id: int, months_ahead: int = 12) -> Path:
    cfg = get_mei_config(profile_id)
    if not cfg:
        raise ValueError("Perfil MEI não configurado")

    entity = MeiProfile(cfg)
    _EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = _EXPORT_DIR / f"das_mei_{profile_id}_{date.today():%Y%m%d}.ics"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//OrcFin//MEI DAS//PT",
        "CALSCALE:GREGORIAN",
    ]
    ref = date.today()
    for _ in range(months_ahead):
        das = entity.das_due_info(ref)
        due: date = das["due_date"]
        if not das_payment_exists(profile_id, due.year, due.month):
            uid = f"das-{profile_id}-{due.year}{due.month:02d}@orcfin"
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTART;VALUE=DATE:{_ics_date(due)}",
                f"DTEND;VALUE=DATE:{_ics_date(due + timedelta(days=1))}",
                f"SUMMARY:DAS MEI — {entity.das_amount()}",
                "DESCRIPTION:Pagar pelo app Simples Nacional e confirmar no OrcFin.",
                "END:VEVENT",
            ])
        y, m = (ref.year + 1, 1) if ref.month == 12 else (ref.year, ref.month + 1)
        ref = date(y, m, min(cfg.das_day, calendar.monthrange(y, m)[1]))

    lines.append("END:VCALENDAR")
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return path