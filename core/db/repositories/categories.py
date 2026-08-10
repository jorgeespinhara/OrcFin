"""Income and expense categories."""

import sqlite3
from typing import List, Optional

from core.categories_catalog import MEI_CATEGORY_SEED, category_label
from core.db.connection import get_connection
from core.models import Category, TransactionType

MEI_CATEGORY_NAMES = frozenset(name for _slug, _t, _i, name, _d in MEI_CATEGORY_SEED)
MEI_CATEGORY_SLUGS = frozenset(slug for slug, _t, _i, _n, _d in MEI_CATEGORY_SEED)


def is_mei_category(category: Category) -> bool:
    if category.slug and category.slug in MEI_CATEGORY_SLUGS:
        return True
    return category.name in MEI_CATEGORY_NAMES


def display_name(category: Category) -> str:
    """Localized label for UI lists and dropdowns."""
    return category_label(category.slug, category.name)


def get_categories_for_mode(mei_mode: bool) -> List[Category]:
    """Return MEI-only categories in MEI mode; hide them in personal mode."""
    all_cats = get_all_categories()
    if mei_mode:
        return [c for c in all_cats if is_mei_category(c)]
    return [c for c in all_cats if not is_mei_category(c)]


def get_categories_for_profile(profile_id: int) -> List[Category]:
    conn = get_connection()
    row = conn.execute(
        "SELECT profile_type FROM profiles WHERE id = ?",
        (profile_id,),
    ).fetchone()
    conn.close()
    mei_mode = bool(row and row["profile_type"] == "mei")
    return get_categories_for_mode(mei_mode)


def _row_to_category(r) -> Category:
    keys = r.keys()
    return Category(
        id=r["id"],
        name=r["name"],
        type=r["type"],
        icon=r["icon"],
        slug=r["slug"] if "slug" in keys else None,
        is_mei_deductible=bool(r["is_mei_deductible"] if "is_mei_deductible" in keys else 0),
        created_at=r["created_at"],
    )


def get_all_categories():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [_row_to_category(r) for r in rows]


def get_category_by_slug(slug: str) -> Optional[Category]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories WHERE slug = ? LIMIT 1", (slug,))
    row = cur.fetchone()
    conn.close()
    return _row_to_category(row) if row else None


def create_category(name: str, type_: TransactionType, icon: Optional[str] = None) -> Category:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO categories (name, type, icon) VALUES (?, ?, ?)",
        (name, type_.value, icon),
    )
    cat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return Category(id=cat_id, name=name, type=type_, icon=icon)


def update_category(category_id: int, name: str, icon: Optional[str] = None) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE categories SET name = ?, icon = ? WHERE id = ?",
        (name, icon, category_id),
    )
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def delete_category(category_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        success = cursor.rowcount > 0
    except sqlite3.IntegrityError:
        success = False  # Category in use by transactions
    conn.commit()
    conn.close()
    return success
