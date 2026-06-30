"""MEI → ME (Simples Nacional) migration tax simulator — offline estimates."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.domain.entities.mei_profile import MEI_ANNUAL_LIMIT_DEFAULT, MeiProfile
from core.models import MeiConfig

# Alíquotas nominais simplificadas do Simples Nacional (Anexos I–V) — referência educativa
SIMPLES_NOMINAL_RATES: Dict[str, List[Dict[str, Any]]] = {
    "comercio": [
        {"up_to": Decimal("180000"), "rate": Decimal("0.04")},
        {"up_to": Decimal("360000"), "rate": Decimal("0.073")},
        {"up_to": Decimal("720000"), "rate": Decimal("0.095")},
    ],
    "servico": [
        {"up_to": Decimal("180000"), "rate": Decimal("0.06")},
        {"up_to": Decimal("360000"), "rate": Decimal("0.112")},
        {"up_to": Decimal("720000"), "rate": Decimal("0.135")},
    ],
    "industria": [
        {"up_to": Decimal("180000"), "rate": Decimal("0.045")},
        {"up_to": Decimal("360000"), "rate": Decimal("0.078")},
        {"up_to": Decimal("720000"), "rate": Decimal("0.10")},
    ],
    "comercio_servico": [
        {"up_to": Decimal("180000"), "rate": Decimal("0.045")},
        {"up_to": Decimal("360000"), "rate": Decimal("0.085")},
        {"up_to": Decimal("720000"), "rate": Decimal("0.115")},
    ],
}

MEI_ANNUAL_DAS_MONTHS = 12
ME_MIGRATION_THRESHOLD_PCT = 70.0


def _nominal_rate_for_revenue(activity_type: str, annual_revenue: Decimal) -> Decimal:
    brackets = SIMPLES_NOMINAL_RATES.get(activity_type, SIMPLES_NOMINAL_RATES["servico"])
    for bracket in brackets:
        if annual_revenue <= bracket["up_to"]:
            return bracket["rate"]
    return brackets[-1]["rate"]


def _das_amount(activity_type: str, custom_das: Optional[float] = None) -> Decimal:
    config = MeiConfig(
        profile_id=0,
        razao_social="",
        cnpj="",
        activity_type=activity_type,  # type: ignore[arg-type]
        custom_das_amount=custom_das,
    )
    return MeiProfile(config).das_amount()


def estimate_mei_annual_tax(activity_type: str, custom_das: Optional[float] = None) -> Decimal:
    monthly = _das_amount(activity_type, custom_das)
    return (monthly * MEI_ANNUAL_DAS_MONTHS).quantize(Decimal("0.01"))


def estimate_simples_annual_tax(activity_type: str, annual_revenue: Decimal) -> Decimal:
    if annual_revenue <= 0:
        return Decimal("0")
    rate = _nominal_rate_for_revenue(activity_type, annual_revenue)
    return (annual_revenue * rate).quantize(Decimal("0.01"))


def simulate_me_migration(
    ytd_revenue: Decimal,
    projected_annual: Decimal,
    activity_type: str = "servico",
    custom_das: Optional[float] = None,
    annual_limit: Optional[Decimal] = None,
) -> Dict[str, Any]:
    """Compare MEI fixed DAS vs rough Simples Nacional estimate for ME."""
    limit = annual_limit or MEI_ANNUAL_LIMIT_DEFAULT
    mei_annual = estimate_mei_annual_tax(activity_type, custom_das)
    simples_projected = estimate_simples_annual_tax(activity_type, projected_annual)
    simples_at_limit = estimate_simples_annual_tax(activity_type, limit)

    limit_pct = float((ytd_revenue / limit * 100)) if limit > 0 else 0.0
    exceeds_mei = projected_annual > limit

    monthly_mei = _das_amount(activity_type, custom_das)
    monthly_simples = (simples_projected / 12).quantize(Decimal("0.01")) if projected_annual > 0 else Decimal("0")
    delta_annual = simples_projected - mei_annual

    recommendation = "permanecer_mei"
    if exceeds_mei:
        recommendation = "migrar_obrigatorio"
    elif limit_pct >= ME_MIGRATION_THRESHOLD_PCT:
        recommendation = "avaliar_migracao"
    elif delta_annual > mei_annual * Decimal("0.5"):
        recommendation = "avaliar_migracao"

    return {
        "ytd_revenue": ytd_revenue,
        "projected_annual": projected_annual,
        "annual_limit": limit,
        "limit_usage_pct": round(limit_pct, 1),
        "exceeds_mei_limit": exceeds_mei,
        "mei_annual_tax": mei_annual,
        "mei_monthly_das": monthly_mei,
        "simples_annual_tax_projected": simples_projected,
        "simples_annual_tax_at_limit": simples_at_limit,
        "simples_monthly_estimate": monthly_simples,
        "annual_tax_delta": delta_annual,
        "recommendation": recommendation,
        "activity_type": activity_type,
        "disclaimer": "Estimativa educativa. Consulte um contador para decisão formal.",
    }