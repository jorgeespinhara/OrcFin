"""MEI profile and fiscal data for subviews."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

import flet as ft

from core.db.repositories.mei import (
    get_mei_clients,
    get_mei_config,
    get_mei_deductible_category_ids,
    get_mei_profile,
)
from core.domain.entities.mei_profile import MeiProfile
from core.mei import (
    get_invoice_reconciliation,
    get_mei_dashboard_data,
    get_revenue_limit_status,
    get_simplified_report,
)
from core.services.mei_service import das_payment_exists

if TYPE_CHECKING:
    from ui.shell import OrcFinApp


@dataclass
class MeiContext:
    profile_id: Optional[int]
    profile_name: str
    razao_social: str
    cnpj: str
    activity_type: str
    operational_profile: str
    cnae: str | None
    annual_limit: Decimal
    custom_das_amount: Optional[float]
    das_info: dict
    das_amount: Decimal
    das_paid: bool
    limit_status: dict
    dashboard: dict
    report: dict
    reconciliation: dict
    client_count: int

    @classmethod
    def load(cls) -> "MeiContext":
        profile = get_mei_profile()
        if not profile:
            return cls.empty()

        config = get_mei_config(profile.id)
        if not config:
            return cls.empty()

        entity = MeiProfile(config)
        limit = entity.annual_limit
        today = date.today()

        return cls(
            profile_id=profile.id,
            profile_name=profile.name,
            razao_social=config.razao_social,
            cnpj=config.cnpj,
            activity_type=config.activity_type,
            operational_profile=config.operational_profile,
            cnae=config.cnae,
            annual_limit=limit,
            custom_das_amount=config.custom_das_amount,
            das_info=entity.das_due_info(),
            das_amount=entity.das_amount(),
            das_paid=das_payment_exists(profile.id, today.year, today.month),
            limit_status=get_revenue_limit_status(profile.id, limit),
            dashboard=get_mei_dashboard_data(profile.id),
            report=get_simplified_report(
                profile.id,
                deductible_category_ids=get_mei_deductible_category_ids(),
            ),
            reconciliation=get_invoice_reconciliation(profile.id),
            client_count=len(get_mei_clients(profile.id)),
        )

    @classmethod
    def empty(cls) -> "MeiContext":
        return cls(
            profile_id=None,
            profile_name="",
            razao_social="",
            cnpj="",
            activity_type="servico",
            operational_profile="on_demand",
            cnae=None,
            annual_limit=Decimal("81000"),
            custom_das_amount=None,
            das_info={},
            das_amount=Decimal("0"),
            das_paid=False,
            limit_status={},
            dashboard={},
            report={},
            reconciliation={},
            client_count=0,
        )

    @property
    def is_ready(self) -> bool:
        return self.profile_id is not None


def require_mei_ready(app: "OrcFinApp", ctx: MeiContext) -> ft.Control | None:
    """Return setup UI when MEI profile is missing; None when ready."""
    if ctx.is_ready:
        return None
    from ui.mei.setup import build_setup
    return build_setup(app)