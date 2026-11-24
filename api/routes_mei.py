"""FastAPI router for MEI module and 3-step Onboarding + Backup Restore."""

from __future__ import annotations

import base64
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.backup import restore_backup
from core.db.repositories.categories import get_categories_for_mode
from core.db.repositories.mei import (
    create_mei_client,
    create_mei_invoice,
    delete_mei_client,
    delete_mei_invoice,
    get_mei_clients,
    get_mei_config,
    get_mei_invoices,
    get_mei_profile,
    update_mei_config,
    receive_invoice_payment,
)
from core.db.schema import init_database
from core.demo_data import seed_demo_onboarding
from core.i18n import COUNTRY_PRESETS, apply_from_settings, supports_mei
from core.mei import (
    get_mei_dashboard_data,
    get_obligations_checklist,
    get_revenue_limit_status,
    get_simplified_report,
)
from core.domain.entities.mei_profile import MeiProfile
from core.mei_nfe_xml import import_nfe_xml
from core.models import MeiClient, MeiConfig, MeiInvoice, TransactionType
from core.services.mei_service import (
    confirm_das_payment,
    create_mei_profile,
    das_payment_exists,
)
from core.settings_store import load_settings, save_settings

router = APIRouter(prefix="/api", tags=["mei-onboarding"])


def _js(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _js(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_js(v) for v in obj]
    if hasattr(obj, "model_dump"):
        return _js(obj.model_dump())
    if hasattr(obj, "__dict__") and not isinstance(obj, type):
        return _js(vars(obj))
    if hasattr(obj, "value") and not isinstance(obj, (str, bytes)):
        return obj.value
    return obj


# --- MEI ---

class MeiSetupPayload(BaseModel):
    razao_social: str = Field(min_length=2, max_length=120)
    cnpj: str = Field(min_length=11, max_length=20)
    activity_type: Literal["comercio", "servico", "misto"] = "servico"
    operational_profile: Literal["on_demand", "recurring", "inventory", "hybrid"] = "on_demand"
    das_day: int = Field(default=20, ge=1, le=28)


class MeiClientPayload(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    document: str = ""
    email: str = ""
    phone: str = ""


class MeiInvoicePayload(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=40)
    issue_date: date
    amount: Decimal = Field(gt=0)
    description: str = ""
    client_id: int | None = None


class NfeXmlPayload(BaseModel):
    content_b64: str


@router.get("/mei/overview")
def mei_overview_ep() -> dict[str, Any]:
    init_database()
    prof = get_mei_profile()
    if not prof or not prof.id:
        return {"configured": False}
    cfg = get_mei_config(prof.id)
    if not cfg:
        return {"configured": False}
    today = date.today()
    dash = get_mei_dashboard_data(prof.id)
    limit_status = get_revenue_limit_status(prof.id, cfg.annual_limit)
    report = get_simplified_report(prof.id, today.year)
    mei_entity = MeiProfile(cfg)
    das_info = mei_entity.das_due_info(today)
    das_amount = mei_entity.das_amount()
    das_paid = das_payment_exists(prof.id, today.year, today.month)
    checklist = get_obligations_checklist(prof.id)
    clients = get_mei_clients(prof.id)
    invoices = get_mei_invoices(prof.id, today.year)

    return _js(
        {
            "configured": True,
            "profile_id": prof.id,
            "config": cfg,
            "dashboard": dash,
            "limit_status": limit_status,
            "report": report,
            "das": {
                "paid": das_paid,
                "amount": das_amount,
                "info": das_info,
            },
            "checklist": checklist,
            "clients": clients,
            "invoices": invoices,
        }
    )


@router.post("/mei/setup")
def mei_setup_ep(payload: MeiSetupPayload) -> dict[str, Any]:
    init_database()
    prof = get_mei_profile()
    if prof and prof.id:
        existing = get_mei_config(prof.id)
        if existing:
            updated = MeiConfig(
                id=existing.id,
                profile_id=prof.id,
                razao_social=payload.razao_social.strip(),
                cnpj=payload.cnpj.strip(),
                activity_type=payload.activity_type,
                operational_profile=payload.operational_profile,
                das_day=payload.das_day,
                annual_limit=existing.annual_limit,
                cnae=existing.cnae,
            )
            update_mei_config(updated)
            return {"profile_id": prof.id, "updated": True}

    prof, _cfg = create_mei_profile(
        name=payload.razao_social.strip()[:40],
        razao_social=payload.razao_social.strip(),
        cnpj=payload.cnpj.strip(),
        activity_type=payload.activity_type,
        operational_profile=payload.operational_profile,
    )
    settings = load_settings()
    settings["mei_profile_id"] = prof.id
    save_settings(settings)
    return {"profile_id": prof.id, "created": True}


@router.post("/mei/das/confirm")
def mei_confirm_das_ep() -> dict[str, Any]:
    prof = get_mei_profile()
    if not prof or not prof.id:
        raise HTTPException(status_code=400, detail="MEI not configured")
    cfg = get_mei_config(prof.id)
    if not cfg:
        raise HTTPException(status_code=400, detail="MEI config missing")
    amount = MeiProfile(cfg).das_amount()
    tx_id = confirm_das_payment(prof.id, date.today(), amount)
    return {"confirmed": True, "transaction_id": tx_id}


@router.post("/mei/clients")
def mei_create_client_ep(payload: MeiClientPayload) -> dict[str, Any]:
    prof = get_mei_profile()
    if not prof or not prof.id:
        raise HTTPException(status_code=400, detail="MEI not configured")
    c = create_mei_client(
        MeiClient(
            profile_id=prof.id,
            name=payload.name.strip(),
            document=payload.document.strip() or None,
            email=payload.email.strip() or None,
            phone=payload.phone.strip() or None,
        )
    )
    return _js({"id": c.id})


@router.delete("/mei/clients/{client_id}")
def mei_delete_client_ep(client_id: int) -> dict[str, Any]:
    delete_mei_client(client_id)
    return {"deleted": True}


@router.post("/mei/invoices")
def mei_create_invoice_ep(payload: MeiInvoicePayload) -> dict[str, Any]:
    prof = get_mei_profile()
    if not prof or not prof.id:
        raise HTTPException(status_code=400, detail="MEI not configured")
    inv = create_mei_invoice(
        MeiInvoice(
            profile_id=prof.id,
            invoice_number=payload.invoice_number.strip(),
            issue_date=payload.issue_date,
            amount=payload.amount,
            description=payload.description.strip() or None,
            client_id=payload.client_id,
        )
    )
    return _js({"id": inv.id})


@router.post("/mei/invoices/{invoice_id}/receive")
def mei_receive_invoice_ep(invoice_id: int) -> dict[str, Any]:
    prof = get_mei_profile()
    if not prof or not prof.id:
        raise HTTPException(status_code=400, detail="MEI not configured")
    cats = get_categories_for_mode(True)
    inc = next((c for c in cats if c.type == TransactionType.INCOME and c.id), None)
    if not inc or not inc.id:
        raise HTTPException(status_code=400, detail="No MEI income category found")
    tx_id = receive_invoice_payment(prof.id, invoice_id, inc.id, date.today())
    return {"received": True, "transaction_id": tx_id}


@router.delete("/mei/invoices/{invoice_id}")
def mei_delete_invoice_ep(invoice_id: int) -> dict[str, Any]:
    delete_mei_invoice(invoice_id)
    return {"deleted": True}


@router.post("/mei/nfe-xml")
def mei_nfe_xml_ep(payload: NfeXmlPayload) -> dict[str, Any]:
    prof = get_mei_profile()
    if not prof or not prof.id:
        raise HTTPException(status_code=400, detail="MEI not configured")
    raw = base64.b64decode(payload.content_b64)
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="XML exceeds 5 MB limit")
    inv = import_nfe_xml(prof.id, raw)
    return _js({"id": inv.id, "invoice_number": inv.invoice_number})


# --- Onboarding & Backup Restore ---

class OnboardingCompletePayload(BaseModel):
    country: Literal["BR", "US", "ES"] = "BR"
    setup_mode: Literal["personal", "mei", "both"] = "personal"
    use_demo: bool = False
    backup_on_close: bool = True


class RestoreBackupPayload(BaseModel):
    filename: str
    content_b64: str


@router.post("/onboarding/complete")
def onboarding_complete_ep(payload: OnboardingCompletePayload) -> dict[str, Any]:
    init_database()
    preset = COUNTRY_PRESETS.get(payload.country) or COUNTRY_PRESETS["BR"]
    mode = payload.setup_mode
    if not supports_mei(payload.country) and mode in ("mei", "both"):
        mode = "personal"

    s = load_settings()
    s["country_profile"] = payload.country
    s["locale"] = preset["locale"]
    s["currency"] = preset["currency"]
    s["setup_mode"] = mode
    s["backup_on_close"] = payload.backup_on_close
    s["onboarding_completed"] = True
    apply_from_settings(s)

    seeded_personal = seeded_mei = 0
    if payload.use_demo:
        seeded_personal, seeded_mei = seed_demo_onboarding(s)

    save_settings(s)
    return {
        "completed": True,
        "seeded_personal": seeded_personal,
        "seeded_mei": seeded_mei,
    }


@router.post("/backup/restore")
def backup_restore_ep(payload: RestoreBackupPayload) -> dict[str, Any]:
    raw = base64.b64decode(payload.content_b64)
    with tempfile.TemporaryDirectory(prefix="orcfin_restore_api_") as tmp:
        p = Path(tmp) / (Path(payload.filename).name or "backup.orcfin.bak")
        p.write_bytes(raw)
        restore_backup(p)
    s = load_settings()
    s["onboarding_completed"] = True
    apply_from_settings(s)
    save_settings(s)
    return {"restored": True}
