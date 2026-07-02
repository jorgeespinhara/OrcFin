"""MEI operational profiles and CNAE suggestion."""

from core.db.repositories.mei import get_mei_config
from core.db.schema import init_database
from core.mei_operational import enabled_modules, profile_label, suggest_profile
from core.services.mei_service import create_mei_profile


def test_suggest_profile_by_cnae():
    assert suggest_profile("1412602") == "by_order"
    assert suggest_profile("4711301") == "sales"
    assert suggest_profile("6201501") == "on_demand"
    assert suggest_profile("9602501") == "mixed"
    assert suggest_profile("") == "on_demand"


def test_enabled_modules_for_order_profile():
    mods = enabled_modules("by_order")
    assert "orders" in mods
    assert "core" in mods


def test_enabled_modules_for_recurring_profile():
    mods = enabled_modules("recurring")
    assert "recurring_billing" in mods
    assert "orders" not in mods


def test_enabled_modules_for_sales_profile():
    mods = enabled_modules("sales")
    assert "inventory" in mods
    assert "orders" not in mods


def test_enabled_modules_for_mixed_profile():
    mods = enabled_modules("mixed")
    assert "orders" in mods
    assert "inventory" in mods


def test_create_mei_profile_stores_operational_profile(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "test.db"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    init_database()
    profile, _ = create_mei_profile(
        name="Facção",
        razao_social="Costura ME",
        cnpj="12.345.678/0001-90",
        activity_type="industria",
        operational_profile="by_order",
        cnae="1412602",
    )
    cfg = get_mei_config(profile.id)
    assert cfg is not None
    assert cfg.operational_profile == "by_order"
    assert cfg.cnae == "1412602"
    assert profile_label(cfg.operational_profile) == "Serviço por pedido"