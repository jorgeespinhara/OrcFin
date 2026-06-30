"""Portuguese month/year labels for charts and reports."""

from __future__ import annotations

MONTH_ABBR_PT: tuple[str, ...] = (
    "",
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
)


def format_month_year_label(year: int, month: int) -> str:
    """Return a compact label such as Jan/2026."""
    if 1 <= month <= 12:
        return f"{MONTH_ABBR_PT[month]}/{year}"
    return str(year)


def chart_point_label(point: dict) -> str:
    """Resolve a chart point dict to a month/year label."""
    year = point.get("year")
    month = point.get("month")
    if year is not None and month is not None:
        return format_month_year_label(int(year), int(month))
    return str(point.get("label", ""))