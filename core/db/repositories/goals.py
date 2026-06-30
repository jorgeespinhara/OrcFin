"""Savings and financial goals."""

from datetime import date
from typing import Any, Dict, List, Optional

from core.db.connection import get_connection


def create_goal(name: str, target_amount: float, deadline: Optional[date] = None, profile_id: Optional[int] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO goals (name, target_amount, deadline, profile_id)
        VALUES (?, ?, ?, ?)
    """, (name, target_amount, deadline.isoformat() if deadline else None, profile_id))
    goal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return goal_id


def get_active_goals(profile_id: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM goals WHERE is_completed = 0"
    if profile_id:
        query += " AND (profile_id = ? OR profile_id IS NULL)"
        cursor.execute(query, (profile_id,))
    else:
        cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_goal_progress(goal_id: int, add_amount: float) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE goals 
        SET current_amount = current_amount + ? 
        WHERE id = ?
    """, (add_amount, goal_id))
    cursor.execute(
        "UPDATE goals SET is_completed = 1 WHERE id = ? AND current_amount >= target_amount",
        (goal_id,),
    )
    conn.commit()
    conn.close()
    return True


def delete_goal(goal_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success