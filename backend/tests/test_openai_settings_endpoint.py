from fastapi.testclient import TestClient


def test_get_balance_defaults_to_zero(client: TestClient) -> None:
    response = client.get("/api/openai/balance")
    assert response.status_code == 200
    data = response.json()
    assert data["balance_usd"] == 0.0
    assert data["estimated_cost_per_generation_usd"] > 0


def test_put_balance_updates_and_persists(client: TestClient) -> None:
    response = client.put("/api/openai/balance", json={"balance_usd": 25.0})
    assert response.status_code == 200
    assert response.json()["balance_usd"] == 25.0

    response = client.get("/api/openai/balance")
    assert response.json()["balance_usd"] == 25.0


def test_put_balance_rejects_negative(client: TestClient) -> None:
    response = client.put("/api/openai/balance", json={"balance_usd": -1.0})
    assert response.status_code == 422
