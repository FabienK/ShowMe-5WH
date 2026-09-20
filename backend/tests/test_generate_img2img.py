import base64

from fastapi.testclient import TestClient

# 1x1 opaque PNG, valide pour Pillow.
_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY"
    "42YAAAAASUVORK5CYII="
)
_TINY_PNG_DATA_URL = f"data:image/png;base64,{_TINY_PNG_B64}"


def test_img2img_success_sd_checkpoint(client: TestClient, mock_comfyui_success: None) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "Anime, Guerrier, Forêt, Aube, Plan large",
            "style": "Anime",
            "model_id": "counterfeit_anime",
            "seed": 42,
            "reference_image": _TINY_PNG_DATA_URL,
            "denoise_strength": 0.4,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["preset_used"]["denoise_strength"] == 0.4


def test_img2img_success_flux(client: TestClient, mock_comfyui_success: None) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "une aquarelle de montagnes",
            "style": "Aquarelle",
            "model_id": "flux_aquarelle",
            "seed": 7,
            "reference_image": _TINY_PNG_DATA_URL,
            "denoise_strength": 0.5,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["preset_used"]["denoise_strength"] == 0.5


def test_img2img_success_anima(client: TestClient, mock_comfyui_success: None) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "un super-héros sur un toit",
            "style": "Bande dessinée",
            "model_id": "anima_bd",
            "seed": 3,
            "reference_image": _TINY_PNG_DATA_URL,
            "denoise_strength": 0.7,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["preset_used"]["denoise_strength"] == 0.7


def test_img2img_rejected_for_flux_schnell(client: TestClient, mock_comfyui_success: None) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "une photo réaliste sous la pluie la nuit",
            "style": "Photoréaliste",
            "model_id": "flux_schnell_photo",
            "seed": 11,
            "reference_image": _TINY_PNG_DATA_URL,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error_type"] == "img2img_not_supported_for_model"


def test_flux_kontext_success_with_reference_image(
    client: TestClient, mock_comfyui_success: None
) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "change the background to a beach, keep the person in the same pose",
            "style": "Photoréaliste",
            "model_id": "flux_kontext_photorealiste",
            "seed": 5,
            "reference_image": _TINY_PNG_DATA_URL,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["preset_used"]["model_id"] == "flux_kontext_photorealiste"
    assert data["preset_used"]["denoise_strength"] is None


def test_flux_kontext_rejected_without_reference_image(
    client: TestClient, mock_comfyui_success: None
) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "change the background to a beach",
            "style": "Photoréaliste",
            "model_id": "flux_kontext_photorealiste",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error_type"] == "reference_image_required_for_model"


def test_img2img_rejects_malformed_data_url(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "un chat en armure",
            "style": None,
            "model_id": "sdxl_default",
            "reference_image": "not-a-data-url",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error_type"] == "invalid_reference_image"


def test_img2img_rejects_non_image_payload(client: TestClient) -> None:
    fake_bytes = base64.b64encode(b"not an image").decode()
    response = client.post(
        "/api/generate",
        json={
            "script": "un chat en armure",
            "style": None,
            "model_id": "sdxl_default",
            "reference_image": f"data:image/png;base64,{fake_bytes}",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error_type"] == "invalid_reference_image"


def test_generate_requires_script_or_reference_image(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        json={"script": "", "style": None, "model_id": "sdxl_default"},
    )
    assert response.status_code == 422


def test_denoise_strength_out_of_range_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "un chat en armure",
            "style": None,
            "model_id": "sdxl_default",
            "reference_image": _TINY_PNG_DATA_URL,
            "denoise_strength": 1.5,
        },
    )
    assert response.status_code == 422
