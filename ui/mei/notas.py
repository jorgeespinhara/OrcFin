"""MEI Notas e Clientes — com aging de contas a receber."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import flet as ft

from core.copy import EMPTY_CELL
from core.domain.value_objects.money import format_brl
from core.db.repositories.categories import get_categories_for_mode
from core.db.repositories.mei import get_mei_clients, get_mei_invoices, receive_invoice_payment
from core.i18n import t
from core.mei_nfe_xml import import_nfe_xml
from core.mei_receivables import get_receivables_aging
from core.pdf_generator import generate_mei_service_receipt_pdf
from ui.mei.actions import open_invoice_modal, delete_invoice
from ui.mei.components import mei_text, mei_title, section_card
from ui.mei.constants import MEI_ACCENT
from ui.theme import active as theme_colors, primary_button_style
from ui.mei.context import MeiContext, require_mei_ready


class MeiNotasView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.ctx = MeiContext.load()

    def build(self) -> ft.Control:
        if setup := require_mei_ready(self.app, self.ctx):
            return setup

        pid = self.ctx.profile_id
        invoices = get_mei_invoices(pid, year=date.today().year)
        recon = self.ctx.reconciliation
        aging = get_receivables_aging(pid)
        tc = theme_colors()
        align = (
            t("mei.invoices.aligned")
            if recon.get("aligned")
            else t("mei.invoices.divergence", amount=format_brl(abs(recon.get("difference", 0))))
        )

        async def import_xml_click(_=None):
            files = await ft.FilePicker().pick_files(
                allow_multiple=False,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["xml"],
            )
            if not files:
                return
            selected = files[0]
            if selected.path:
                content = Path(selected.path).read_bytes()
            elif selected.bytes:
                content = bytes(selected.bytes)
            else:
                self.app.show_snack(t("mei.invoices.xml_read_fail"), success=False)
                return
            try:
                inv = import_nfe_xml(pid, content)
                self.app.show_snack(t("mei.invoices.xml_imported", number=inv.invoice_number))
                self.app.refresh_current_view()
            except Exception as ex:
                self.app.show_snack(t("mei.invoices.xml_error", error=ex), success=False)

        header = ft.Row(
            [
                ft.Column(
                    [
                        mei_title(t("mei.invoices.title")),
                        ft.Text(
                            t("mei.invoices.recon_year", status=align),
                            size=12,
                            color=theme_colors().success if recon.get("aligned") else theme_colors().warning,
                        ),
                    ],
                    spacing=4,
                ),
                ft.Container(expand=True),
                ft.OutlinedButton(
                    t("mei.invoices.import_xml"),
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=import_xml_click,
                ),
                ft.ElevatedButton(
                    t("mei.invoices.register"),
                    icon=ft.Icons.DESCRIPTION,
                    on_click=lambda _: open_invoice_modal(self.app, pid),
                    style=primary_button_style(bgcolor=MEI_ACCENT),
                ),
            ],
        )

        aging_card = section_card(
            t("mei.invoices.receivables"),
            ft.Column(
                [
                    ft.Text(
                        t(
                            "mei.invoices.outstanding",
                            amount=format_brl(aging["outstanding_total"]),
                            count=aging["unpaid_count"],
                        ),
                        size=13,
                        color=tc.text_primary,
                    ),
                    ft.Row(
                        [
                            self._aging_bucket(t("mei.invoices.bucket_current"), aging["totals"]["current"], theme_colors().success),
                            self._aging_bucket(t("mei.invoices.bucket_1_30"), aging["totals"]["1_30"], theme_colors().warning),
                            self._aging_bucket(t("mei.invoices.bucket_31_60"), aging["totals"]["31_60"], theme_colors().expense),
                            self._aging_bucket(t("mei.invoices.bucket_61_90"), aging["totals"]["61_90"], theme_colors().danger),
                            self._aging_bucket(t("mei.invoices.bucket_90_plus"), aging["totals"]["90_plus"], theme_colors().error_banner_border),
                        ],
                        wrap=True,
                        spacing=12,
                    ),
                ],
                spacing=10,
            ),
        )

        inv_rows = []
        for inv in invoices:
            paid = bool(inv.get("paid_at"))
            inv_rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(inv["invoice_number"], color=tc.text_primary)),
                    ft.DataCell(ft.Text(inv.get("tomador_name") or EMPTY_CELL, color=tc.text_muted)),
                    ft.DataCell(ft.Text(format_brl(Decimal(str(inv["amount"]))))),
                    ft.DataCell(ft.Text(str(inv.get("due_date") or inv["issue_date"]))),
                    ft.DataCell(ft.Text(
                        t("mei.invoices.status_paid") if paid else t("mei.invoices.status_open"),
                        color=theme_colors().success if paid else theme_colors().warning,
                        size=11,
                    )),
                    ft.DataCell(
                        ft.Row(
                            [
                                ft.IconButton(
                                    ft.Icons.PICTURE_AS_PDF,
                                    icon_color=MEI_ACCENT,
                                    tooltip=t("mei.invoices.receipt_pdf"),
                                    on_click=lambda e, iid=inv["id"]: self._export_receipt(pid, iid),
                                ),
                                ft.IconButton(
                                    ft.Icons.PAYMENTS,
                                    icon_color=theme_colors().success,
                                    tooltip=t("mei.invoices.mark_paid"),
                                    disabled=paid,
                                    on_click=lambda e, iid=inv["id"]: self._mark_paid(iid),
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE_OUTLINE,
                                    icon_color=theme_colors().danger,
                                    on_click=lambda e, iid=inv["id"]: delete_invoice(self.app, iid),
                                ),
                            ],
                            spacing=0,
                        )
                    ),
                ])
            )
        if not inv_rows:
            inv_rows = [ft.DataRow(cells=[ft.DataCell(mei_text(t("mei.invoices.none_year"), muted=True))] * 6)]

        return ft.Column(
            [
                header,
                ft.Container(height=16),
                aging_card,
                ft.Container(height=16),
                section_card(
                    t("mei.invoices.control"),
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text(t("mei.invoices.col_number"))),
                            ft.DataColumn(ft.Text(t("mei.invoices.col_tomador"))),
                            ft.DataColumn(ft.Text(t("mei.invoices.col_amount"))),
                            ft.DataColumn(ft.Text(t("mei.invoices.col_due"))),
                            ft.DataColumn(ft.Text(t("mei.invoices.col_status"))),
                            ft.DataColumn(ft.Text("")),
                        ],
                        rows=inv_rows,
                        heading_row_color=tc.surface_alt,
                    ),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _aging_bucket(self, label: str, total: Decimal, color: str) -> ft.Column:
        return ft.Column(
            [
                mei_text(label, size=10, muted=True),
                ft.Text(format_brl(total), size=14, weight=ft.FontWeight.BOLD, color=color),
            ],
            spacing=2,
        )

    def _export_receipt(self, profile_id: int, invoice_id: int):
        try:
            path = generate_mei_service_receipt_pdf(profile_id, invoice_id)
            self.app.show_snack(t("mei.invoices.receipt_saved", path=path))
        except Exception as ex:
            self.app.show_snack(t("mei.invoices.pdf_error", error=ex), success=False)

    def _mark_paid(self, invoice_id: int):
        income = next((c for c in get_categories_for_mode(True) if c.type.value == "income"), None)
        if not income:
            self.app.show_snack(t("mei.invoices.no_income_cat"), success=False)
            return
        if receive_invoice_payment(self.ctx.profile_id, invoice_id, income.id):
            self.app.show_snack(t("mei.invoices.paid_posted"))
            self.app.refresh_current_view()
        else:
            self.app.show_snack(t("mei.invoices.already_paid"), success=False)
