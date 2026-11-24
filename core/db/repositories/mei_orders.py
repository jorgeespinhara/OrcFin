"""MEI work orders, suppliers, and outsourcing lines."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from core.db.connection import get_connection
from core.models import MeiOrder, MeiOrderOutsource, MeiSupplier


def create_supplier(supplier: MeiSupplier) -> MeiSupplier:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO mei_suppliers (profile_id, name, document, notes) VALUES (?, ?, ?, ?)",
        (supplier.profile_id, supplier.name.strip(), supplier.document, supplier.notes),
    )
    supplier.id = cursor.lastrowid
    conn.commit()
    conn.close()
    return supplier


def get_suppliers(profile_id: int) -> list[MeiSupplier]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM mei_suppliers WHERE profile_id = ? ORDER BY name",
        (profile_id,),
    ).fetchall()
    conn.close()
    return [
        MeiSupplier(
            id=r["id"],
            profile_id=r["profile_id"],
            name=r["name"],
            document=r["document"],
            notes=r["notes"],
        )
        for r in rows
    ]


def create_order(order: MeiOrder) -> MeiOrder:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO mei_orders (profile_id, client_id, reference, revenue_amount, order_date, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order.profile_id,
            order.client_id,
            order.reference.strip(),
            float(order.revenue_amount),
            order.order_date.isoformat(),
            order.status,
            order.notes,
        ),
    )
    order.id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order


def get_orders(profile_id: int, year: int | None = None, month: int | None = None) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        query = "SELECT * FROM mei_orders WHERE profile_id = ?"
        params: list[Any] = [profile_id]
        if year is not None and month is not None:
            start = f"{year}-{month:02d}-01"
            end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
            query += " AND order_date >= ? AND order_date < ?"
            params.extend([start, end])
        elif year is not None:
            query += " AND order_date >= ? AND order_date < ?"
            params.extend([f"{year}-01-01", f"{year + 1}-01-01"])
        elif month is not None:
            query += " AND strftime('%m', order_date) = ?"
            params.append(f"{month:02d}")
        query += " ORDER BY order_date DESC, id DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_order(order_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM mei_orders WHERE id = ?", (order_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def mark_order_done(order_id: int) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE mei_orders SET status = 'done' WHERE id = ?", (order_id,))
        ok = cursor.rowcount > 0
        conn.commit()
        return ok
    finally:
        conn.close()


def get_outsource_for_orders(order_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    """Bulk fetch outsource lines grouped by order_id."""
    ids = [int(oid) for oid in dict.fromkeys(order_ids) if oid is not None]
    if not ids:
        return {}
    placeholders = ",".join("?" * len(ids))
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT o.*, s.name AS supplier_name
            FROM mei_order_outsource o
            JOIN mei_suppliers s ON s.id = o.supplier_id
            WHERE o.order_id IN ({placeholders})
            ORDER BY o.id
            """,
            ids,
        ).fetchall()
    finally:
        conn.close()
    grouped: dict[int, list[dict[str, Any]]] = {oid: [] for oid in ids}
    for r in rows:
        item = dict(r)
        grouped.setdefault(int(item["order_id"]), []).append(item)
    return grouped


def add_outsource(line: MeiOrderOutsource) -> MeiOrderOutsource:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO mei_order_outsource (order_id, supplier_id, amount, sent_date, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            line.order_id,
            line.supplier_id,
            float(line.amount),
            line.sent_date.isoformat() if line.sent_date else None,
            line.notes,
        ),
    )
    line.id = cursor.lastrowid
    conn.commit()
    conn.close()
    return line


def get_outsource_for_order(order_id: int) -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT o.*, s.name AS supplier_name
        FROM mei_order_outsource o
        JOIN mei_suppliers s ON s.id = o.supplier_id
        WHERE o.order_id = ?
        ORDER BY o.id
        """,
        (order_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_outsource_line(line_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM mei_order_outsource WHERE id = ?", (line_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _outsourcing_expense_category_id() -> int | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id FROM categories
            WHERE (slug = 'mei_materials' OR name = ?) AND type = 'expense'
            ORDER BY CASE WHEN slug = 'mei_materials' THEN 0 ELSE 1 END
            LIMIT 1
            """,
            ("Materiais e Insumos",),
        ).fetchone()
        return int(row["id"]) if row else None
    finally:
        conn.close()


def pay_outsource_line(
    profile_id: int,
    line_id: int,
    payment_date: date | None = None,
) -> int | None:
    from core.db.connection import db_session

    pay = payment_date or date.today()
    with db_session() as conn:
        line = conn.execute(
            "SELECT * FROM mei_order_outsource WHERE id = ?", (line_id,)
        ).fetchone()
        if not line or line["paid_at"]:
            return None
        order = conn.execute(
            "SELECT * FROM mei_orders WHERE id = ?", (int(line["order_id"]),)
        ).fetchone()
        if not order or order["profile_id"] != profile_id:
            return None
        cat_id = _outsourcing_expense_category_id()
        if not cat_id:
            return None
        supplier = conn_supplier_name(int(line["supplier_id"]))
        ref = order["reference"] or ""
        try:
            cur = conn.execute(
                """
                INSERT INTO transactions (
                    profile_id, date, description, amount, category_id, type, notes
                )
                VALUES (?, ?, ?, ?, ?, 'expense', ?)
                """,
                (
                    profile_id,
                    pay.isoformat(),
                    f"Terceiro {supplier} · pedido {ref}".strip(),
                    float(Decimal(str(line["amount"]))),
                    cat_id,
                    f"outsource:{line_id}",
                ),
            )
            tx_id = cur.lastrowid
            upd = conn.execute(
                """
                UPDATE mei_order_outsource
                SET paid_at = ?, transaction_id = ?
                WHERE id = ? AND paid_at IS NULL
                """,
                (pay.isoformat(), tx_id, line_id),
            )
            if upd.rowcount == 0:
                conn.rollback()
                return None
            conn.commit()
            return tx_id
        except Exception:
            conn.rollback()
            raise


def conn_supplier_name(supplier_id: int) -> str:
    conn = get_connection()
    row = conn.execute("SELECT name FROM mei_suppliers WHERE id = ?", (supplier_id,)).fetchone()
    conn.close()
    return row["name"] if row else "terceiro"


def list_unpaid_outsource(profile_id: int, year: int, month: int) -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT o.id AS line_id, o.amount, o.sent_date, o.order_id,
               ord.reference, ord.order_date, s.id AS supplier_id, s.name AS supplier_name
        FROM mei_order_outsource o
        JOIN mei_orders ord ON ord.id = o.order_id
        JOIN mei_suppliers s ON s.id = o.supplier_id
        WHERE ord.profile_id = ?
          AND o.paid_at IS NULL
          AND strftime('%Y', ord.order_date) = ?
          AND strftime('%m', ord.order_date) = ?
        ORDER BY s.name, ord.order_date
        """,
        (profile_id, str(year), f"{month:02d}"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]