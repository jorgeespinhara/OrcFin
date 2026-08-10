"""System category slugs — stable keys for i18n and seeds."""

from __future__ import annotations

# (slug, type, icon, seed_name_pt) — seed_name keeps demo/back-compat lookups
PERSONAL_CATEGORY_SEED: tuple[tuple[str, str, str, str], ...] = (
    ("salary", "income", "💼", "Salário"),
    ("side_income", "income", "💰", "Renda Extra / Freelance"),
    ("investments_income", "income", "📈", "Investimentos (Dividendos/Juros)"),
    ("rent_income", "income", "🏠", "Aluguel Recebido"),
    ("other_income", "income", "📥", "Outros Rendimentos"),
    ("housing", "expense", "🏡", "Moradia (Aluguel/Financiamento/Condomínio)"),
    ("food", "expense", "🛒", "Alimentação (Mercado + Refeições)"),
    ("transport", "expense", "🚗", "Transporte (Combustível/Uber/Transporte Público)"),
    ("health", "expense", "🏥", "Saúde (Plano + Medicamentos + Consultas)"),
    ("education", "expense", "📚", "Educação (Escola/Cursos)"),
    ("leisure", "expense", "🎮", "Lazer e Entretenimento"),
    ("subscriptions", "expense", "📱", "Assinaturas (Streaming, Apps, etc.)"),
    ("utilities", "expense", "💡", "Utilities (Luz, Água, Gás, Internet)"),
    ("insurance", "expense", "🛡️", "Seguros (Vida, Auto, Residencial)"),
    ("personal_care", "expense", "👕", "Roupas e Cuidados Pessoais"),
    ("travel", "expense", "✈️", "Viagens e Férias"),
    ("gifts", "expense", "🎁", "Presentes e Doações"),
    ("maintenance", "expense", "🔧", "Manutenção e Reparos"),
    ("taxes", "expense", "📋", "Impostos e Taxas"),
    ("other_expense", "expense", "📦", "Outros Gastos"),
)

MEI_CATEGORY_SEED: tuple[tuple[str, str, str, str, int], ...] = (
    # slug, type, icon, name_pt, is_mei_deductible
    ("mei_revenue", "income", "💼", "Receita MEI", 0),
    ("mei_das", "expense", "📋", "DAS / Impostos MEI", 0),
    ("mei_materials", "expense", "📦", "Materiais e Insumos", 1),
    ("mei_admin", "expense", "🗂️", "Despesas Administrativas MEI", 1),
    ("mei_equipment", "expense", "🛠️", "Equipamentos MEI", 0),
    ("mei_marketing", "expense", "📣", "Marketing MEI", 1),
)

# Legacy Portuguese name → slug (migration backfill)
NAME_TO_SLUG: dict[str, str] = {
    **{name: slug for slug, _t, _i, name in PERSONAL_CATEGORY_SEED},
    **{name: slug for slug, _t, _i, name, _d in MEI_CATEGORY_SEED},
}


def category_label(slug: str | None, fallback_name: str) -> str:
    """Localized label for a system category slug."""
    if not slug:
        return fallback_name
    from core.i18n import t

    key = f"category.{slug}"
    text = t(key)
    return fallback_name if text == key else text
