"""MEI profile entity — DAS, limits, and obligation rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING
from typing import Any, Dict, Literal, Optional

from core.models import MeiConfig

DAS_AMOUNTS: Dict[str, Decimal] = {
    "comercio": Decimal("71.60"),
    "industria": Decimal("71.60"),
    "servico": Decimal("75.90"),
    "comercio_servico": Decimal("76.60"),
}

MEI_ANNUAL_LIMIT_DEFAULT = Decimal("81000")
DAS_DUE_DAY = 20

ActivityType = Literal["comercio", "servico", "industria", "comercio_servico"]


@dataclass
class MeiProfile:
    """MEI business rules backed by persisted configuration."""

    config: MeiConfig

    @property
    def profile_id(self) -> int:
        return self.config.profile_id

    @property
    def annual_limit(self) -> Decimal:
        return Decimal(str(self.config.annual_limit))

    def das_amount(self) -> Decimal:
        custom = self.config.custom_das_amount
        if custom is not None and custom > 0:
            return Decimal(str(custom))
        return DAS_AMOUNTS.get(self.config.activity_type, DAS_AMOUNTS["servico"])

    def das_due_info(self, today: Optional[date] = None) -> Dict[str, Any]:
        """Days until next DAS due date (default: day 20)."""
        today = today or date.today()
        due_day = self.config.das_day or DAS_DUE_DAY
        if today.day <= due_day:
            due = today.replace(day=due_day)
        else:
            if today.month == 12:
                due = date(today.year + 1, 1, due_day)
            else:
                due = date(today.year, today.month + 1, due_day)

        days_left = (due - today).days
        return {
            "due_date": due,
            "days_left": days_left,
            "is_urgent": days_left <= 5,
            "reference_month": due.month,
        }

    def das_payment_description(self, payment_date: date) -> str:
        return f"DAS MEI {payment_date.month:02d}/{payment_date.year}"

    def revenue_limit_status(
        self,
        ytd_revenue: Decimal,
        today: Optional[date] = None,
    ) -> Dict[str, Any]:
        today = today or date.today()
        limit = self.annual_limit
        pct = float((ytd_revenue / limit * 100)) if limit > 0 else 0.0
        projected_date = self.project_limit_reach_date(ytd_revenue, today)

        months_elapsed = today.month
        projected_annual = (
            (ytd_revenue / months_elapsed * 12) if months_elapsed > 0 else Decimal("0")
        )

        return {
            "ytd_revenue": ytd_revenue,
            "annual_limit": limit,
            "percentage": min(round(pct, 1), 100.0),
            "remaining": max(limit - ytd_revenue, Decimal("0")),
            "projected_annual": projected_annual.quantize(Decimal("0.01")),
            "projected_limit_date": projected_date,
            "at_risk": pct >= 80,
            "exceeded": ytd_revenue >= limit,
        }

    def project_limit_reach_date(
        self,
        ytd_revenue: Decimal,
        today: Optional[date] = None,
    ) -> Optional[date]:
        """Project when annual revenue limit would be reached at current pace."""
        today = today or date.today()
        limit = self.annual_limit
        if ytd_revenue <= 0:
            return None
        if ytd_revenue >= limit:
            return today

        start = date(today.year, 1, 1)
        days_elapsed = max((today - start).days + 1, 1)
        daily_rate = ytd_revenue / Decimal(days_elapsed)
        if daily_rate <= 0:
            return None

        remaining = limit - ytd_revenue
        days_to_limit = int(
            (remaining / daily_rate).to_integral_value(rounding=ROUND_CEILING)
        )
        return today + timedelta(days=days_to_limit)