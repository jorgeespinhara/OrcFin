"""MEI accountant pack — PDF + CSV in one ZIP (local export)."""

from __future__ import annotations

import calendar
import csv
import zipfile
from datetime import date
from pathlib import Path

from core.db.repositories.mei import get_mei_config, get_mei_deductible_category_ids, get_mei_invoices
from core.db.repositories.transactions import get_transactions
from core.mei import get_simplified_report
from core.pdf_generator import generate_mei_monthly_result_pdf

from core.paths import get_app_data_dir


def _export_dir() -> Path:
    folder = get_app_data_dir() / "exports"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def export_accountant_pack(profile_id: int, year: int, month: int) -> Path:
    export_dir = _export_dir()
    stamp = f"{year}{month:02d}"
    zip_path = export_dir / f"mei_contador_{stamp}.zip"
    report = get_simplified_report(profile_id, year, deductible_category_ids=get_mei_deductible_category_ids())
    pdf_path = generate_mei_monthly_result_pdf(profile_id, year, month, report)

    start, end = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    txs = get_transactions(profile_id=profile_id, start_date=start, end_date=end, limit=5000)
    invoices = get_mei_invoices(profile_id, year=year)

    tx_csv = export_dir / f"_tx_{stamp}.csv"
    nf_csv = export_dir / f"_nf_{stamp}.csv"
    with tx_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "description", "amount", "type", "category_id"])
        for tx in txs:
            w.writerow([tx.date.isoformat(), tx.description, str(tx.amount), tx.type.value, tx.category_id])
    with nf_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["invoice_number", "tomador", "amount", "issue_date", "due_date", "paid_at"])
        for inv in invoices:
            if str(inv.get("issue_date", "")).startswith(f"{year}-{month:02d}"):
                w.writerow([
                    inv.get("invoice_number"),
                    inv.get("tomador_name"),
                    inv.get("amount"),
                    inv.get("issue_date"),
                    inv.get("due_date"),
                    inv.get("paid_at"),
                ])

    cfg = get_mei_config(profile_id)
    readme = export_dir / f"_readme_{stamp}.txt"
    readme.write_text(
        f"Pacote contador MEI {month:02d}/{year}\n"
        f"{cfg.razao_social if cfg else ''} | CNPJ {cfg.cnpj if cfg else ''}\n",
        encoding="utf-8",
    )

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(pdf_path, arcname=pdf_path.name)
        zf.write(tx_csv, arcname=f"lancamentos_{stamp}.csv")
        zf.write(nf_csv, arcname=f"notas_{stamp}.csv")
        zf.write(readme, arcname="leia-me.txt")

    for tmp in (tx_csv, nf_csv, readme):
        tmp.unlink(missing_ok=True)
    return zip_path