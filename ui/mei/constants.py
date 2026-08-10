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

# Activity type keys (fiscal nature for DAS). Labels via activity_label().
ACTIVITY_KEYS = ("comercio", "industria", "servico", "comercio_servico")


def activity_label(key: str) -> str:
    from core.i18n import t

    return t(f"mei.activity.{key}")


def activity_labels() -> dict[str, str]:
    return {k: activity_label(k) for k in ACTIVITY_KEYS}


# Back-compat: live labels (same as activity_labels()).
ACTIVITY_LABELS = activity_labels  # call: ACTIVITY_LABELS()
