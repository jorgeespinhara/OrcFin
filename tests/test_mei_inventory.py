"""MEI light inventory."""

from datetime import date
from decimal import Decimal

from core.db.repositories.mei_inventory import create_product, get_product, record_movement
from core.db.schema import init_database
from core.mei_inventory_summary import get_inventory_summary
from core.models import MeiProduct, MeiStockMovement
from core.services.mei_service import create_mei_profile


def _setup_mei(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "test.db"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    init_database()
    profile, _ = create_mei_profile(
        "Loja",
        "Comercio ME",
        "33.333.333/0001-33",
        operational_profile="sales",
    )
    return profile.id


def test_product_stock_movements(project_tmp_path, monkeypatch):
    pid = _setup_mei(project_tmp_path, monkeypatch)
    product = create_product(
        MeiProduct(
            profile_id=pid,
            name="Camiseta",
            unit_price=Decimal("49.90"),
            cost_price=Decimal("25"),
            stock_qty=Decimal("5"),
            low_stock_threshold=Decimal("3"),
        )
    )

    record_movement(
        MeiStockMovement(
            product_id=int(product.id),
            movement_type="out",
            quantity=Decimal("3"),
            movement_date=date.today(),
        ),
        profile_id=pid,
    )
    updated = get_product(int(product.id))
    assert Decimal(str(updated["stock_qty"])) == Decimal("2")

    summary = get_inventory_summary(pid)
    assert summary["product_count"] == 1
    assert summary["low_stock_count"] == 1
    assert summary["stock_value"] == Decimal("50")


def test_stock_out_blocks_negative(project_tmp_path, monkeypatch):
    pid = _setup_mei(project_tmp_path, monkeypatch)
    product = create_product(
        MeiProduct(profile_id=pid, name="Caneca", stock_qty=Decimal("1")),
    )
    result = record_movement(
        MeiStockMovement(
            product_id=int(product.id),
            movement_type="out",
            quantity=Decimal("5"),
            movement_date=date.today(),
        ),
        profile_id=pid,
    )
    assert result is None
    assert Decimal(str(get_product(int(product.id))["stock_qty"])) == Decimal("1")