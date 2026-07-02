"""Parse NF-e / NFS-e XML locally and register MEI invoices."""

from __future__ import annotations

import re

import defusedxml.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from core.db.repositories.mei import create_mei_invoice
from core.models import MeiInvoice


def _tag(local: str) -> str:
    return f".//{{*}}{local}"


def _text(node: Optional[ET.Element]) -> str:
    return (node.text or "").strip() if node is not None else ""


def _parse_date(raw: str) -> date:
    raw = raw.strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    if "T" in raw:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")[:19]).date()
    raise ValueError(f"data inválida no XML: {raw}")


def _parse_amount(raw: str) -> Decimal:
    text = re.sub(r"[^\d,.-]", "", raw.strip())
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    return Decimal(text or "0")


def parse_nfe_xml(content: bytes) -> Dict[str, Any]:
    """Extract invoice fields from NF-e/NFS-e XML (namespace-agnostic)."""
    root = ET.fromstring(content)

    number = _text(root.find(_tag("nNF"))) or _text(root.find(_tag("nDFSe")))
    if not number:
        for node in root.iter():
            if node.tag.split("}")[-1] in ("nNF", "nDFSe", "Numero", "numero"):
                number = _text(node)
                if number:
                    break
    if not number:
        raise ValueError("Número da NF não encontrado no XML")

    issue_raw = (
        _text(root.find(_tag("dhEmi")))
        or _text(root.find(_tag("dEmi")))
        or _text(root.find(_tag("dhProc")))
        or _text(root.find(_tag("DataEmissao")))
    )
    if not issue_raw:
        for node in root.iter():
            tag = node.tag.split("}")[-1]
            if tag in ("dhEmi", "dEmi", "DataEmissao", "dhProc"):
                issue_raw = _text(node)
                if issue_raw:
                    break
    issue_date = _parse_date(issue_raw) if issue_raw else date.today()

    tomador = (
        _text(root.find(_tag("xNome")))
        or _text(root.find(_tag("RazaoSocial")))
        or _text(root.find(_tag("NomeTomador")))
    )
    if not tomador:
        for dest in root.iter():
            if dest.tag.split("}")[-1] in ("dest", "Tomador", "tomador"):
                for child in dest.iter():
                    if child.tag.split("}")[-1] in ("xNome", "RazaoSocial", "Nome"):
                        tomador = _text(child)
                        if tomador:
                            break
            if tomador:
                break

    amount_raw = (
        _text(root.find(_tag("vNF")))
        or _text(root.find(_tag("vLiq")))
        or _text(root.find(_tag("ValorServicos")))
        or _text(root.find(_tag("ValorTotal")))
    )
    if not amount_raw:
        for node in root.iter():
            if node.tag.split("}")[-1] in ("vNF", "vLiq", "ValorServicos", "ValorTotal"):
                amount_raw = _text(node)
                if amount_raw:
                    break
    amount = _parse_amount(amount_raw)
    if amount <= 0:
        raise ValueError("Valor da NF inválido ou ausente no XML")

    return {
        "invoice_number": number,
        "tomador_name": tomador or None,
        "amount": amount,
        "issue_date": issue_date,
    }


def import_nfe_xml(profile_id: int, content: bytes) -> MeiInvoice:
    data = parse_nfe_xml(content)
    return create_mei_invoice(
        MeiInvoice(
            profile_id=profile_id,
            invoice_number=data["invoice_number"],
            tomador_name=data["tomador_name"],
            amount=data["amount"],
            issue_date=data["issue_date"],
            notes="import:xml",
        )
    )