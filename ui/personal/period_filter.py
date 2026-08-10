"""Year/month period filter for personal finance screens."""

from __future__ import annotations

from datetime import date

import flet as ft

from core.i18n import t
from ui.personal.charts import PERSONAL_ACCENT
from ui.theme import dropdown as themed_dropdown

_MONTH_KEYS = (
    "personal.month_all",
    "personal.month_1",
    "personal.month_2",
    "personal.month_3",
    "personal.month_4",
    "personal.month_5",
    "personal.month_6",
    "personal.month_7",
    "personal.month_8",
    "personal.month_9",
    "personal.month_10",
    "personal.month_11",
    "personal.month_12",
)


def month_options() -> list[tuple[str, str]]:
    """Localized month dropdown options; call at build time so locale is current."""
    return [(str(i), t(_MONTH_KEYS[i])) for i in range(13)]


# Backward-compatible name used by settings/financial and others.
# Prefer month_options() for live UI so language switches apply.
MONTH_OPTIONS = month_options()


def period_label(year: int, month: int | None) -> str:
    opts = month_options()
    if month:
        month_name = next(
            (label for key, label in opts if int(key) == month),
            str(month),
        )
        return f"{month_name}/{year}"
    return t("personal.year_label", year=year)


def build_period_filter(app: "OrcFinApp", on_change=None) -> ft.Row:
    """Year/month dropdowns wired to app.filter_year / filter_month."""

    def handle_change(_):
        year = int(year_dropdown.value)
        month_raw = int(month_dropdown.value)
        month = None if month_raw == 0 else month_raw
        app.set_period_filter(year, month)
        if on_change:
            on_change()
        else:
            app.refresh_current_view()

    current_year = date.today().year
    year_options = [
        ft.dropdown.Option(str(y), str(y))
        for y in range(current_year, current_year - 11, -1)
    ]

    year_dropdown = themed_dropdown(
        accent=PERSONAL_ACCENT,
        label=t("common.year"),
        width=132,
        value=str(app.filter_year or current_year),
        options=year_options,
        on_select=handle_change,
    )
    month_dropdown = themed_dropdown(
        accent=PERSONAL_ACCENT,
        label=t("common.month"),
        width=196,
        value=str(app.filter_month or 0),
        options=[ft.dropdown.Option(key, label) for key, label in month_options()],
        on_select=handle_change,
    )

    return ft.Row(
        [year_dropdown, month_dropdown],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
