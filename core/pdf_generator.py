"""
OrcFin - Professional PDF Report Generator
Clean, modern monthly financial report.
"""

from calendar import monthrange
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fpdf import FPDF

from core.branding import APP_NAME
from core.copy import EMPTY_CELL
from core.db.queries import (
    get_category_breakdown,
    get_consolidated_summary,
    get_monthly_summary,
)
from core.db.repositories.mei import get_mei_config, get_mei_invoices
from core.db.repositories.profiles import get_all_profiles
from core.db.repositories.transactions import get_transactions
from core.domain.locale_format import format_display_month_day
from core.domain.value_objects.money import format_brl
from core.engine.reporting import get_year_to_date_summary
from core.i18n import t
from core.models import TransactionType


def _find_font_files() -> Tuple[str, Optional[str]]:
    """Resolve Unicode-capable fonts across Windows, Linux, and macOS."""
    root = Path(__file__).parent.parent
    candidates_regular = [
        root / "assets" / "fonts" / "DejaVuSans.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
    ]
    candidates_bold = [
        root / "assets" / "fonts" / "DejaVuSans-Bold.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/Library/Fonts/Arial Bold.ttf"),
    ]

    regular = next((str(p) for p in candidates_regular if p.exists()), None)
    bold = next((str(p) for p in candidates_bold if p.exists()), None)
    if not regular:
        raise FileNotFoundError(t("pdf.font_missing"))
    return regular, bold


def _app_tagline() -> str:
    return f"{APP_NAME}: {t('app.subtitle')}"


def _month_period_label(year: int, month: int) -> str:
    month_name = t(f"personal.month_{month}")
    return t("pdf.month_year", month=month_name, year=year)


class OrcFinPDF(FPDF):
    FONT_FAMILY = "OrcFin"

    def __init__(self):
        super().__init__()
        regular, bold = _find_font_files()
        self.add_font(self.FONT_FAMILY, "", regular)
        self.add_font(self.FONT_FAMILY, "B", bold or regular)
        self.add_font(self.FONT_FAMILY, "I", regular)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font(self.FONT_FAMILY, "B", 18)
        self.set_text_color(20, 184, 166)
        self.cell(0, 12, t("pdf.header_title"), ln=True, align="C")
        self.set_font(self.FONT_FAMILY, "", 10)
        self.set_text_color(100, 116, 139)
        self.cell(0, 6, t("app.subtitle"), ln=True, align="C")
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.FONT_FAMILY, "", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, t("pdf.page", n=self.page_no()), align="C")


class MeiPDF(FPDF):
    FONT_FAMILY = "OrcFin"

    def __init__(self):
        super().__init__()
        regular, bold = _find_font_files()
        self.add_font(self.FONT_FAMILY, "", regular)
        self.add_font(self.FONT_FAMILY, "B", bold or regular)
        self.add_font(self.FONT_FAMILY, "I", regular)
        self.set_auto_page_break(auto=True, margin=15)

    def _section(self, title: str):
        self.set_fill_color(30, 41, 59)
        self.set_text_color(255, 255, 255)
        self.set_font(self.FONT_FAMILY, "B", 11)
        self.cell(0, 8, f"  {title}", ln=True, fill=True)
        self.ln(2)
        self.set_text_color(30, 41, 59)


def _month_period(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    return start, end


def _reports_dir() -> Path:
    d = Path(__file__).parent.parent / "reports"
    d.mkdir(exist_ok=True)
    return d


def generate_monthly_report(
    year: int,
    month: int,
    consolidated: bool = True,
    profile_id: Optional[int] = None,
    output_path: Path = None,
) -> Path:
    """Generate a beautiful monthly PDF report."""
    if not consolidated and profile_id is None:
        raise ValueError(t("pdf.err_profile_required"))

    if output_path is None:
        suffix = "consolidado" if consolidated else f"perfil_{profile_id}"
        output_path = _reports_dir() / f"relatorio_{year}_{month:02d}_{suffix}.pdf"

    if consolidated:
        current = get_consolidated_summary(year, month)
        breakdown_profile_id = None
        tx_profile_id = None
        active_only = True
        scope_label = t("pdf.scope_consolidated")
    else:
        current = get_monthly_summary(year, month, profile_id)
        breakdown_profile_id = profile_id
        tx_profile_id = profile_id
        active_only = False
        profile = next((p for p in get_all_profiles() if p.id == profile_id), None)
        scope_label = (
            t("pdf.scope_profile", name=profile.name)
            if profile
            else t("pdf.scope_profile_id", id=profile_id)
        )

    ytd = get_year_to_date_summary(
        profile_id=profile_id,
        consolidated=consolidated,
        year=year,
        up_to_month=month,
    )
    categories = get_category_breakdown(
        year, month, breakdown_profile_id, TransactionType.EXPENSE
    )[:8]

    period_start, period_end = _month_period(year, month)
    recent_txs = get_transactions(
        profile_id=tx_profile_id,
        active_profiles_only=active_only,
        start_date=period_start,
        end_date=period_end,
        limit=15,
    )

    pdf = OrcFinPDF()
    pdf.add_page()

    ff = OrcFinPDF.FONT_FAMILY
    pdf.set_font(ff, "B", 14)
    pdf.set_text_color(30, 41, 59)
    period = _month_period_label(year, month)
    pdf.cell(0, 10, t("pdf.report_of", period=period), ln=True, align="C")
    pdf.set_font(ff, "", 10)
    pdf.cell(0, 8, scope_label, ln=True, align="C")
    pdf.ln(6)

    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(ff, "B", 11)
    pdf.cell(0, 8, t("pdf.section_month_summary"), ln=True, fill=True)
    pdf.ln(2)

    pdf.set_text_color(30, 41, 59)
    pdf.set_font(ff, "", 11)

    summary_data = [
        (t("pdf.total_income"), format_brl(current["total_income"])),
        (t("pdf.total_expense"), format_brl(current["total_expense"])),
        (t("pdf.net_savings"), format_brl(current["net_savings"])),
        (t("pdf.savings_rate"), f"{current['savings_rate']}%"),
    ]

    for label, value in summary_data:
        pdf.set_font(ff, "", 10)
        pdf.cell(80, 7, f"  {label}:", border=0)
        pdf.set_font(ff, "B", 10)
        pdf.cell(0, 7, value, ln=True)

    pdf.ln(6)

    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(ff, "B", 11)
    pdf.cell(0, 8, t("pdf.section_ytd", month=month, year=year), ln=True, fill=True)
    pdf.ln(2)

    pdf.set_text_color(30, 41, 59)
    ytd_data = [
        (t("pdf.income_ytd"), format_brl(ytd["total_income"])),
        (t("pdf.expense_ytd"), format_brl(ytd["total_expense"])),
        (t("pdf.savings_ytd"), format_brl(ytd["net_savings"])),
        (t("pdf.savings_rate_ytd"), f"{ytd['savings_rate']}%"),
    ]

    for label, value in ytd_data:
        pdf.set_font(ff, "", 10)
        pdf.cell(80, 7, f"  {label}:", border=0)
        pdf.set_font(ff, "B", 10)
        pdf.cell(0, 7, value, ln=True)

    pdf.ln(8)

    if categories:
        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(ff, "B", 11)
        pdf.cell(0, 8, t("pdf.section_top_categories"), ln=True, fill=True)
        pdf.ln(3)

        pdf.set_text_color(30, 41, 59)
        pdf.set_font(ff, "B", 9)
        pdf.cell(10, 7, "#", border=0)
        pdf.cell(70, 7, t("common.category"), border=0)
        pdf.cell(40, 7, t("common.amount"), border=0, align="R")
        pdf.cell(30, 7, t("pdf.col_pct"), border=0, align="R", ln=True)

        pdf.set_font(ff, "", 9)
        total_expense = current["total_expense"] or Decimal("1")

        for i, cat in enumerate(categories, 1):
            pct = float((cat["total"] / total_expense * 100)) if total_expense > 0 else 0
            pdf.cell(10, 6, str(i), border=0)
            pdf.cell(70, 6, f"{cat['icon']} {cat['name'][:35]}", border=0)
            pdf.cell(40, 6, format_brl(cat["total"]), border=0, align="R")
            pdf.cell(30, 6, f"{pct:.1f}%", border=0, align="R", ln=True)

    pdf.ln(8)

    if recent_txs:
        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(ff, "B", 11)
        pdf.cell(0, 8, t("pdf.section_transactions"), ln=True, fill=True)
        pdf.ln(3)

        pdf.set_text_color(30, 41, 59)
        pdf.set_font(ff, "B", 8)
        pdf.cell(22, 6, t("common.date"), border=0)
        pdf.cell(75, 6, t("common.description"), border=0)
        pdf.cell(45, 6, t("common.amount"), border=0, align="R")
        pdf.cell(0, 6, t("common.type"), border=0, ln=True)

        pdf.set_font(ff, "", 8)
        for tx in recent_txs[:12]:
            tx_type = (
                t("common.income")
                if tx.type == TransactionType.INCOME
                else t("common.expense")
            )
            color = (34, 197, 94) if tx.type == TransactionType.INCOME else (239, 68, 68)
            pdf.set_text_color(*color)
            pdf.cell(22, 5, format_display_month_day(tx.date), border=0)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(75, 5, tx.description[:40], border=0)
            pdf.cell(45, 5, format_brl(tx.amount), border=0, align="R")
            pdf.cell(0, 5, tx_type, ln=True)

    pdf.ln(10)

    pdf.set_font(ff, "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(
        0, 5, t("pdf.footer_auto", app=_app_tagline(), scope=scope_label)
    )

    pdf.output(output_path)
    return output_path


def generate_mei_service_receipt_pdf(
    profile_id: int,
    invoice_id: int,
    output_path: Optional[Path] = None,
) -> Path:
    """Generate a service receipt PDF for a registered MEI invoice."""
    config = get_mei_config(profile_id)
    if not config:
        raise ValueError(t("pdf.err_mei_not_configured"))

    invoices = get_mei_invoices(profile_id)
    invoice = next((i for i in invoices if i["id"] == invoice_id), None)
    if not invoice:
        raise ValueError(t("pdf.err_invoice_not_found"))

    if output_path is None:
        safe_num = str(invoice["invoice_number"]).replace("/", "-")[:30]
        output_path = _reports_dir() / f"recibo_mei_{safe_num}.pdf"

    pdf = MeiPDF()
    pdf.add_page()
    ff = MeiPDF.FONT_FAMILY

    pdf.set_font(ff, "B", 16)
    pdf.set_text_color(245, 158, 11)
    pdf.cell(0, 10, t("pdf.receipt_title"), ln=True, align="C")
    pdf.ln(4)

    pdf.set_text_color(30, 41, 59)
    pdf.set_font(ff, "B", 12)
    pdf.cell(0, 8, config.razao_social, ln=True, align="C")
    pdf.set_font(ff, "", 10)
    pdf.cell(0, 6, f"CNPJ: {config.cnpj}", ln=True, align="C")
    pdf.ln(8)

    pdf._section(t("pdf.section_invoice"))
    pdf.set_font(ff, "", 10)
    rows = [
        (t("pdf.invoice_number"), invoice["invoice_number"]),
        (t("pdf.client"), invoice.get("tomador_name") or EMPTY_CELL),
        (t("pdf.issue_date"), str(invoice["issue_date"])),
        (t("common.amount"), format_brl(Decimal(str(invoice["amount"])))),
    ]
    if invoice.get("due_date"):
        rows.append((t("pdf.due_date"), str(invoice["due_date"])))
    for label, value in rows:
        pdf.cell(55, 7, f"  {label}:", border=0)
        pdf.set_font(ff, "B", 10)
        pdf.cell(0, 7, str(value), ln=True)
        pdf.set_font(ff, "", 10)

    pdf.ln(6)
    pdf._section(t("pdf.section_declaration"))
    pdf.set_font(ff, "", 10)
    tomador = invoice.get("tomador_name") or t("pdf.client_fallback")
    valor = format_brl(Decimal(str(invoice["amount"])))
    pdf.multi_cell(
        0,
        6,
        t(
            "pdf.declaration_body",
            tomador=tomador,
            valor=valor,
            number=invoice["invoice_number"],
        ),
    )

    pdf.ln(12)
    pdf.set_font(ff, "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, t("pdf.receipt_footer", app=APP_NAME))

    pdf.output(output_path)
    return output_path


def generate_mei_monthly_result_pdf(
    profile_id: int,
    year: int,
    month: int,
    report: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """Generate MEI monthly P&L result PDF."""
    config = get_mei_config(profile_id)
    if not config:
        raise ValueError(t("pdf.err_mei_not_configured"))

    if output_path is None:
        output_path = _reports_dir() / f"resultado_mei_{year}_{month:02d}.pdf"

    monthly = get_monthly_summary(year, month, profile_id)
    pdf = MeiPDF()
    pdf.add_page()
    ff = MeiPDF.FONT_FAMILY

    period = _month_period_label(year, month)
    pdf.set_font(ff, "B", 16)
    pdf.set_text_color(245, 158, 11)
    pdf.cell(0, 10, t("pdf.mei_result_title", period=period), ln=True, align="C")
    pdf.set_font(ff, "", 10)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 6, f"{config.razao_social} • CNPJ {config.cnpj}", ln=True, align="C")
    pdf.ln(8)

    pdf._section(t("pdf.section_month_result"))
    pdf.set_font(ff, "", 10)
    for label, value in [
        (t("pdf.month_income"), format_brl(monthly["total_income"])),
        (t("pdf.month_expense"), format_brl(monthly["total_expense"])),
        (t("pdf.month_balance"), format_brl(monthly["net_savings"])),
    ]:
        pdf.cell(70, 7, f"  {label}:", border=0)
        pdf.set_font(ff, "B", 10)
        pdf.cell(0, 7, value, ln=True)
        pdf.set_font(ff, "", 10)

    pdf.ln(4)
    pdf._section(t("pdf.mei_ytd_section", year=year))
    pdf.set_font(ff, "", 10)
    for label, value in [
        (t("pdf.mei_gross_ytd"), format_brl(report["gross_revenue"])),
        (t("pdf.mei_deductible"), format_brl(report["deductible_expenses"])),
        (t("pdf.mei_non_deductible"), format_brl(report["non_deductible_expenses"])),
        (t("pdf.mei_simplified_result"), format_brl(report["simplified_result"])),
    ]:
        pdf.cell(70, 7, f"  {label}:", border=0)
        pdf.set_font(ff, "B", 10)
        pdf.cell(0, 7, value, ln=True)
        pdf.set_font(ff, "", 10)

    pdf.ln(8)
    pdf.set_font(ff, "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, t("pdf.mei_disclaimer"))

    pdf.output(output_path)
    return output_path
