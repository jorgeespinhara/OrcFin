"""Transaction audit detail modal."""

from __future__ import annotations

import flet as ft

from core.change_log import format_change_line, list_changes_for_entity
from core.db.repositories.import_batches import get_import_batch
from core.domain.value_objects.money import format_brl
from core.engine.categorization import strip_system_notes
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

    lines = [
        ft.Text(tx.description, size=15, weight=ft.FontWeight.W_600, color=c.text_primary),
        ft.Text(
            f"{tx.date.strftime('%d/%m/%Y')} · "
            f"{'Receita' if tx.type == TransactionType.INCOME else 'Despesa'} · "
            f"{format_brl(tx.amount)}",
            size=12,
            color=c.text_secondary,
        ),
        ft.Divider(color=c.border),
        ft.Text("Origem", size=12, weight=ft.FontWeight.W_600, color=c.text_muted),
        ft.Text(f"{origin['kind'].capitalize()}: {origin['detail']}", size=12, color=c.text_primary),
    ]
    if tx.created_at:
        lines.append(ft.Text(f"Criado em: {tx.created_at}", size=11, color=c.text_muted))
    if tx.import_confidence:
        lines.append(ft.Text(f"Confiança na importação: {tx.import_confidence}", size=11, color=c.text_muted))
    if batch:
        when = batch.get("created_at") or ""
        lines.append(
            ft.Text(
                f"Lote #{batch['id']} · {batch.get('filename', '')} · {when}",
                size=11,
                color=c.text_muted,
            )
        )
    if user_notes:
        lines.extend([
            ft.Text("Notas", size=12, weight=ft.FontWeight.W_600, color=c.text_muted),
            ft.Text(user_notes, size=12, color=c.text_secondary),
        ])
    if changes:
        lines.append(ft.Text("Alterações registradas", size=12, weight=ft.FontWeight.W_600, color=c.text_muted))
        for row in changes[:5]:
            lines.append(ft.Text(format_change_line(row), size=10, color=c.text_muted))
            if row.get("old_value_json") or row.get("new_value_json"):
                bits = []
                if row.get("old_value_json"):
                    bits.append(f"antes: {row['old_value_json'][:120]}")
                if row.get("new_value_json"):
                    bits.append(f"depois: {row['new_value_json'][:120]}")
                lines.append(ft.Text(" · ".join(bits), size=9, color=c.text_muted))

    view.app.show_modal(
        ft.Column(
            [
                *lines,
                ft.Row(
                    [
                        ft.TextButton(
                            "Fechar",
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
        title="Detalhes do lançamento",
    )