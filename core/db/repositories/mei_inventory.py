"""MEI light inventory — products and stock movements."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from core.db.connection import get_connection
from core.models import MeiProduct, MeiStockMovement


def create_product(product: MeiProduct) -> MeiProduct:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO mei_products (
            profile_id, name, sku, unit_price, cost_price,
            stock_qty, low_stock_threshold, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product.profile_id,
            product.name.strip(),
            product.sku,
            float(product.unit_price),
            float(product.cost_price) if product.cost_price is not None else None,
            float(product.stock_qty),
            float(product.low_stock_threshold) if product.low_stock_threshold is not None else None,
            product.notes,
        ),
    )
    product.id = cursor.lastrowid
    conn.commit()
    conn.close()
    return product


def get_products(profile_id: int) -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM mei_products WHERE profile_id = ? ORDER BY name",
        (profile_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product(product_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM mei_products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _expense_category_id() -> int | None:
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


def record_movement(
    movement: MeiStockMovement,
    *,
    profile_id: int,
    create_purchase_expense: bool = False,
) -> MeiStockMovement | None:
    from core.db.connection import db_session

    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM mei_products WHERE id = ?", (movement.product_id,)
        ).fetchone()
        if not row or row["profile_id"] != profile_id:
            return None
        product = dict(row)
        current = Decimal(str(product["stock_qty"]))

        if movement.movement_type == "in":
            new_qty = current + movement.quantity
        elif movement.movement_type == "out":
            new_qty = current - movement.quantity
        else:
            new_qty = movement.quantity

        if new_qty < 0:
            return None

        try:
            tx_id: int | None = None
            if create_purchase_expense and movement.movement_type == "in":
                cat_id = _expense_category_id()
                unit = movement.unit_cost or Decimal(str(product.get("cost_price") or 0))
                if cat_id and unit > 0:
                    total = unit * movement.quantity
                    cur_tx = conn.execute(
                        """
                        INSERT INTO transactions (
                            profile_id, date, description, amount, category_id, type, notes
                        )
                        VALUES (?, ?, ?, ?, ?, 'expense', ?)
                        """,
                        (
                            profile_id,
                            movement.movement_date.isoformat(),
                            f"Compra estoque {product.get('name', '')}".strip(),
                            float(total),
                            cat_id,
                            f"stock_in:{movement.product_id}",
                        ),
                    )
                    tx_id = cur_tx.lastrowid

            conn.execute(
                "UPDATE mei_products SET stock_qty = ? WHERE id = ?",
                (float(new_qty), movement.product_id),
            )
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO mei_stock_movements (
                    product_id, movement_type, quantity, unit_cost,
                    movement_date, notes, transaction_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    movement.product_id,
                    movement.movement_type,
                    float(movement.quantity),
                    float(movement.unit_cost) if movement.unit_cost is not None else None,
                    movement.movement_date.isoformat(),
                    movement.notes,
                    tx_id,
                ),
            )
            movement.id = cursor.lastrowid
            movement.transaction_id = tx_id
            conn.commit()
            return movement
        except Exception:
            conn.rollback()
            raise