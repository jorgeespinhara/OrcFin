"""MEI shell visual constants."""

from ui.theme import PERSONAL_ACCENT

MEI_ACCENT = "#F59E0B"

# Activity type keys (fiscal nature for DAS). Labels via activity_label().
ACTIVITY_KEYS = ("comercio", "industria", "servico", "comercio_servico")


def activity_label(key: str) -> str:
    from core.i18n import t

    return t(f"mei.activity.{key}")
