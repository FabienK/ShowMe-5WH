import base64

import httpx
import httpx2
import openai
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services import comfyui_client, openai_generator

# 1x1 transparent PNG, used as the fake ComfyUI output.
_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY"
    "42YAAAAASUVORK5CYII="
)


def _success_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/upload/image" and request.method == "POST":
        return httpx.Response(200, json={"name": "ref-uploaded.png", "subfolder": "", "type": "input"})
    if request.url.path == "/prompt" and request.method == "POST":
        return httpx.Response(200, json={"prompt_id": "test-123", "number": 1, "node_errors": {}})
    if request.url.path == "/history/test-123":
        image = {"images": [{"filename": "test.png", "subfolder": "", "type": "output"}]}
        return httpx.Response(
            200,
            # Le mock ne sait pas quel workflow a été soumis, donc on renvoie une
            # sortie sous les node id de SaveImage possibles (fast/anima : "9",
            # flux : "11", flux schnell : "3", flux kontext : "13").
            json={"test-123": {"outputs": {"9": image, "11": image, "3": image, "13": image}}},
        )
    if request.url.path == "/view":
        return httpx.Response(200, content=_TINY_PNG, headers={"content-type": "image/png"})
    if request.url.path == "/system_stats":
        return httpx.Response(200, json={})
    return httpx.Response(404, json={"error": "unexpected path"})


@pytest.fixture
def mock_comfyui_success(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = httpx.MockTransport(_success_handler)

    def _build_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url="http://comfyui.test", transport=transport)

    monkeypatch.setattr(comfyui_client, "_build_client", _build_client)


@pytest.fixture
def mock_comfyui_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(_raise)

    def _build_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url="http://comfyui.test", transport=transport)

    monkeypatch.setattr(comfyui_client, "_build_client", _build_client)


_OPENAI_USAGE = {
    "input_tokens": 20,
    "input_tokens_details": {"text_tokens": 20, "image_tokens": 0},
    "output_tokens": 1056,
    "total_tokens": 1076,
}


def _openai_success_handler(request: httpx2.Request) -> httpx2.Response:
    if request.url.path == "/v1/images/generations" and request.method == "POST":
        return httpx2.Response(
            200,
            json={
                "created": 1,
                "data": [{"b64_json": base64.b64encode(_TINY_PNG).decode()}],
                "usage": _OPENAI_USAGE,
            },
        )
    return httpx2.Response(404, json={"error": "unexpected path"})


@pytest.fixture
def mock_openai_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    transport = httpx2.MockTransport(_openai_success_handler)

    def _client() -> openai.AsyncOpenAI:
        return openai.AsyncOpenAI(
            api_key=settings.openai_api_key,
            http_client=httpx2.AsyncClient(transport=transport),
        )

    monkeypatch.setattr(openai_generator, "_client", _client)


@pytest.fixture
def mock_openai_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    def _error_handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            429,
            json={"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}},
        )

    transport = httpx2.MockTransport(_error_handler)

    def _client() -> openai.AsyncOpenAI:
        return openai.AsyncOpenAI(
            api_key=settings.openai_api_key,
            http_client=httpx2.AsyncClient(transport=transport),
        )

    monkeypatch.setattr(openai_generator, "_client", _client)


@pytest.fixture(autouse=True)
def _isolate_openai_state(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Empêche les tests d'écrire dans le vrai backend/state/openai_state.json."""
    monkeypatch.setattr(settings, "openai_state_path", tmp_path / "state" / "openai_state.json")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _isolate_batches_dir(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Empêche les tests d'écrire dans le vrai backend/generated_batches/."""
    monkeypatch.setattr(settings, "generated_batches_dir", tmp_path / "generated_batches")


@pytest.fixture(autouse=True)
def _isolate_generated_openai_dir(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Empêche les tests d'écrire dans le vrai backend/generated_openai/."""
    monkeypatch.setattr(settings, "generated_openai_dir", tmp_path / "generated_openai")
