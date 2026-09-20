from fastapi.testclient import TestClient


def test_generate_success_with_explicit_model_id(
    client: TestClient, mock_comfyui_success: None
) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "Anime, Guerrier, Forêt, Aube, Plan large",
            "style": "Anime",
            "model_id": "counterfeit_anime",
            "seed": 42,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["image_base64"].startswith("data:image/png;base64,")
    assert data["prompt_id"] == "test-123"
    assert data["seed_used"] == 42
    assert data["preset_used"]["style"] == "Anime"
    assert data["preset_used"]["model_id"] == "counterfeit_anime"


def test_generate_flux_is_always_offered_even_for_single_model_styles(
    client: TestClient, mock_comfyui_success: None
) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "Anime, Guerrier, Forêt, Aube, Plan large",
            "style": "Anime",
            "model_id": "flux_anime",
            "seed": 42,
        },
    )
    assert response.status_code == 200
    assert response.json()["preset_used"]["model_id"] == "flux_anime"


def test_generate_anime_without_model_id_rejected_now_that_flux_is_added(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/generate",
        json={"script": "Anime, Guerrier, Forêt, Aube, Plan large", "style": "Anime"},
    )
    assert response.status_code == 422


def test_generate_flux_model_success(client: TestClient, mock_comfyui_success: None) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "une aquarelle de montagnes",
            "style": "Aquarelle",
            "model_id": "flux_aquarelle",
            "seed": 7,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["seed_used"] == 7
    assert data["preset_used"]["model_id"] == "flux_aquarelle"
    assert data["preset_used"]["cfg"] == 1.0


def test_generate_flux_schnell_model_success(
    client: TestClient, mock_comfyui_success: None
) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "une photo réaliste sous la pluie la nuit",
            "style": "Photoréaliste",
            "model_id": "flux_schnell_photo",
            "seed": 11,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["seed_used"] == 11
    assert data["preset_used"]["model_id"] == "flux_schnell_photo"
    assert data["preset_used"]["steps"] == 4


def test_generate_anima_model_success(client: TestClient, mock_comfyui_success: None) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "un super-héros sur un toit",
            "style": "Bande dessinée",
            "model_id": "anima_bd",
            "seed": 3,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["seed_used"] == 3
    assert data["preset_used"]["model_id"] == "anima_bd"
    assert data["preset_used"]["steps"] == 30


def test_generate_multiple_models_without_model_id_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        json={"script": "une aquarelle de montagnes", "style": "Aquarelle"},
    )
    assert response.status_code == 422


def test_generate_unknown_model_id_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        json={"script": "une aquarelle de montagnes", "style": "Aquarelle", "model_id": "nope"},
    )
    assert response.status_code == 422


def test_generate_unreachable_returns_503(client: TestClient, mock_comfyui_unreachable: None) -> None:
    response = client.post(
        "/api/generate",
        json={"script": "un chat en armure", "style": None, "model_id": "sdxl_default"},
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
