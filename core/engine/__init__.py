"""Finance engine — calculations, budgets, categorization (no UI, no AI)."""

from core.engine.budget_alerts import check_budget_impact, check_import_budget_impacts
from core.engine.categorization import (
    AUTO_CAT_MARKER,
    append_auto_cat_marker,
    apply_rules_retroactive,
    create_rule,
    delete_rule,
    get_all_rules,
    has_auto_cat_marker,
    strip_system_notes,
    suggest_category,
)
from core.engine.reporting import (
    generate_ai_context,
    get_dashboard_data,
    get_year_to_date_summary,
)

__all__ = [
    "AUTO_CAT_MARKER",
    "append_auto_cat_marker",
    "apply_rules_retroactive",
    "check_budget_impact",
    "check_import_budget_impacts",
    "create_rule",
    "delete_rule",
    "generate_ai_context",
    "get_all_rules",
    "get_dashboard_data",
    "get_year_to_date_summary",
    "has_auto_cat_marker",
    "strip_system_notes",
    "suggest_category",
]