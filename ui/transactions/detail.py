"""Transaction audit detail modal."""

from __future__ import annotations

import flet as ft

from core.change_log import format_change_line, list_changes_for_entity
from core.db.repositories.import_batches import get_import_batch
from core.domain.value_objects.money import format_brl
from core.engine.categorization import strip_system_notes
from core.i18n import t
from core.models import Transaction, TransactionType
from core.transaction_origin import describe_transaction_origin
from ui.theme import active as theme_colors


def show_transaction_detail(view, tx: Transaction) -> None:
    if tx.id is None:
        return
    c = theme_colors()
    origin = describe_transaction_origin(tx)
    batch = get_import_batch(origin["batch_id"]) if origin.get("batch_id") else None
    user_notes = strip_system_notes(tx.notes)
    changes = list_changes_for_entity("transaction", tx.id)

    type_label = t("tx.income") if tx.type == TransactionType.INCOME else t("tx.expense")
    lines = [
        ft.Text(tx.description, size=15, weight=ft.FontWeight.W_600, color=c.text_primary),
        ft.Text(
            t(
                "tx.detail.meta",
                date=tx.date.strftime("%d/%m/%Y"),
                type=type_label,
                amount=format_brl(tx.amount),
            ),
            size=12,
            color=c.text_secondary,
        ),
        ft.Divider(color=c.border),
        ft.Text(t("tx.origin"), size=12, weight=ft.FontWeight.W_600, color=c.text_muted),
        ft.Text(
            t("tx.detail.origin_line", kind=str(origin["kind"]).capitalize(), detail=origin["detail"]),
            size=12,
            color=c.text_primary,
        ),
    ]
    if tx.created_at:
        lines.append(ft.Text(t("tx.detail.created", when=tx.created_at), size=11, color=c.text_muted))
    if tx.import_confidence:
        lines.append(
            ft.Text(
                t("tx.detail.import_confidence", value=tx.import_confidence),
                size=11,
                color=c.text_muted,
            )
        )
    if batch:
        when = batch.get("created_at") or ""
        lines.append(
            ft.Text(
                t(
                    "tx.detail.batch",
                    id=batch["id"],
                    filename=batch.get("filename", ""),
                    when=when,
                ),
                size=11,
                color=c.text_muted,
            )
        )
    if user_notes:
        lines.extend([
            ft.Text(t("tx.notes"), size=12, weight=ft.FontWeight.W_600, color=c.text_muted),
            ft.Text(user_notes, size=12, color=c.text_secondary),
        ])
    if changes:
        lines.append(ft.Text(t("tx.detail.changes"), size=12, weight=ft.FontWeight.W_600, color=c.text_muted))
        for row in changes[:5]:
            lines.append(ft.Text(format_change_line(row), size=10, color=c.text_muted))
            if row.get("old_value_json") or row.get("new_value_json"):
                bits = []
                if row.get("old_value_json"):
                    bits.append(t("tx.detail.before", value=row["old_value_json"][:120]))
                if row.get("new_value_json"):
                    bits.append(t("tx.detail.after", value=row["new_value_json"][:120]))
                lines.append(ft.Text(" · ".join(bits), size=9, color=c.text_muted))

    view.app.show_modal(
        ft.Column(
            [
                *lines,
                ft.Row(
                    [
                        ft.TextButton(
                            t("common.close"),
                            on_click=lambda _: view.app.close_modal(),
                            style=ft.ButtonStyle(color=c.text_primary),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=8,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        title=t("tx.detail.title"),
    )
