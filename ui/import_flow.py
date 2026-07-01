"""Statement import UI — local-only processing (LGPD). No invoice data sent to AI."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from core.copy import EMPTY_CELL
from core.engine.budget_alerts import check_import_budget_impacts
from core.domain.value_objects.money import format_brl
from core.import_parsers.models import ParseResult
from core.db.repositories.import_batches import (
    STATUS_ROLLED_BACK,
    count_batch_transactions,
    list_import_batches,
    rollback_import_batch,
)
from core.db.repositories.import_templates import list_templates, save_template
from core.engine.categorization import create_rule
from core.import_parsers.generic_csv import probe_csv_columns, template_to_column_map
from core.services.import_service import commit_import, prepare_import
from core.db.repositories.categories import get_categories_for_profile

_ALLOWED_EXTENSIONS = ["csv", "ofx", "qfx", "pdf"]

_CONF_LABELS = {
    "high": "alta",
    "medium": "média",
    "low": "baixa",
    "review": "revisar",
}

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


def process_import_bytes(
    app,
    content: bytes,
    filename: str,
    *,
    column_map: dict[str, str] | None = None,
):
    """Parse file locally and open preview modal."""
    profile_id = _resolve_profile_id(app)
    if not profile_id:
        app.show_snack("Crie um perfil antes de importar", success=False)
        return

    try:
        result = prepare_import(content, filename, profile_id, column_map=column_map)
        preferred_card_id = getattr(app, "_import_preferred_card_id", None)
        if preferred_card_id:
            result.credit_card_id = preferred_card_id
        if not result.lines:
            app.show_snack("Nenhum lançamento encontrado no arquivo", success=False)
            return
        show_import_preview(app, result, profile_id)
    except Exception as ex:
        if filename.lower().endswith(".csv") and column_map is None:
            show_csv_mapper(app, content, filename, profile_id, hint=str(ex))
            return
        app.show_snack(f"Erro ao importar: {ex}", success=False)


def _column_dropdown(label: str, columns: list[str], value: str | None) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=value or (columns[0] if columns else None),
        options=[ft.dropdown.Option(c, c) for c in columns],
        width=200,
        dense=True,
    )


def show_csv_mapper(app, content: bytes, filename: str, profile_id: int, *, hint: str = ""):
    """Map CSV columns manually and optionally save a reusable template."""
    try:
        columns, detected_sep = probe_csv_columns(content)
    except ValueError as ex:
        app.show_snack(str(ex), success=False)
        return

    templates = list_templates(profile_id)

    date_dd = _column_dropdown("Data", columns, columns[0])
    desc_dd = _column_dropdown("Descrição", columns, columns[1] if len(columns) > 1 else columns[0])
    amount_dd = _column_dropdown("Valor", columns, columns[-1])
    debit_dd = _column_dropdown("Débito (opcional)", [""] + columns, "")
    credit_dd = _column_dropdown("Crédito (opcional)", [""] + columns, "")
    sep_dd = ft.Dropdown(
        label="Separador",
        value=detected_sep or ";",
        options=[
            ft.dropdown.Option(";", ";"),
            ft.dropdown.Option(",", ","),
            ft.dropdown.Option("\\t", "Tab"),
        ],
        width=120,
        dense=True,
    )
    template_dd = ft.Dropdown(
        label="Template salvo",
        value="",
        options=[ft.dropdown.Option("", "Nenhum")] + [
            ft.dropdown.Option(str(t["id"]), t["name"]) for t in templates
        ],
        width=220,
        dense=True,
    )
    template_name = ft.TextField(label="Salvar como template", hint_text="Opcional", width=220)
    status = ft.Text(hint or "Indique as colunas do seu extrato.", size=11, color=ft.Colors.GREY_400)

    def apply_template(ev):
        tid = ev.control.value
        if not tid:
            return
        row = next((t for t in templates if str(t["id"]) == tid), None)
        if not row:
            return
        cmap = template_to_column_map(row)
        date_dd.value = cmap.get("date_col")
        desc_dd.value = cmap.get("desc_col")
        amount_dd.value = cmap.get("amount_col") or columns[-1]
        debit_dd.value = cmap.get("debit_col") or ""
        credit_dd.value = cmap.get("credit_col") or ""
        if cmap.get("sep"):
            sep_dd.value = cmap["sep"]
        if template_dd.page:
            template_dd.page.update()

    template_dd.on_select = apply_template

    def build_map() -> dict[str, str]:
        sep = sep_dd.value
        if sep == "\\t":
            sep = "\t"
        cmap = {
            "date_col": date_dd.value,
            "desc_col": desc_dd.value,
            "sep": sep or ";",
        }
        if debit_dd.value or credit_dd.value:
            if debit_dd.value:
                cmap["debit_col"] = debit_dd.value
            if credit_dd.value:
                cmap["credit_col"] = credit_dd.value
        else:
            cmap["amount_col"] = amount_dd.value
        return cmap

    def run_preview(_):
        try:
            cmap = build_map()
            if template_name.value and template_name.value.strip():
                save_template(
                    name=template_name.value.strip(),
                    date_col=cmap["date_col"],
                    desc_col=cmap["desc_col"],
                    amount_col=cmap.get("amount_col"),
                    debit_col=cmap.get("debit_col"),
                    credit_col=cmap.get("credit_col"),
                    sep=cmap.get("sep"),
                    profile_id=profile_id,
                )
            app.close_modal()
            process_import_bytes(app, content, filename, column_map=cmap)
        except Exception as ex:
            status.value = str(ex)
            status.color = ft.Colors.AMBER_200
            if status.page:
                status.update()

    content_col = ft.Column(
        [
            status,
            ft.Row([date_dd, desc_dd], spacing=8, wrap=True),
            ft.Row([amount_dd, debit_dd, credit_dd, sep_dd], spacing=8, wrap=True),
            ft.Row([template_dd, template_name], spacing=8, wrap=True),
            ft.Row(
                [
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _: app.close_modal(),
                        style=ft.ButtonStyle(color=ft.Colors.WHITE),
                    ),
                    ft.ElevatedButton(
                        "Prévia com este mapeamento",
                        icon=ft.Icons.PREVIEW,
                        on_click=run_preview,
                        style=ft.ButtonStyle(bgcolor="#14B8A6", color=ft.Colors.WHITE),
                    ),
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
        ],
        spacing=10,
        tight=True,
    )
    app.show_modal(content_col, title=f"Mapear CSV: {filename}")


def _save_rule_from_line(app, result: ParseResult, profile_id: int, categories) -> None:
    line = next((ln for ln in result.lines if ln.selected), None)
    if not line or not line.suggested_category_id:
        app.show_snack("Selecione uma linha com categoria", success=False)
        return
    token = line.description.split()[0][:24] if line.description else ""
    if len(token) < 3:
        app.show_snack("Descrição curta demais para regra", success=False)
        return
    create_rule(token, line.suggested_category_id, profile_id=profile_id)
    app.show_snack(f"Regra criada: {token.upper()}")


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
            cat_label = f"{cat.icon or ''} {cat.name}" if cat else EMPTY_CELL
            tipo = "Receita" if line.tx_type.value == "income" else "Despesa"
            color = "#22C55E" if line.tx_type.value == "income" else "#EF4444"
            if line.is_duplicate:
                color = ft.Colors.AMBER_200
            parcel = ""
            if line.installment_number and line.installment_total:
                parcel = f" • {line.installment_number}/{line.installment_total}"
            dupe = " • duplicata" if line.is_duplicate else ""
            conf = _CONF_LABELS.get(line.confidence, line.confidence)

            def toggle(ev, ln=line):
                ln.selected = ev.control.value

            def pick_cat(ev, ln=line):
                ln.suggested_category_id = int(ev.control.value)

            cat_dd = ft.Dropdown(
                value=str(line.suggested_category_id),
                options=[
                    ft.dropdown.Option(str(c.id), f"{c.icon or ''} {c.name}")
                    for c in categories
                ],
                width=160,
                dense=True,
                on_select=pick_cat,
            )

            preview_list.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Checkbox(value=line.selected, on_change=toggle),
                            ft.Column(
                                [
                                    ft.Text(line.description[:48], size=12, color=ft.Colors.WHITE),
                                    ft.Text(
                                        f"{line.date.strftime('%d/%m/%Y')} • {tipo}{parcel}{dupe} • conf. {conf}",
                                        size=10,
                                        color=ft.Colors.AMBER_200 if line.is_duplicate else ft.Colors.GREY_400,
                                    ),
                                ],
                                expand=True,
                                spacing=2,
                            ),
                            cat_dd,
                            ft.Text(format_brl(line.amount), size=12, color=color),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
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
        count, _batch_id = commit_import(
            result,
            profile_id,
            lines=selected,
            credit_card_id=card_id,
        )
        app.close_modal()
        app.show_snack(
            f"{count} lançamentos importados de {result.institution}. "
            "Você pode desfazer em Histórico de importações."
        )
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
                    ft.OutlinedButton(
                        "Salvar regra (1ª linha)",
                        on_click=lambda _: _save_rule_from_line(app, result, profile_id, categories),
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
    app.show_modal(content, title=f"Prévia: {result.institution}")


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


def _open_history_from_drop_zone(app):
    app.close_modal()
    show_import_history(app)


async def _open_csv_mapper_from_drop_zone(app):
    picked = await pick_statement_file()
    if not picked:
        return
    content, filename = picked
    if not filename.lower().endswith(".csv"):
        app.show_snack("Selecione um arquivo CSV", success=False)
        return
    profile_id = _resolve_profile_id(app)
    if not profile_id:
        app.show_snack("Crie um perfil antes de importar", success=False)
        return
    app.close_modal()
    show_csv_mapper(app, content, filename, profile_id)


def _format_batch_when(created_at: str | None) -> str:
    if not created_at:
        return "n/d"
    text = str(created_at)
    if "T" in text:
        text = text.replace("T", " ")[:16]
    return text


def show_import_history(app, profile_id: int | None = None):
    """List past imports and allow rolling back a batch."""
    pid = profile_id or _resolve_profile_id(app)
    if not pid:
        app.show_snack("Crie um perfil antes de ver o histórico", success=False)
        return

    list_box = ft.Column(spacing=6, height=360, scroll=ft.ScrollMode.AUTO)

    def rebuild():
        batches = list_import_batches(pid, limit=25)
        list_box.controls.clear()
        if not batches:
            list_box.controls.append(
                ft.Text("Nenhuma importação registrada ainda.", size=12, color=ft.Colors.GREY_400)
            )
            return
        for row in batches:
            status = row.get("status") or ""
            rolled = status == STATUS_ROLLED_BACK
            imported = int(row.get("rows_imported") or 0)
            skipped = int(row.get("rows_skipped") or 0)
            label = row.get("filename") or "arquivo"
            parser = row.get("parser_name") or ""
            when = _format_batch_when(row.get("created_at"))
            summary = f"{imported} importados"
            if skipped:
                summary += f", {skipped} ignorados"
            if rolled:
                summary += " · desfeito"

            def make_undo(batch_id: int, batch_row: dict):
                def run_undo(_):
                    remaining = count_batch_transactions(batch_id)
                    if batch_row.get("status") == STATUS_ROLLED_BACK or remaining == 0:
                        app.show_snack("Esta importação já foi desfeita.", success=False)
                        return

                    def confirm(_c):
                        try:
                            removed = rollback_import_batch(batch_id, profile_id=pid)
                            app.close_modal()
                            app.show_snack(f"Importação desfeita ({removed} lançamentos removidos).")
                            app.refresh_current_view()
                            rebuild()
                            if list_box.page:
                                list_box.update()
                        except Exception as ex:
                            app.show_snack(str(ex), success=False)

                    app.show_modal(
                        ft.Column(
                            [
                                ft.Text(
                                    f"Desfazer a importação de {batch_row.get('filename')}?",
                                    size=13,
                                    color=ft.Colors.WHITE,
                                ),
                                ft.Text(
                                    f"Isso remove {remaining} lançamento(s) deste lote. "
                                    "Lançamentos manuais e outras importações não são alterados.",
                                    size=11,
                                    color=ft.Colors.GREY_400,
                                ),
                                ft.Row(
                                    [
                                        ft.TextButton(
                                            "Cancelar",
                                            on_click=lambda _: app.close_modal(),
                                            style=ft.ButtonStyle(color=ft.Colors.WHITE),
                                        ),
                                        ft.ElevatedButton(
                                            "Desfazer importação",
                                            on_click=confirm,
                                            style=ft.ButtonStyle(bgcolor="#EF4444", color=ft.Colors.WHITE),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.END,
                                ),
                            ],
                            spacing=10,
                            tight=True,
                        ),
                        title="Confirmar desfazer",
                    )

                return run_undo

            list_box.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(label, size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                                    ft.Text(
                                        f"{when} · {parser} · {summary}",
                                        size=10,
                                        color=ft.Colors.GREY_400,
                                    ),
                                ],
                                expand=True,
                                spacing=2,
                            ),
                            ft.OutlinedButton(
                                "Desfazer",
                                disabled=rolled or imported == 0,
                                on_click=make_undo(int(row["id"]), row),
                                style=ft.ButtonStyle(color=ft.Colors.WHITE),
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=10,
                    bgcolor="#0F172A",
                    border_radius=8,
                    border=ft.Border.all(1, "#334155"),
                )
            )

    rebuild()

    content = ft.Column(
        [
            ft.Text(
                "Cada importação confirmada fica registrada como um lote. "
                "Desfazer remove só os lançamentos daquele arquivo.",
                size=11,
                color=ft.Colors.GREY_400,
            ),
            list_box,
            ft.Row(
                [
                    ft.TextButton(
                        "Fechar",
                        on_click=lambda _: app.close_modal(),
                        style=ft.ButtonStyle(color=ft.Colors.WHITE),
                    ),
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
        ],
        spacing=10,
        tight=True,
    )
    app.show_modal(content, title="Histórico de importações")


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
                    "CSV, OFX, QFX ou PDF (Nubank, Inter, C6, Itaú, Bradesco, Santander, Caixa, BTG)",
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
                        "Mapear CSV",
                        icon=ft.Icons.TABLE_CHART,
                        on_click=lambda _: app.page.run_task(_open_csv_mapper_from_drop_zone, app),
                        style=ft.ButtonStyle(color=ft.Colors.WHITE),
                    ),
                    ft.TextButton(
                        "Histórico",
                        icon=ft.Icons.HISTORY,
                        on_click=lambda _: _open_history_from_drop_zone(app),
                        style=ft.ButtonStyle(color=ft.Colors.WHITE),
                    ),
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