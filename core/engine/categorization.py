"""Rule-based auto-categorization (if/then, priority order)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from core.db.connection import get_connection

AUTO_CAT_MARKER = "[sys:auto-cat]"


def append_auto_cat_marker(notes: str | None) -> str:
    """Append system marker without clobbering user notes."""
    marker = f"{AUTO_CAT_MARKER}rule"
    if notes and AUTO_CAT_MARKER in notes:
        return notes
    if notes and notes.strip():
        return f"{notes.strip()}\n{marker}"
    return marker


def strip_system_notes(notes: str | None) -> str | None:
    """Remove system markers before showing notes in the UI."""
    if not notes:
        return None
    kept = [
        line for line in notes.splitlines()
        if AUTO_CAT_MARKER not in line
        and not line.strip().startswith("installment:")
        and not line.strip().startswith("import:")
    ]
    text = "\n".join(ln.strip() for ln in kept if ln.strip())
    return text or None


def has_auto_cat_marker(notes: str | None) -> bool:
    return bool(notes and AUTO_CAT_MARKER in notes)


@dataclass
class CategorizationRule:
    id: int
    priority: int
    match_type: str  # contains, starts_with, equals
    pattern: str
    category_id: int
    profile_id: Optional[int] = None


def get_all_rules() -> list[CategorizationRule]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM categorization_rules ORDER BY priority ASC, id ASC"
    )
    rows = cur.fetchall()
    conn.close()
    return [
        CategorizationRule(
            id=r["id"],
            priority=r["priority"],
            match_type=r["match_type"],
            pattern=r["pattern"],
            category_id=r["category_id"],
            profile_id=r["profile_id"],
        )
        for r in rows
    ]


def create_rule(
    pattern: str,
    category_id: int,
    match_type: str = "contains",
    profile_id: Optional[int] = None,
    priority: int = 100,
) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO categorization_rules (priority, match_type, pattern, category_id, profile_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (priority, match_type, pattern.strip().upper(), category_id, profile_id),
    )
    rule_id = cur.lastrowid
    conn.commit()
    conn.close()
    return rule_id


def delete_rule(rule_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM categorization_rules WHERE id = ?", (rule_id,))
    ok = cur.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def _matches(description: str, match_type: str, pattern: str) -> bool:
    desc = description.upper()
    pat = pattern.upper()
    if match_type == "contains":
        return pat in desc
    if match_type == "starts_with":
        return desc.startswith(pat)
    if match_type == "equals":
        return desc == pat
    return False


def suggest_category(
    description: str,
    profile_id: Optional[int] = None,
) -> Optional[int]:
    cat, _ = suggest_category_with_confidence(description, profile_id)
    return cat


def suggest_category_with_confidence(
    description: str,
    profile_id: Optional[int] = None,
) -> tuple[Optional[int], str]:
    for rule in get_all_rules():
        if rule.profile_id is not None and profile_id is not None and rule.profile_id != profile_id:
            continue
        if _matches(description, rule.match_type, rule.pattern):
            return rule.category_id, "high"
    if len(description.strip()) < 4:
        return None, "review"
    return None, "low"


def update_rule(rule_id: int, *, pattern: str | None = None, category_id: int | None = None) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    sets: list[str] = []
    params: list[Any] = []
    if pattern is not None:
        sets.append("pattern = ?")
        params.append(pattern.strip().upper())
    if category_id is not None:
        sets.append("category_id = ?")
        params.append(category_id)
    if not sets:
        conn.close()
        return False
    params.append(rule_id)
    cur.execute(f"UPDATE categorization_rules SET {', '.join(sets)} WHERE id = ?", params)
    ok = cur.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def apply_rules_retroactive(profile_id: Optional[int] = None) -> int:
    """Re-apply rules to uncategorized-like transactions (notes marker). Returns count updated."""
    from core.db.repositories.transactions import get_transactions, update_transaction

    updated = 0
    txs = get_transactions(profile_id=profile_id, limit=2000)
    for tx in txs:
        if has_auto_cat_marker(tx.notes):
            continue
        cat_id = suggest_category(tx.description, tx.profile_id)
        if cat_id and cat_id != tx.category_id:
            tx.category_id = cat_id
            tx.notes = append_auto_cat_marker(tx.notes)
            if update_transaction(tx):
                updated += 1
    return updated