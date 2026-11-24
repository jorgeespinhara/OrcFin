"""Local FastAPI server bridging OrcFin core/ (SQLite) to the React desktop UI."""

from __future__ import annotations

from calendar import monthrange
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.branding import APP_NAME, APP_VERSION
from core.db.connection import SCHEMA_VERSION
from core.db.repositories.categories import display_name, get_all_categories
from core.db.repositories.credit_cards import get_credit_cards
from core.db.repositories.profiles import get_all_profiles
from core.db.repositories.transactions import (
    create_transaction,
    delete_transactions_batch,
    get_transaction,
    get_transactions,
    restore_transactions,
    search_transactions,
    soft_delete_transactions,
    update_transaction,
    update_transactions_category_batch,
)
from core.db.schema import init_database
from core.demo_data import seed_demo_transactions
from core.engine.due_dates import get_upcoming_due_dates
from core.engine.reporting import get_dashboard_data
from core.engine.spendable import get_spendable_amount
from core.i18n import apply_from_settings, get_currency, supports_mei
from core.models import Transaction, TransactionType
from core.settings_store import load_settings, save_settings

_BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
FRONTEND_DIST = _BASE_DIR / "frontend" / "dist"


def _to_json_safe(obj: Any) -> Any:
    """Recursively convert Decimal/date/Enum to JSON-serializable primitives."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(v) for v in obj]
    if hasattr(obj, "value") and not isinstance(obj, (str, bytes)):
        return obj.value
    return obj


class TransactionPayload(BaseModel):
    profile_id: int
    date: date
    description: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(gt=0)
    category_id: int
    type: Literal["income", "expense"]
    credit_card_id: int | None = None
    notes: str | None = None
    is_recurring: bool = False


class ThemePayload(BaseModel):
    theme_mode: Literal["dark", "light"]


class IdsPayload(BaseModel):
    ids: list[int] = Field(min_length=1)


class BatchCategoryPayload(BaseModel):
    ids: list[int] = Field(min_length=1)
    category_id: int


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    settings = load_settings()
    apply_from_settings(settings)
    init_database()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=f"{APP_NAME} Local API", version=APP_VERSION, lifespan=_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/meta")
    def get_meta() -> dict[str, Any]:
        init_database()
        settings = load_settings()
        apply_from_settings(settings)
        profiles = get_all_profiles()
        categories = get_all_categories()
        cards = get_credit_cards(None)
        return _to_json_safe(
            {
                "app_name": APP_NAME,
                "version": APP_VERSION,
                "schema_version": SCHEMA_VERSION,
                "theme_mode": settings.get("theme_mode", "dark"),
                "locale": settings.get("locale", "pt-BR"),
                "currency": get_currency() or settings.get("currency", "BRL"),
                "strict_offline": bool(settings.get("strict_offline", False)),
                "onboarding_completed": bool(settings.get("onboarding_completed", False)),
                "mei_available": supports_mei(settings.get("country_profile", "BR")),
                "profiles": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "color": p.color,
                        "is_active": p.is_active,
                    }
                    for p in profiles
                ],
                "categories": [
                    {
                        "id": c.id,
                        "name": display_name(c),
                        "slug": c.slug,
                        "icon": c.icon or "",
                        "color": getattr(c, "color", None) or ("#22C55E" if c.type == TransactionType.INCOME else "#14B8A6"),
                        "type": c.type.value,
                    }
                    for c in categories
                ],
                "credit_cards": [
                    {
                        "id": cd.id,
                        "name": cd.name,
                        "profile_id": cd.profile_id,
                        "limit": cd.credit_limit,
                        "due_day": cd.due_day,
                    }
                    for cd in cards
                ],
            }
        )

    @app.post("/api/settings/theme")
    def set_theme(payload: ThemePayload) -> dict[str, str]:
        settings = load_settings()
        settings["theme_mode"] = payload.theme_mode
        save_settings(settings)
        return {"theme_mode": payload.theme_mode}

    @app.post("/api/demo-seed")
    def seed_demo() -> dict[str, Any]:
        init_database()
        count = seed_demo_transactions()
        return {"seeded": count}

    @app.get("/api/dashboard")
    def dashboard(
        profile_id: int | None = Query(default=None),
        consolidated: bool = Query(default=True),
        year: int | None = Query(default=None),
        month: int | None = Query(default=None),
    ) -> dict[str, Any]:
        init_database()
        today = date.today()
        y = year or today.year
        m = month
        eff_profile = None if consolidated else profile_id
        data = get_dashboard_data(
            profile_id=eff_profile,
            consolidated=consolidated,
            year=y,
            month=m,
        )
        spend = get_spendable_amount(
            profile_id=eff_profile,
            consolidated=consolidated,
            year=y,
            month=m or today.month,
        )
        try:
            due_dates = get_upcoming_due_dates(
                profile_id=eff_profile,
                consolidated=consolidated,
                days_ahead=30,
            )
        except Exception:
            due_dates = []
        data["spendable"] = spend
        data["due_dates"] = due_dates[:6]
        return _to_json_safe(data)

    @app.get("/api/transactions")
    def list_transactions(
        profile_id: int | None = Query(default=None),
        consolidated: bool = Query(default=True),
        year: int | None = Query(default=None),
        month: int | None = Query(default=None),
        q: str = Query(default=""),
        type_filter: Literal["all", "income", "expense"] = Query(default="all"),
        category_id: int | None = Query(default=None),
        card_id: int | None = Query(default=None),
        sort: Literal["date_desc", "date_asc", "amount_desc", "amount_asc"] = Query(default="date_desc"),
        limit: int = Query(default=500, ge=1, le=2000),
    ) -> dict[str, Any]:
        init_database()
        today = date.today()
        y = year or today.year
        if month:
            start = date(y, month, 1)
            end = date(y, month, monthrange(y, month)[1])
        else:
            start = date(y, 1, 1)
            end = date(y, 12, 31)

        query_text = q.strip()
        loader = search_transactions if query_text else get_transactions
        kwargs: dict[str, Any] = dict(start_date=start, end_date=end, limit=limit)
        if query_text:
            kwargs["query"] = query_text
        if consolidated:
            txs = loader(active_profiles_only=True, **kwargs)
        elif profile_id:
            txs = loader(profile_id=profile_id, **kwargs)
        else:
            txs = []

        if type_filter == "income":
            txs = [tx for tx in txs if tx.type == TransactionType.INCOME]
        elif type_filter == "expense":
            txs = [tx for tx in txs if tx.type == TransactionType.EXPENSE]
        if category_id is not None:
            txs = [tx for tx in txs if tx.category_id == category_id]
        if card_id is not None:
            txs = [tx for tx in txs if tx.credit_card_id == card_id]

        if sort == "date_asc":
            txs.sort(key=lambda tx: (tx.date, tx.id or 0))
        elif sort == "amount_desc":
            txs.sort(key=lambda tx: (Decimal(str(tx.amount)), tx.date), reverse=True)
        elif sort == "amount_asc":
            txs.sort(key=lambda tx: (Decimal(str(tx.amount)), tx.date))
        else:
            txs.sort(key=lambda tx: (tx.date, tx.id or 0), reverse=True)

        income_total = sum((tx.amount for tx in txs if tx.type == TransactionType.INCOME), Decimal("0"))
        expense_total = sum((tx.amount for tx in txs if tx.type == TransactionType.EXPENSE), Decimal("0"))

        cat_map = {c.id: c for c in get_all_categories()}
        prof_map = {p.id: p for p in get_all_profiles()}
        card_map = {cd.id: cd for cd in get_credit_cards(None)}

        items = []
        for tx in txs:
            cat = cat_map.get(tx.category_id)
            prof = prof_map.get(tx.profile_id)
            card = card_map.get(tx.credit_card_id) if tx.credit_card_id else None
            items.append(
                {
                    "id": tx.id,
                    "profile_id": tx.profile_id,
                    "profile_name": prof.name if prof else "",
                    "profile_color": prof.color if prof else "#14B8A6",
                    "date": tx.date.isoformat(),
                    "description": tx.description,
                    "amount": float(tx.amount),
                    "category_id": tx.category_id,
                    "category_name": display_name(cat) if cat else "",
                    "category_icon": (cat.icon or "") if cat else "",
                    "category_color": (getattr(cat, "color", None) or ("#22C55E" if tx.type == TransactionType.INCOME else "#14B8A6")) if cat else "#64748B",
                    "type": tx.type.value,
                    "credit_card_id": tx.credit_card_id,
                    "credit_card_name": card.name if card else None,
                    "notes": tx.notes,
                    "is_recurring": bool(tx.is_recurring),
                }
            )

        return _to_json_safe(
            {
                "items": items,
                "totals": {
                    "income": income_total,
                    "expense": expense_total,
                    "net": income_total - expense_total,
                    "count": len(items),
                },
            }
        )

    @app.post("/api/transactions")
    def create_tx(payload: TransactionPayload) -> dict[str, Any]:
        init_database()
        tx = create_transaction(
            Transaction(
                profile_id=payload.profile_id,
                date=payload.date,
                description=payload.description.strip(),
                amount=payload.amount,
                category_id=payload.category_id,
                type=TransactionType(payload.type),
                credit_card_id=payload.credit_card_id,
                notes=payload.notes,
                is_recurring=payload.is_recurring,
            )
        )
        return _to_json_safe({"id": tx.id})

    @app.put("/api/transactions/{tx_id}")
    def update_tx(tx_id: int, payload: TransactionPayload) -> dict[str, Any]:
        existing = get_transaction(tx_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Transaction not found")
        ok = update_transaction(
            Transaction(
                id=tx_id,
                profile_id=payload.profile_id,
                date=payload.date,
                description=payload.description.strip(),
                amount=payload.amount,
                category_id=payload.category_id,
                type=TransactionType(payload.type),
                credit_card_id=payload.credit_card_id,
                notes=payload.notes,
                is_recurring=payload.is_recurring,
            )
        )
        if not ok:
            raise HTTPException(status_code=500, detail="Could not update transaction")
        return {"updated": True, "id": tx_id}

    @app.delete("/api/transactions/{tx_id}")
    def soft_delete_tx(tx_id: int) -> dict[str, Any]:
        removed = soft_delete_transactions([tx_id])
        if not removed:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return {"deleted": removed, "id": tx_id}

    @app.post("/api/transactions/restore")
    def restore_txs(payload: IdsPayload) -> dict[str, Any]:
        restored = restore_transactions(payload.ids)
        return {"restored": restored}

    @app.post("/api/transactions/batch-category")
    def batch_category(payload: BatchCategoryPayload) -> dict[str, Any]:
        updated = update_transactions_category_batch(payload.ids, payload.category_id)
        return {"updated": updated}

    @app.post("/api/transactions/batch-delete")
    def batch_delete(payload: IdsPayload) -> dict[str, Any]:
        removed = delete_transactions_batch(payload.ids)
        return {"deleted": removed}

    from api.routes_personal import router as personal_router
    from api.routes_mei import router as mei_router

    app.include_router(personal_router)
    app.include_router(mei_router)

    # Serve compiled React frontend if available
    if FRONTEND_DIST.exists():
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}")
        def serve_spa(full_path: str):
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")
            candidate = FRONTEND_DIST / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
