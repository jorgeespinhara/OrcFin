"""Income and expense categories."""

import sqlite3
from typing import List, Optional

from core.db.connection import get_connection
from core.db.repositories.mei import MEI_CATEGORY_SEED
from core.models import Category, TransactionType

MEI_CATEGORY_NAMES = frozenset(name for name, _, _, _ in MEI_CATEGORY_SEED)


def is_mei_category(category: Category) -> bool:
    return category.name in MEI_CATEGORY_NAMES


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


def get_all_categories():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [
        Category(
            id=r["id"],
            name=r["name"],
            type=r["type"],
            icon=r["icon"],
            is_mei_deductible=bool(r["is_mei_deductible"] if "is_mei_deductible" in r.keys() else 0),
            created_at=r["created_at"],
        )
        for r in rows
    ]


def create_category(name: str, type_: TransactionType, icon: Optional[str] = None) -> Category:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO categories (name, type, icon) VALUES (?, ?, ?)",
        (name, type_.value, icon)
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
        (name, icon, category_id)
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