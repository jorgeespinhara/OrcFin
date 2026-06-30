"""Personal and business profiles."""

from typing import List

from core.db.connection import get_connection
from core.models import Profile, ProfileType


def get_all_profiles(active_only: bool = True) -> List[Profile]:
    conn = get_connection()
    cur = conn.cursor()
    if active_only:
        cur.execute("SELECT * FROM profiles WHERE is_active = 1 ORDER BY id DESC")
    else:
        cur.execute("SELECT * FROM profiles ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [
        Profile(
            id=r["id"],
            name=r["name"],
            color=r["color"],
            profile_type=ProfileType(r["profile_type"] if "profile_type" in r.keys() else "personal"),
            created_at=r["created_at"],
            is_active=bool(r["is_active"]),
        )
        for r in rows
    ]


def create_profile(name: str, color: str = "#14B8A6") -> Profile:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO profiles (name, color) VALUES (?, ?)",
        (name, color)
    )
    profile_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return Profile(id=profile_id, name=name, color=color)


def update_profile(profile_id: int, name: str, color: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE profiles SET name = ?, color = ? WHERE id = ?",
        (name, color, profile_id)
    )
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def delete_profile(profile_id: int) -> bool:
    """Soft delete by deactivating. Prevents data loss."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE profiles SET is_active = 0 WHERE id = ?",
        (profile_id,)
    )
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success