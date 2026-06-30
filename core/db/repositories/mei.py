"""MEI profile, clients, invoices, and obligations."""

import sqlite3
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.db.connection import get_connection
from core.db.repositories.profiles import get_all_profiles
from core.models import MeiClient, MeiConfig, MeiInvoice, Profile, ProfileType

MEI_CATEGORY_SEED = [
    ("Receita MEI", "income", "💼", 0),
    ("DAS / Impostos MEI", "expense", "📋", 0),
    ("Materiais e Insumos", "expense", "📦", 1),
    ("Despesas Administrativas MEI", "expense", "🗂️", 1),
    ("Equipamentos MEI", "expense", "🛠️", 0),
    ("Marketing MEI", "expense", "📣", 1),
]


def _seed_mei_categories(cursor: sqlite3.Cursor) -> None:
    for name, type_, icon, deductible in MEI_CATEGORY_SEED:
        cursor.execute(
            "SELECT id FROM categories WHERE name = ? AND type = ?",
            (name, type_),
        )
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO categories (name, type, icon, is_mei_deductible) VALUES (?, ?, ?, ?)",
                (name, type_, icon, deductible),
            )


def get_mei_profiles(active_only: bool = True) -> List[Profile]:
    profiles = get_all_profiles(active_only=active_only)
    return [p for p in profiles if p.profile_type == ProfileType.MEI]


def get_mei_profile() -> Optional[Profile]:
    mei_list = get_mei_profiles()
    return mei_list[0] if mei_list else None


def insert_mei_profile(
    name: str,
    razao_social: str,
    cnpj: str,
    activity_type: str = "servico",
    color: str = "#F59E0B",
    annual_limit: float = 81000.0,
) -> Tuple[Profile, MeiConfig]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO profiles (name, color, profile_type) VALUES (?, ?, 'mei')",
        (name, color),
    )
    profile_id = cursor.lastrowid
    _seed_mei_categories(cursor)
    cursor.execute(
        """
        INSERT INTO mei_config (profile_id, razao_social, cnpj, activity_type, annual_limit)
        VALUES (?, ?, ?, ?, ?)
        """,
        (profile_id, razao_social.strip(), cnpj.strip(), activity_type, annual_limit),
    )
    conn.commit()
    conn.close()
    profile = Profile(id=profile_id, name=name, color=color, profile_type=ProfileType.MEI)
    config = MeiConfig(
        profile_id=profile_id,
        razao_social=razao_social.strip(),
        cnpj=cnpj.strip(),
        activity_type=activity_type,
        annual_limit=annual_limit,
    )
    return profile, config


def get_mei_config(profile_id: int) -> Optional[MeiConfig]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM mei_config WHERE profile_id = ?",
        (profile_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return MeiConfig(
        profile_id=row["profile_id"],
        razao_social=row["razao_social"],
        cnpj=row["cnpj"],
        activity_type=row["activity_type"],
        custom_das_amount=row["custom_das_amount"],
        annual_limit=row["annual_limit"] or 81000.0,
        das_day=row["das_day"] or 20,
    )


def update_mei_config(config: MeiConfig) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE mei_config SET
            razao_social = ?, cnpj = ?, activity_type = ?,
            custom_das_amount = ?, annual_limit = ?, das_day = ?
        WHERE profile_id = ?
        """,
        (
            config.razao_social,
            config.cnpj,
            config.activity_type,
            config.custom_das_amount,
            config.annual_limit,
            config.das_day,
            config.profile_id,
        ),
    )
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def get_mei_deductible_category_ids() -> List[int]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id FROM categories WHERE is_mei_deductible = 1"
    ).fetchall()
    conn.close()
    return [r["id"] for r in rows]


def create_mei_client(client: MeiClient) -> MeiClient:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO mei_clients (profile_id, name, document, notes)
        VALUES (?, ?, ?, ?)
        """,
        (client.profile_id, client.name.strip(), client.document, client.notes),
    )
    client.id = cursor.lastrowid
    conn.commit()
    conn.close()
    return client


def get_mei_clients(profile_id: int) -> List[MeiClient]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM mei_clients WHERE profile_id = ? ORDER BY name",
        (profile_id,),
    ).fetchall()
    conn.close()
    return [
        MeiClient(
            id=r["id"],
            profile_id=r["profile_id"],
            name=r["name"],
            document=r["document"],
            notes=r["notes"],
        )
        for r in rows
    ]


def delete_mei_client(client_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mei_clients WHERE id = ?", (client_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def create_mei_invoice(invoice: MeiInvoice) -> MeiInvoice:
    conn = get_connection()
    cursor = conn.cursor()
    due = invoice.due_date or invoice.issue_date
    cursor.execute(
        """
        INSERT INTO mei_invoices
        (profile_id, invoice_number, client_id, tomador_name, amount, issue_date, due_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invoice.profile_id,
            invoice.invoice_number.strip(),
            invoice.client_id,
            invoice.tomador_name,
            float(invoice.amount),
            invoice.issue_date.isoformat(),
            due.isoformat(),
            invoice.notes,
        ),
    )
    invoice.id = cursor.lastrowid
    conn.commit()
    conn.close()
    return invoice


def get_mei_invoice(invoice_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM mei_invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def receive_invoice_payment(
    profile_id: int,
    invoice_id: int,
    income_category_id: int,
    payment_date: Optional[date] = None,
) -> Optional[int]:
    """Mark NF paid and create matching income transaction."""
    from core.db.repositories.transactions import create_transaction
    from core.models import Transaction, TransactionType

    inv = get_mei_invoice(invoice_id)
    if not inv or inv.get("paid_at"):
        return None
    pay = payment_date or date.today()
    tx = create_transaction(
        Transaction(
            profile_id=profile_id,
            date=pay,
            description=f"Recebimento NF {inv.get('invoice_number', '')}".strip(),
            amount=Decimal(str(inv["amount"])),
            category_id=income_category_id,
            type=TransactionType.INCOME,
            notes=f"nf:{invoice_id}",
        )
    )
    mark_invoice_paid(invoice_id, pay, tx.id)
    return tx.id


def mark_invoice_paid(
    invoice_id: int,
    paid_at: Optional[date] = None,
    transaction_id: Optional[int] = None,
) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    payment_date = (paid_at or date.today()).isoformat()
    cursor.execute(
        """
        UPDATE mei_invoices
        SET paid_at = ?, transaction_id = COALESCE(?, transaction_id)
        WHERE id = ? AND paid_at IS NULL
        """,
        (payment_date, transaction_id, invoice_id),
    )
    ok = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def get_mei_invoices(profile_id: int, year: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    query = "SELECT * FROM mei_invoices WHERE profile_id = ?"
    params: List[Any] = [profile_id]
    if year is not None:
        query += " AND strftime('%Y', issue_date) = ?"
        params.append(str(year))
    query += " ORDER BY issue_date DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_mei_invoice(invoice_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mei_invoices WHERE id = ?", (invoice_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def get_das_category_id() -> Optional[int]:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM categories WHERE name = 'DAS / Impostos MEI' AND type = 'expense' LIMIT 1"
    ).fetchone()
    conn.close()
    return row["id"] if row else None