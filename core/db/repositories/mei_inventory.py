"""MEI light inventory — products and stock movements."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from core.db.connection import get_connection
from core.models import MeiProduct, MeiStockMovement, Transaction, TransactionType


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
    row = conn.execute(
        "SELECT id FROM categories WHERE name = ? AND type = 'expense' LIMIT 1",
        ("Materiais e Insumos",),
    ).fetchone()
    conn.close()
    return int(row["id"]) if row else None


def _apply_stock_delta(product_id: int, delta: Decimal) -> Decimal | None:
    conn = get_connection()
    row = conn.execute("SELECT stock_qty FROM mei_products WHERE id = ?", (product_id,)).fetchone()
    if not row:
        conn.close()
        return None
    new_qty = Decimal(str(row["stock_qty"])) + delta
    if new_qty < 0:
        conn.close()
        return None
    conn.execute(
        "UPDATE mei_products SET stock_qty = ? WHERE id = ?",
        (float(new_qty), product_id),
    )
    conn.commit()
    conn.close()
    return new_qty


def record_movement(
    movement: MeiStockMovement,
    *,
    profile_id: int,
    create_purchase_expense: bool = False,
) -> MeiStockMovement | None:
    product = get_product(movement.product_id)
    if not product or product["profile_id"] != profile_id:
        return None

    if movement.movement_type == "in":
        delta = movement.quantity
    elif movement.movement_type == "out":
        delta = -movement.quantity
    else:
        current = Decimal(str(product["stock_qty"]))
        delta = movement.quantity - current

    tx_id: int | None = None
    if create_purchase_expense and movement.movement_type == "in":
        cat_id = _expense_category_id()
        unit = movement.unit_cost or Decimal(str(product.get("cost_price") or 0))
        if cat_id and unit > 0:
            from core.db.repositories.transactions import create_transaction

            total = unit * movement.quantity
            tx = create_transaction(
                Transaction(
                    profile_id=profile_id,
                    date=movement.movement_date,
                    description=f"Compra estoque {product.get('name', '')}".strip(),
                    amount=total,
                    category_id=cat_id,
                    type=TransactionType.EXPENSE,
                    notes=f"stock_in:{movement.product_id}",
                )
            )
            tx_id = tx.id

    new_qty = _apply_stock_delta(movement.product_id, delta)
    if new_qty is None:
        return None

    conn = get_connection()
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
    conn.close()
    return movement


def get_recent_movements(profile_id: int, limit: int = 20) -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT m.*, p.name AS product_name
        FROM mei_stock_movements m
        JOIN mei_products p ON p.id = m.product_id
        WHERE p.profile_id = ?
        ORDER BY m.movement_date DESC, m.id DESC
        LIMIT ?
        """,
        (profile_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]