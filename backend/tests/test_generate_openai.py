import base64

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.services import openai_state_store

_TINY_PNG_DATA_URL = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_generate_openai_success_decrements_balance(
    client: TestClient, mock_openai_success: None
) -> None:
    openai_state_store.set_balance(1.00)

    response = client.post(
        "/api/generate",
        json={
            "script": "a lone warrior, medieval village, dusk, wide shot",
            "model_id": "openai_default",
            "seed": 42,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["image_base64"].startswith("data:image/png;base64,")
    assert data["seed_used"] == 42
    assert data["preset_used"]["model_id"] == "openai_default"
    assert data["preset_used"]["checkpoint"] == "gpt-image-2"

    # Coût réel = 20 text tokens * 5$/1M + 1056 output tokens * 30$/1M (voir
    # _OPENAI_USAGE dans conftest.py) = 0.0001 + 0.03168 = 0.03178.
    expected_cost = (
        20 * settings.openai_price_per_text_input_token_usd
        + 1056 * settings.openai_price_per_output_token_usd
    )
    assert openai_state_store.read_balance() == pytest.approx(1.00 - expected_cost)


def test_generate_openai_success_saves_image_to_disk(
    client: TestClient, mock_openai_success: None
) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "a lone warrior, medieval village, dusk, wide shot",
            "model_id": "openai_default",
            "seed": 1,
        },
    )
    assert response.status_code == 200
    expected_bytes = base64.b64decode(response.json()["image_base64"].split(",", 1)[1])

    saved_files = list(settings.generated_openai_dir.glob("*.png"))
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == expected_bytes


def test_generate_openai_missing_api_key_returns_explicit_error(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "a lone warrior, medieval village, dusk, wide shot",
            "model_id": "openai_default",
            "seed": 1,
        },
    )
    assert response.status_code == 503
    assert response.json()["detail"]["error_type"] == "openai_api_key_missing"


def test_generate_openai_api_failure_does_not_decrement_balance(
    client: TestClient, mock_openai_rate_limited: None
) -> None:
    openai_state_store.set_balance(1.00)

    response = client.post(
        "/api/generate",
        json={
            "script": "a lone warrior, medieval village, dusk, wide shot",
            "model_id": "openai_default",
            "seed": 1,
        },
    )
    assert response.status_code == 502
    assert response.json()["detail"]["error_type"] == "openai_generation_failed"
    assert openai_state_store.read_balance() == 1.00


def test_generate_openai_rejects_reference_image(
    client: TestClient, mock_openai_success: None
) -> None:
    response = client.post(
        "/api/generate",
        json={
            "script": "a lone warrior, medieval village, dusk, wide shot",
            "model_id": "openai_default",
            "seed": 1,
            "reference_image": _TINY_PNG_DATA_URL,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error_type"] == "img2img_not_supported_for_model"
