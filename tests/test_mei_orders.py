"""MEI orders, suppliers, and payables."""

from datetime import date
from decimal import Decimal

from core.db.repositories.mei import create_mei_client
from core.db.repositories.mei_orders import (
    add_outsource,
    create_order,
    create_supplier,
    get_orders,
    list_unpaid_outsource,
    pay_outsource_line,
)
from core.db.schema import init_database
from core.mei_payables import get_monthly_payables_summary
from core.models import MeiClient, MeiOrder, MeiOrderOutsource, MeiSupplier
from core.services.mei_service import create_mei_profile


def _setup_mei(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "test.db"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    init_database()
    profile, _ = create_mei_profile(
        "Facção",
        "Costura ME",
        "11.111.111/0001-11",
        operational_profile="by_order",
    )
    return profile.id


def test_order_outsource_and_payment(project_tmp_path, monkeypatch):
    pid = _setup_mei(project_tmp_path, monkeypatch)
    supplier = create_supplier(MeiSupplier(profile_id=pid, name="Maria Costura"))
    client = create_mei_client(MeiClient(profile_id=pid, name="Loja A"))
    order = create_order(
        MeiOrder(
            profile_id=pid,
            client_id=client.id,
            reference="PED-001",
            revenue_amount=Decimal("500"),
            order_date=date.today(),
        )
    )
    add_outsource(
        MeiOrderOutsource(
            order_id=order.id,
            supplier_id=supplier.id,
            amount=Decimal("180"),
            sent_date=date.today(),
        )
    )

    summary = get_monthly_payables_summary(pid)
    assert summary["order_count"] == 1
    assert summary["outsourced_count"] == 1
    assert summary["payable_total"] == Decimal("180")

    unpaid = list_unpaid_outsource(pid, date.today().year, date.today().month)
    tx_id = pay_outsource_line(pid, int(unpaid[0]["line_id"]))
    assert tx_id is not None
    assert list_unpaid_outsource(pid, date.today().year, date.today().month) == []


def test_in_house_order_has_no_payable(project_tmp_path, monkeypatch):
    pid = _setup_mei(project_tmp_path, monkeypatch)
    create_order(
        MeiOrder(
            profile_id=pid,
            reference="PED-002",
            revenue_amount=Decimal("300"),
            order_date=date.today(),
        )
    )
    summary = get_monthly_payables_summary(pid)
    assert summary["in_house_count"] == 1
    assert summary["outsourced_count"] == 0
    assert len(get_orders(pid)) == 1