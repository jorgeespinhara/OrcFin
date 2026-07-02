"""MEI recurring subscriptions and charges."""

from datetime import date
from decimal import Decimal

from core.db.repositories.mei import create_mei_client
from core.db.repositories.mei_recurring import (
    create_subscription,
    list_charges_for_month,
    receive_charge_payment,
)
from core.db.schema import init_database
from core.mei_recurring_billing import get_monthly_recurring_summary
from core.models import MeiClient, MeiSubscription
from core.services.mei_service import create_mei_profile


def _setup_mei(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "test.db"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    init_database()
    profile, _ = create_mei_profile(
        "Monitoramento",
        "TI ME",
        "22.222.222/0001-22",
        operational_profile="recurring",
    )
    return profile.id


def test_subscription_generates_charge_and_payment(project_tmp_path, monkeypatch):
    pid = _setup_mei(project_tmp_path, monkeypatch)
    client = create_mei_client(MeiClient(profile_id=pid, name="Cliente Fixo"))
    create_subscription(
        MeiSubscription(
            profile_id=pid,
            client_id=client.id,
            name="Mensalidade suporte",
            monthly_amount=Decimal("350"),
            due_day=10,
            start_date=date.today().replace(day=1),
        )
    )

    summary = get_monthly_recurring_summary(pid)
    assert summary["charge_count"] == 1
    assert summary["pending_total"] == Decimal("350")

    charges = list_charges_for_month(pid, date.today().year, date.today().month, unpaid_only=True)
    tx_id = receive_charge_payment(pid, int(charges[0]["id"]))
    assert tx_id is not None

    summary_after = get_monthly_recurring_summary(pid)
    assert summary_after["pending_total"] == Decimal("0")
    assert summary_after["received_total"] == Decimal("350")


def test_paused_subscription_skips_new_charge(project_tmp_path, monkeypatch):
    from core.db.repositories.mei_recurring import update_subscription_status

    pid = _setup_mei(project_tmp_path, monkeypatch)
    sub = create_subscription(
        MeiSubscription(
            profile_id=pid,
            name="Plano pausado",
            monthly_amount=Decimal("100"),
            due_day=5,
            start_date=date.today().replace(day=1),
        )
    )
    get_monthly_recurring_summary(pid)
    update_subscription_status(int(sub.id), "paused")

    charges = list_charges_for_month(pid, date.today().year, date.today().month)
    assert len(charges) == 1
    assert charges[0]["paid_at"] is None