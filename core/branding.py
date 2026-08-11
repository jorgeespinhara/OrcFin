"""OrcFin product identity — single source of truth for naming."""

APP_VERSION = "0.2.18"

APP_NAME = "OrcFin"
APP_SUBTITLE = "Orçamento Financeiro"
APP_NAME_MEI = "OrcFin MEI"
APP_TAGLINE = f"{APP_NAME}: {APP_SUBTITLE}"

DB_FILENAME = "orcfin.db"

BACKUP_SUFFIX = ".orcfin.bak"
BACKUP_DB_ARCHIVE = "orcfin.db"

KEYRING_SERVICE = "OrcFin"

# (i18n key, color) — resolve name with t(key) at seed time
DEFAULT_PROFILE_SEED: tuple[tuple[str, str], ...] = (
    ("seed.profile_1", "#14B8A6"),
    ("seed.profile_2", "#6366F1"),
)