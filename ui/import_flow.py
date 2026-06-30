"""Statement import UI — local-only processing (LGPD). No invoice data sent to AI."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from core.engine.budget_alerts import check_import_budget_impacts
from core.domain.value_objects.money import format_brl
from core.import_parsers.models import ParseResult
from core.services.import_service import commit_import, prepare_import
from core.db.repositories.categories import get_categories_for_profile

_ALLOWED_EXTENSIONS = ["csv", "ofx", "qfx", "pdf"]

_PRIVACY_NOTICE = (
    "Processamento 100% local. O conteúdo da fatura (nome, CPF, cartão, estabelecimentos) "
    "não é enviado à internet nem à IA."
)


def _resolve_profile_id(app) -> int | None:
    return app.get_view_profile_id() or (app.profiles[0].id if app.profiles else None)


def _read_picked_file(selected: ft.FilePickerFile) -> tuple[bytes, str] | None:
    if selected.path:
        return Path(selected.path).read_bytes(), selected.name
    if selected.bytes:
        return bytes(selected.bytes), selected.name
    return None


async def pick_statement_file() -> tuple[bytes, str] | None:
    """Open native file dialog (Flet 0.85+ async API)."""
    files = await ft.FilePicker().pick_files(
        allow_multiple=False,
        file_type=ft.FilePickerFileType.CUSTOM,
        allowed_extensions=_ALLOWED_EXTENSIONS,
    )
    if not files:
        return None
    return _read_picked_file(files[0])


def process_import_bytes(app, content: bytes, filename: str):
    """Parse file locally and open preview modal."""
    profile_id = _resolve_profile_id(app)
    if not profile_id:
        app.show_snack("Crie um perfil antes de importar", success=False)
        return

    try:
        result = prepare_import(content, filename, profile_id)
        preferred_card_id = getattr(app, "_import_preferred_card_id", None)
        if preferred_card_id:
            result.credit_card_id = preferred_card_id
        if not result.lines:
            app.show_snack("Nenhum lançamento encontrado no arquivo", success=False)
            return
        show_import_preview(app, result, profile_id)
    except Exception as ex:
        app.show_snack(f"Erro ao importar: {ex}", success=False)


def show_import_preview(app, result: ParseResult, profile_id: int):
    categories = get_categories_for_profile(profile_id)
    cat_by_id = {c.id: c for c in categories}
    budget_warnings = check_import_budget_impacts(profile_id, result.lines)

    summary = ft.Text(
        f"{result.institution} • {len(result.lines)} lançamentos detectados",
        color=ft.Colors.WHITE,
        weight=ft.FontWeight.W_600,
    )
    if result.warnings:
        summary.value += f" ({len(result.warnings)} avisos)"

    meta_bits = []
    if result.bank:
        meta_bits.append(f"Banco: {result.bank}")
    if result.card_network:
        meta_bits.append(f"Bandeira: {result.card_network}")
    if result.card_last_four:
        meta_bits.append(f"Final: •••• {result.card_last_four}")
    if result.period_label:
        meta_bits.append(f"Período: {result.period_label}")
    if result.statement_due_date:
        meta_bits.append(f"Vencimento: {result.statement_due_date.strftime('%d/%m/%Y')}")
    if result.statement_total is not None:
        meta_bits.append(f"Total fatura: {format_brl(result.statement_total)}")
    meta_text = ft.Text(" • ".join(meta_bits), size=11, color=ft.Colors.GREY_400) if meta_bits else ft.Container()

    preview_list = ft.Column(spacing=6, height=320, scroll=ft.ScrollMode.AUTO)

    def rebuild_preview():
        preview_list.controls.clear()
        for line in result.lines:
            cat = cat_by_id.get(line.suggested_category_id)
            cat_label = f"{cat.icon or ''} {cat.name}" if cat else "—"
            tipo = "Receita" if line.tx_type.value == "income" else "Despesa"
            color = "#22C55E" if line.tx_type.value == "income" else "#EF4444"
            if line.is_duplicate:
                color = ft.Colors.AMBER_200
            parcel = ""
            if line.installment_number and line.installment_total:
                parcel = f" • {line.installment_number}/{line.installment_total}"
            dupe = " • duplicata" if line.is_duplicate else ""

            def toggle(ev, ln=line):
                ln.selected = ev.control.value

            preview_list.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Checkbox(value=line.selected, on_change=toggle),
                            ft.Column(
                                [
                                    ft.Text(line.description[:48], size=12, color=ft.Colors.WHITE),
                                    ft.Text(
                                        f"{line.date.strftime('%d/%m/%Y')} • {cat_label} • {tipo}{parcel}{dupe}",
                                        size=10,
                                        color=ft.Colors.AMBER_200 if line.is_duplicate else ft.Colors.GREY_400,
                                    ),
                                ],
                                expand=True,
                                spacing=2,
                            ),
                            ft.Text(format_brl(line.amount), size=12, color=color),
                        ],
                        spacing=8,
                    ),
                    padding=8,
                    bgcolor="#292524" if line.is_duplicate else "#0F172A",
                    border_radius=8,
                )
            )

    rebuild_preview()

    def confirm_import(_):
        selected = [ln for ln in result.lines if ln.selected]
        if not selected:
            app.show_snack("Selecione ao menos um lançamento", success=False)
            return
        card_id = result.credit_card_id or getattr(app, "_import_preferred_card_id", None)
        count = commit_import(selected, profile_id, result.filename, credit_card_id=card_id)
        app.close_modal()
        app.show_snack(f"{count} lançamentos importados de {result.institution}!")
        app.refresh_current_view()

    warnings_parts = []
    if result.warnings:
        warnings_parts.extend(result.warnings[:5])
    if budget_warnings:
        warnings_parts.extend(budget_warnings[:3])

    warnings_text = None
    if warnings_parts:
        warnings_text = ft.Text("\n".join(warnings_parts), size=10, color=ft.Colors.AMBER_200)

    content = ft.Column(
        [
            summary,
            meta_text,
            ft.Text(
                "Revise antes de confirmar. Nada é salvo até você clicar em Importar.",
                size=11,
                color=ft.Colors.GREY_400,
            ),
            warnings_text or ft.Container(),
            preview_list,
            ft.Row(
                [
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _: app.close_modal(),
                        style=ft.ButtonStyle(color=ft.Colors.WHITE),
                    ),
                    ft.ElevatedButton(
                        "Importar selecionados",
                        icon=ft.Icons.CHECK,
                        on_click=confirm_import,
                        style=ft.ButtonStyle(bgcolor="#14B8A6", color=ft.Colors.WHITE),
                    ),
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
        ],
        spacing=10,
        tight=True,
    )
    app.show_modal(content, title=f"Preview — {result.institution}")


def _privacy_banner() -> ft.Container:
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.LOCK_OUTLINE, size=18, color="#14B8A6"),
                ft.Text(_PRIVACY_NOTICE, size=11, color=ft.Colors.GREY_400, expand=True),
            ],
            spacing=8,
        ),
        padding=ft.Padding(left=12, top=10, right=12, bottom=10),
        bgcolor="#0F172A",
        border_radius=8,
        border=ft.Border.all(1, "#334155"),
    )


def show_import_drop_zone(app):
    """Modal to select a statement file (click). Parsing stays on device."""

    async def handle_pick(_=None):
        picked = await pick_statement_file()
        if not picked:
            return
        content, filename = picked
        app.close_modal()
        process_import_bytes(app, content, filename)

    drop_zone = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.CLOUD_UPLOAD, size=48, color="#14B8A6"),
                ft.Text(
                    "Clique para selecionar a fatura",
                    size=14,
                    color=ft.Colors.WHITE,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Text(
                    "CSV, OFX, QFX ou PDF — Nubank, Inter, C6, Itaú, Bradesco, BTG",
                    size=11,
                    color=ft.Colors.GREY_400,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        alignment=ft.Alignment.CENTER,
        width=480,
        height=160,
        border=ft.Border.all(2, "#334155"),
        border_radius=12,
        bgcolor="#0F172A",
        ink=True,
        on_click=handle_pick,
    )

    content = ft.Column(
        [
            _privacy_banner(),
            ft.Text(
                "O sistema detecta a instituição pelo cabeçalho do arquivo.",
                size=12,
                color=ft.Colors.GREY_400,
            ),
            drop_zone,
            ft.Row(
                [
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _: app.close_modal(),
                        style=ft.ButtonStyle(color=ft.Colors.WHITE),
                    ),
                    ft.ElevatedButton(
                        "Selecionar arquivo",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=handle_pick,
                        style=ft.ButtonStyle(bgcolor="#14B8A6", color=ft.Colors.WHITE),
                    ),
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
        ],
        spacing=12,
        tight=True,
    )
    app.show_modal(content, title="Importar Fatura")


def open_import_flow(app, preferred_card_id: int | None = None):
    """Open import modal (sync entry point for buttons)."""
    app._import_preferred_card_id = preferred_card_id
    show_import_drop_zone(app)