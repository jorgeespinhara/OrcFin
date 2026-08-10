"""MEI operational profiles — how the business runs (not fiscal nature)."""

from __future__ import annotations

OperationalProfile = str

PROFILES: tuple[str, ...] = (
    "sales",
    "on_demand",
    "by_order",
    "recurring",
    "mixed",
)

DEFAULT_PROFILE = "on_demand"

# Membership set (labels/hints via i18n keys mei.profile.* / mei.profile_hint.*)
PROFILE_KEYS = frozenset(PROFILES)


def normalize_cnae(raw: str | None) -> str:
    if not raw:
        return ""
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits[:7] if len(digits) >= 4 else ""


def suggest_profile(cnae: str | None) -> str:
    code = normalize_cnae(cnae)
    if not code:
        return DEFAULT_PROFILE

    division = int(code[:2])
    group = int(code[:4]) if len(code) >= 4 else division * 100

    if division in (14, 15, 16) or group in (1071, 1072, 1082, 3101, 3102, 3103):
        return "by_order"
    if division in (41, 42, 43):
        return "by_order"
    if division == 47:
        return "sales"
    if division in (45, 46):
        return "mixed"
    if division in (56, 10):
        return "sales"
    if division == 96:
        return "mixed"
    if division in (80, 85):
        return "recurring"
    if division in (62, 63, 69, 70, 71, 72, 73, 74, 78, 82):
        return "on_demand"
    if division in (49, 50, 51, 52, 53):
        return "on_demand"
    if division in (31, 32, 33):
        return "by_order"
    return DEFAULT_PROFILE


def profile_label(profile: str | None) -> str:
    from core.i18n import t

    key = profile if profile in PROFILE_KEYS else DEFAULT_PROFILE
    return t(f"mei.profile.{key}")


def profile_hint(profile: str | None) -> str:
    from core.i18n import t

    key = profile if profile in PROFILE_KEYS else DEFAULT_PROFILE
    return t(f"mei.profile_hint.{key}")


def enabled_modules(profile: str | None) -> frozenset[str]:
    key = profile if profile in PROFILE_KEYS else DEFAULT_PROFILE
    modules = {"core", "receivables"}
    if key in ("by_order", "mixed"):
        modules.add("orders")
    if key == "recurring":
        modules.add("recurring_billing")
    if key in ("sales", "mixed"):
        modules.add("inventory")
    return frozenset(modules)