"""OrcFin product identity — single source of truth for naming."""

APP_VERSION = "0.1.0-alpha"

APP_NAME = "OrcFin"
APP_SUBTITLE = "Orçamento Financeiro"
APP_NAME_MEI = "OrcFin MEI"
APP_TAGLINE = f"{APP_NAME}: {APP_SUBTITLE}"

DB_FILENAME = "orcfin.db"
LEGACY_DB_FILENAME = "finforge.db"

BACKUP_SUFFIX = ".orcfin.bak"
LEGACY_BACKUP_SUFFIX = ".finforge.bak"
BACKUP_DB_ARCHIVE = "orcfin.db"
LEGACY_BACKUP_DB_ARCHIVE = "finforge.db"

KEYRING_SERVICE = "OrcFin"
LEGACY_KEYRING_SERVICE = "FinForge"

DEFAULT_PROFILE_SEED: tuple[tuple[str, str], ...] = (
    ("Usuário 1", "#14B8A6"),
    ("Usuário 2", "#6366F1"),
)