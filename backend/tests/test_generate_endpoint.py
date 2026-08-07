from fastapi.testclient import TestClient


def test_generate_success(client: TestClient, mock_comfyui_success: None) -> None:
    response = client.post(
        "/api/generate",
        json={"script": "Anime, Guerrier, Forêt, Aube, Plan large", "style": "Anime", "seed": 42},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["image_base64"].startswith("data:image/png;base64,")
    assert data["prompt_id"] == "test-123"
    assert data["seed_used"] == 42
    assert data["preset_used"]["style"] == "Anime"


def test_generate_unreachable_returns_503(client: TestClient, mock_comfyui_unreachable: None) -> None:
    response = client.post(
        "/api/generate",
        json={"script": "un chat en armure", "style": None},
    )
    assert response.status_code == 503

    detail = response.json()["detail"]
    assert detail["error_type"] == "comfyui_unreachable"


def test_generate_unknown_style_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        json={"script": "un chat en armure", "style": "Style Qui N'existe Pas"},
    )
    assert response.status_code == 422


def test_comfyui_status_reachable(client: TestClient, mock_comfyui_success: None) -> None:
    response = client.get("/api/comfyui/status")
    assert response.status_code == 200
    assert response.json() == {"reachable": True}


def test_comfyui_status_unreachable(client: TestClient, mock_comfyui_unreachable: None) -> None:
    response = client.get("/api/comfyui/status")
    assert response.status_code == 200
    assert response.json() == {"reachable": False}
