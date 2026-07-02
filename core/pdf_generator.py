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

from core.copy import EMPTY_CELL
from core.domain.value_objects.money import format_brl
from core.engine.reporting import get_year_to_date_summary
from core.db.queries import (
    get_category_breakdown,
    get_consolidated_summary,
    get_monthly_summary,
)
from core.db.repositories.mei import get_mei_config, get_mei_invoices
from core.db.repositories.profiles import get_all_profiles
from core.db.repositories.transactions import get_transactions
from core.branding import APP_NAME, APP_SUBTITLE, APP_TAGLINE
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
        raise FileNotFoundError(
            "Nenhuma fonte Unicode encontrada. Instale DejaVu ou use Windows/macOS com Arial."
        )
    return regular, bold


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
        self.cell(0, 12, f"{APP_NAME}: Relatório Financeiro", ln=True, align="C")
        self.set_font(self.FONT_FAMILY, "", 10)
        self.set_text_color(100, 116, 139)
        self.cell(0, 6, APP_SUBTITLE, ln=True, align="C")
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.FONT_FAMILY, "", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")


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
        raise ValueError("profile_id é obrigatório para relatório individual")

    if output_path is None:
        suffix = "consolidado" if consolidated else f"perfil_{profile_id}"
        output_path = _reports_dir() / f"relatorio_{year}_{month:02d}_{suffix}.pdf"

    if consolidated:
        current = get_consolidated_summary(year, month)
        breakdown_profile_id = None
        tx_profile_id = None
        active_only = True
        scope_label = "Visão Consolidada (todos os perfis ativos)"
    else:
        current = get_monthly_summary(year, month, profile_id)
        breakdown_profile_id = profile_id
        tx_profile_id = profile_id
        active_only = False
        profile = next((p for p in get_all_profiles() if p.id == profile_id), None)
        scope_label = f"Perfil: {profile.name}" if profile else f"Perfil #{profile_id}"

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
    month_name = date(year, month, 1).strftime("%B de %Y").capitalize()
    pdf.cell(0, 10, f"Relatório de {month_name}", ln=True, align="C")
    pdf.set_font(ff, "", 10)
    pdf.cell(0, 8, scope_label, ln=True, align="C")
    pdf.ln(6)

    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(ff, "B", 11)
    pdf.cell(0, 8, "  RESUMO DO MÊS", ln=True, fill=True)
    pdf.ln(2)

    pdf.set_text_color(30, 41, 59)
    pdf.set_font(ff, "", 11)

    summary_data = [
        ("Receita Total", format_brl(current["total_income"])),
        ("Despesa Total", format_brl(current["total_expense"])),
        ("Economia Líquida", format_brl(current["net_savings"])),
        ("Taxa de Poupança", f"{current['savings_rate']}%"),
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
    pdf.cell(0, 8, f"  RESUMO ANO ATÉ {month:02d}/{year} (YTD)", ln=True, fill=True)
    pdf.ln(2)

    pdf.set_text_color(30, 41, 59)
    ytd_data = [
        ("Receita YTD", format_brl(ytd["total_income"])),
        ("Despesa YTD", format_brl(ytd["total_expense"])),
        ("Economia YTD", format_brl(ytd["net_savings"])),
        ("Taxa de Poupança YTD", f"{ytd['savings_rate']}%"),
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
        pdf.cell(0, 8, "  PRINCIPAIS CATEGORIAS DE DESPESA", ln=True, fill=True)
        pdf.ln(3)

        pdf.set_text_color(30, 41, 59)
        pdf.set_font(ff, "B", 9)
        pdf.cell(10, 7, "#", border=0)
        pdf.cell(70, 7, "Categoria", border=0)
        pdf.cell(40, 7, "Valor", border=0, align="R")
        pdf.cell(30, 7, "% do Total", border=0, align="R", ln=True)

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
        pdf.cell(0, 8, "  LANÇAMENTOS DO PERÍODO", ln=True, fill=True)
        pdf.ln(3)

        pdf.set_text_color(30, 41, 59)
        pdf.set_font(ff, "B", 8)
        pdf.cell(22, 6, "Data", border=0)
        pdf.cell(75, 6, "Descrição", border=0)
        pdf.cell(45, 6, "Valor", border=0, align="R")
        pdf.cell(0, 6, "Tipo", border=0, ln=True)

        pdf.set_font(ff, "", 8)
        for tx in recent_txs[:12]:
            tx_type = "Receita" if tx.type == TransactionType.INCOME else "Despesa"
            color = (34, 197, 94) if tx.type == TransactionType.INCOME else (239, 68, 68)
            pdf.set_text_color(*color)
            pdf.cell(22, 5, tx.date.strftime("%d/%m"), border=0)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(75, 5, tx.description[:40], border=0)
            pdf.cell(45, 5, format_brl(tx.amount), border=0, align="R")
            pdf.cell(0, 5, tx_type, ln=True)

    pdf.ln(10)

    pdf.set_font(ff, "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, f"Relatório gerado automaticamente pelo {APP_TAGLINE}. Escopo: {scope_label}.")

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
        raise ValueError("Perfil MEI não configurado")

    invoices = get_mei_invoices(profile_id)
    invoice = next((i for i in invoices if i["id"] == invoice_id), None)
    if not invoice:
        raise ValueError("Nota fiscal não encontrada")

    if output_path is None:
        safe_num = str(invoice["invoice_number"]).replace("/", "-")[:30]
        output_path = _reports_dir() / f"recibo_mei_{safe_num}.pdf"

    pdf = MeiPDF()
    pdf.add_page()
    ff = MeiPDF.FONT_FAMILY

    pdf.set_font(ff, "B", 16)
    pdf.set_text_color(245, 158, 11)
    pdf.cell(0, 10, "RECIBO DE PRESTAÇÃO DE SERVIÇOS", ln=True, align="C")
    pdf.ln(4)

    pdf.set_text_color(30, 41, 59)
    pdf.set_font(ff, "B", 12)
    pdf.cell(0, 8, config.razao_social, ln=True, align="C")
    pdf.set_font(ff, "", 10)
    pdf.cell(0, 6, f"CNPJ: {config.cnpj}", ln=True, align="C")
    pdf.ln(8)

    pdf._section("DADOS DA NOTA")
    pdf.set_font(ff, "", 10)
    rows = [
        ("Número da NF", invoice["invoice_number"]),
        ("Tomador", invoice.get("tomador_name") or EMPTY_CELL),
        ("Data de emissão", str(invoice["issue_date"])),
        ("Valor", format_brl(Decimal(str(invoice["amount"])))),
    ]
    if invoice.get("due_date"):
        rows.append(("Vencimento", str(invoice["due_date"])))
    for label, value in rows:
        pdf.cell(55, 7, f"  {label}:", border=0)
        pdf.set_font(ff, "B", 10)
        pdf.cell(0, 7, str(value), ln=True)
        pdf.set_font(ff, "", 10)

    pdf.ln(6)
    pdf._section("DECLARAÇÃO")
    pdf.set_font(ff, "", 10)
    tomador = invoice.get("tomador_name") or "o tomador"
    valor = format_brl(Decimal(str(invoice["amount"])))
    pdf.multi_cell(
        0, 6,
        f"Declaro ter recebido de {tomador} a quantia de {valor}, referente à prestação "
        f"de serviços documentada pela nota fiscal nº {invoice['invoice_number']}.",
    )

    pdf.ln(12)
    pdf.set_font(ff, "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(
        0, 5,
        f"Documento gerado pelo {APP_NAME} para controle interno. Não substitui NF-e oficial do governo.",
    )

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
        raise ValueError("Perfil MEI não configurado")

    if output_path is None:
        output_path = _reports_dir() / f"resultado_mei_{year}_{month:02d}.pdf"

    monthly = get_monthly_summary(year, month, profile_id)
    pdf = MeiPDF()
    pdf.add_page()
    ff = MeiPDF.FONT_FAMILY

    month_name = date(year, month, 1).strftime("%B de %Y").capitalize()
    pdf.set_font(ff, "B", 16)
    pdf.set_text_color(245, 158, 11)
    pdf.cell(0, 10, f"Resultado MEI: {month_name}", ln=True, align="C")
    pdf.set_font(ff, "", 10)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 6, f"{config.razao_social} • CNPJ {config.cnpj}", ln=True, align="C")
    pdf.ln(8)

    pdf._section("RESULTADO DO MÊS")
    pdf.set_font(ff, "", 10)
    for label, value in [
        ("Receita do mês", format_brl(monthly["total_income"])),
        ("Despesa do mês", format_brl(monthly["total_expense"])),
        ("Saldo do mês", format_brl(monthly["net_savings"])),
    ]:
        pdf.cell(70, 7, f"  {label}:", border=0)
        pdf.set_font(ff, "B", 10)
        pdf.cell(0, 7, value, ln=True)
        pdf.set_font(ff, "", 10)

    pdf.ln(4)
    pdf._section(f"ACUMULADO {year}")
    pdf.set_font(ff, "", 10)
    for label, value in [
        ("Receita bruta YTD", format_brl(report["gross_revenue"])),
        ("Despesas dedutíveis", format_brl(report["deductible_expenses"])),
        ("Despesas não dedutíveis", format_brl(report["non_deductible_expenses"])),
        ("Resultado simplificado", format_brl(report["simplified_result"])),
    ]:
        pdf.cell(70, 7, f"  {label}:", border=0)
        pdf.set_font(ff, "B", 10)
        pdf.cell(0, 7, value, ln=True)
        pdf.set_font(ff, "", 10)

    pdf.ln(8)
    pdf.set_font(ff, "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(
        0, 5,
        "Visão simplificada para gestão interna. Consulte seu contador para declarações oficiais.",
    )

    pdf.output(output_path)
    return output_path