"""Year/month period filter for personal finance screens."""

from __future__ import annotations

from datetime import date

import flet as ft

from ui.personal.charts import PERSONAL_ACCENT
from ui.theme import dropdown as themed_dropdown

MONTH_OPTIONS = [
    ("0", "Todos os meses"),
    ("1", "Janeiro"),
    ("2", "Fevereiro"),
    ("3", "Março"),
    ("4", "Abril"),
    ("5", "Maio"),
    ("6", "Junho"),
    ("7", "Julho"),
    ("8", "Agosto"),
    ("9", "Setembro"),
    ("10", "Outubro"),
    ("11", "Novembro"),
    ("12", "Dezembro"),
]


def period_label(year: int, month: int | None) -> str:
    if month:
        month_name = next(
            (label for key, label in MONTH_OPTIONS if int(key) == month),
            str(month),
        )
        return f"{month_name}/{year}"
    return f"Ano {year}"


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
        label="Ano",
        width=132,
        value=str(app.filter_year or current_year),
        options=year_options,
        on_select=handle_change,
    )
    month_dropdown = themed_dropdown(
        accent=PERSONAL_ACCENT,
        label="Mês",
        width=196,
        value=str(app.filter_month or 0),
        options=[ft.dropdown.Option(key, label) for key, label in MONTH_OPTIONS],
        on_select=handle_change,
    )

    return ft.Row(
        [year_dropdown, month_dropdown],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )