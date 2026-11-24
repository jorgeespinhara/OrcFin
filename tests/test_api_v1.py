"""API tests for the local FastAPI backend used by the PRO desktop UI."""

from datetime import date

from fastapi.testclient import TestClient

from api.server import create_app
from core.db.repositories.categories import create_category
from core.db.repositories.profiles import create_profile
from core.models import TransactionType


def test_api_meta_dashboard_and_transactions_crud(fresh_db, project_tmp_path, monkeypatch):
    monkeypatch.setattr("core.settings_store.CONFIG_FILE", project_tmp_path / "settings.json")
    p = create_profile("Jorge")
    c_exp = create_category("Alimentação", TransactionType.EXPENSE)
    c_other = create_category("Lazer", TransactionType.EXPENSE)

    client = TestClient(create_app())

    meta = client.get("/api/meta")
    assert meta.status_code == 200
    body = meta.json()
    assert body["version"] == "1.0.0"
    assert any(prof["id"] == p.id for prof in body["profiles"])

    today = date.today()
    created = client.post(
        "/api/transactions",
        json={
            "profile_id": p.id,
            "date": today.isoformat(),
            "description": "Café especial",
            "amount": 32.5,
            "category_id": c_exp.id,
            "type": "expense",
        },
    )
    assert created.status_code == 200
    tx_id = created.json()["id"]

    listing = client.get(
        "/api/transactions",
        params={"year": today.year, "month": today.month, "consolidated": "true"},
    )
    assert listing.status_code == 200
    assert listing.json()["totals"]["count"] == 1
    assert listing.json()["items"][0]["description"] == "Café especial"

    dash = client.get(
        "/api/dashboard",
        params={"year": today.year, "month": today.month, "consolidated": "true"},
    )
    assert dash.status_code == 200
    assert dash.json()["current_month"]["total_expense"] == 32.5

    # Soft delete + Undo restore
    deleted = client.delete(f"/api/transactions/{tx_id}")
    assert deleted.status_code == 200
    after_del = client.get(
        "/api/transactions",
        params={"year": today.year, "month": today.month, "consolidated": "true"},
    )
    assert after_del.json()["totals"]["count"] == 0

    restored = client.post("/api/transactions/restore", json={"ids": [tx_id]})
    assert restored.status_code == 200
    assert restored.json()["restored"] == 1

    # Batch category update
    batch = client.post(
        "/api/transactions/batch-category",
        json={"ids": [tx_id], "category_id": c_other.id},
    )
    assert batch.status_code == 200
    assert batch.json()["updated"] == 1

    # Phase 2 endpoints smoke checks
    card = client.post(
        "/api/cards",
        json={"profile_id": p.id, "name": "Nubank", "credit_limit": 5000, "due_day": 10, "closing_day": 3},
    )
    assert card.status_code == 200
    assert len(client.get("/api/cards").json()["items"]) == 1

    assert client.post("/api/goals", json={"name": "Reserva", "target_amount": 10000}).status_code == 200
    assert client.get("/api/reports").status_code == 200
    assert client.get("/api/settings").status_code == 200
    assert client.get("/api/investments", params={"profile_id": p.id}).status_code == 200
    assert client.get("/api/net-worth", params={"profile_id": p.id}).status_code == 200

    # Phase 3 MEI + Onboarding endpoints
    assert client.get("/api/mei/overview").json()["configured"] is False
    mei_setup = client.post(
        "/api/mei/setup",
        json={"razao_social": "Jorge MEI", "cnpj": "12.345.678/0001-99", "activity_type": "servico"},
    )
    assert mei_setup.status_code == 200
    assert client.get("/api/mei/overview").json()["configured"] is True
    assert client.post("/api/mei/clients", json={"name": "Cliente A"}).status_code == 200
    assert client.post("/api/onboarding/complete", json={"country": "BR", "setup_mode": "both", "use_demo": False}).status_code == 200
