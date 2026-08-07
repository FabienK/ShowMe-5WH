import base64

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import comfyui_client

# 1x1 transparent PNG, used as the fake ComfyUI output.
_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY"
    "42YAAAAASUVORK5CYII="
)


def _success_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/prompt" and request.method == "POST":
        return httpx.Response(200, json={"prompt_id": "test-123", "number": 1, "node_errors": {}})
    if request.url.path == "/history/test-123":
        return httpx.Response(
            200,
            json={
                "test-123": {
                    "outputs": {
                        "9": {"images": [{"filename": "test.png", "subfolder": "", "type": "output"}]}
                    }
                }
            },
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


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
