"""MEI shell visual constants."""

from ui.theme import PERSONAL_ACCENT, active as theme_colors

MEI_ACCENT = "#F59E0B"
MEI_ACCENT_DARK = "#422006"


def mei_surface() -> str:
    return theme_colors().surface


def mei_border() -> str:
    return theme_colors().border


def mei_field_bg() -> str:
    return theme_colors().field_bg


def mei_field_border() -> str:
    return theme_colors().field_border


# Kept for older imports; prefer theme_colors() in new code.
MEI_BG = "#0F172A"
MEI_CARD = "#1E293B"
MEI_BORDER = "#334155"
FIELD_BG = "#0F172A"
FIELD_BORDER = "#475569"

ACTIVITY_LABELS = {
    "comercio": "Comércio",
    "industria": "Indústria",
    "servico": "Prestação de Serviços",
    "comercio_servico": "Comércio + Serviços",
}
