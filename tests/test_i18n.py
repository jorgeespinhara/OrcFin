"""Locale, country profile, and money formatting."""

from datetime import date
from decimal import Decimal

from core.domain.locale_format import format_display_date, format_display_month_day
from core.domain.value_objects.money import format_brl, format_money
from core.i18n import (
    apply_locale_settings,
    clear_locale_cache,
    get_country,
    get_currency,
    get_locale,
    supports_mei,
    t,
)
from core.import_parsers.registry import list_parsers
from core.settings_store import DEFAULT_SETTINGS, load_settings, save_settings


def setup_function():
    apply_locale_settings(locale="pt-BR", country_profile="BR", currency="BRL")


def test_t_pt_and_en():
    apply_locale_settings(locale="pt-BR")
    assert t("nav.transactions") == "Lançamentos"
    apply_locale_settings(locale="en-US")
    assert t("nav.transactions") == "Transactions"
    apply_locale_settings(locale="es-ES")
    assert t("nav.transactions") == "Movimientos"


def test_supports_mei_by_country():
    assert supports_mei("BR") is True
    assert supports_mei("US") is False
    assert supports_mei("ES") is False


def test_detect_system_locale_returns_supported():
    from core.i18n import SUPPORTED_LOCALES, detect_system_country, detect_system_locale

    assert detect_system_locale() in SUPPORTED_LOCALES
    assert detect_system_country() in ("BR", "US", "ES")


def test_country_native_names_fixed():
    from core.i18n import COUNTRY_PRESETS

    assert COUNTRY_PRESETS["BR"]["native_name"] == "Brasil"
    assert COUNTRY_PRESETS["US"]["native_name"] == "United States"
    assert COUNTRY_PRESETS["ES"]["native_name"] == "España"


def test_category_slug_and_label(fresh_db):
    from core.categories_catalog import category_label
    from core.db.repositories.categories import get_all_categories, get_category_by_slug
    from core.i18n import apply_locale_settings, clear_locale_cache

    food = get_category_by_slug("food")
    assert food is not None
    assert food.slug == "food"
    clear_locale_cache()
    apply_locale_settings(locale="en-US")
    assert category_label("food", food.name) == "Food (groceries + dining)"
    apply_locale_settings(locale="pt-BR")
    assert any(c.slug for c in get_all_categories())


def test_onboarding_flow_has_welcome_before_mode():
    from ui.onboarding.view import _step_flow

    flow = _step_flow("personal", "BR")
    assert flow[0] == "welcome"
    assert flow[1] == "mode"
    assert "locale" not in flow  # country flags live on welcome
    assert "mei_profile" not in _step_flow("personal", "US")
    assert "mei_profile" in _step_flow("mei", "BR")
    assert "mei_profile" not in _step_flow("mei", "US")


def test_format_money_currencies():
    assert format_money(Decimal("1234.56"), "BRL") == "R$ 1.234,56"
    assert format_money(Decimal("1234.56"), "USD") == "$1,234.56"
    assert format_money(Decimal("1234.56"), "EUR") == "1.234,56 €"
    assert format_money(Decimal("-50.5"), "BRL") == "-R$ 50,50"


def test_format_brl_uses_active_currency():
    apply_locale_settings(currency="USD")
    assert format_brl(Decimal("10")) == "$10.00"
    apply_locale_settings(currency="BRL")
    assert format_brl(Decimal("10")) == "R$ 10,00"


def test_display_date_locale():
    d = date(2024, 2, 1)
    assert format_display_date(d, "en-US") == "02/01/2024"
    assert format_display_date(d, "pt-BR") == "01/02/2024"
    assert format_display_month_day(d, "en-US") == "02/01"


def test_parsers_filtered_by_country():
    br_ids = {p["id"] for p in list_parsers("BR")}
    us_ids = {p["id"] for p in list_parsers("US")}
    assert "nubank_csv" in br_ids
    assert "ofx" in us_ids
    assert "generic_csv" in us_ids
    assert "nubank_csv" not in us_ids


def test_settings_defaults_include_locale(project_tmp_path, monkeypatch):
    cfg = project_tmp_path / "settings.json"
    monkeypatch.setattr("core.settings_store.CONFIG_FILE", cfg)
    settings = load_settings()
    assert settings["locale"] == "pt-BR"
    assert settings["country_profile"] == "BR"
    assert settings["currency"] == "BRL"


def test_pdf_and_seed_keys_localized():
    clear_locale_cache()
    apply_locale_settings(locale="en-US")
    assert t("pdf.receipt_title") == "SERVICE RECEIPT"
    assert t("seed.profile_1") == "User 1"
    assert t("pdf.page", n=3) == "Page 3"
    apply_locale_settings(locale="pt-BR")
    assert t("pdf.receipt_title") == "RECIBO DE PRESTAÇÃO DE SERVIÇOS"
    assert t("seed.profile_1") == "Usuário 1"


def test_ai_gateway_errors_localized(fresh_db):
    from core.ai.gateway import request_financial_insights, test_connection
    from core.network_policy import blocked_message

    clear_locale_cache()
    apply_locale_settings(locale="en-US")
    bad = request_financial_insights(
        provider="not-a-provider",
        api_key="x",
        context="ctx — no PII",
        use_fallback_on_error=False,
    )
    assert bad.error and "Unsupported provider" in bad.error

    no_key = request_financial_insights(
        provider="grok",
        api_key="",
        context="ctx — no PII",
        use_fallback_on_error=False,
    )
    assert no_key.error and "API key" in no_key.error and "Settings" in no_key.error

    offline = test_connection(
        "grok",
        "fake",
        settings={"strict_offline": True},
    )
    assert offline["success"] is False
    assert blocked_message() == offline["error"]
    assert "offline" in offline["error"].lower() or "Strict" in offline["error"]

    apply_locale_settings(locale="pt-BR")
    bad_pt = request_financial_insights(
        provider="not-a-provider",
        api_key="x",
        context="ctx — no PII",
        use_fallback_on_error=False,
    )
    assert bad_pt.error and "Provedor não suportado" in bad_pt.error


def test_settings_persist_country_profile(project_tmp_path, monkeypatch):
    cfg = project_tmp_path / "settings.json"
    monkeypatch.setattr("core.settings_store.CONFIG_FILE", cfg)
    data = dict(DEFAULT_SETTINGS)
    data["country_profile"] = "US"
    data["locale"] = "en-US"
    data["currency"] = "USD"
    save_settings(data)
    loaded = load_settings()
    assert loaded["country_profile"] == "US"
    assert loaded["locale"] == "en-US"
    assert loaded["currency"] == "USD"
    assert get_country() == "US"
    assert get_locale() == "en-US"
    assert get_currency() == "USD"
