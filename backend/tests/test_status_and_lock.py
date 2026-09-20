"""Verrou global de génération (services/activity.py) et GET /api/status."""

import asyncio
import threading
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import GenerateRequest
from app.services import activity, comfyui_client
from app.services.generation_dispatch import dispatch_generation
from app.services.presets import resolve_model
from tests.conftest import _success_handler


def _blocking_transport(release: threading.Event) -> httpx.MockTransport:
    """Mock ComfyUI dont /history ne répond qu'une fois `release` levé — la
    génération reste "en cours" tant que le test ne la libère pas, sans
    bloquer la boucle asyncio (handler async + sleep)."""

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/history/"):
            while not release.is_set():
                await asyncio.sleep(0.01)
        return _success_handler(request)

    return httpx.MockTransport(handler)


def _install(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    monkeypatch.setattr(
        comfyui_client,
        "_build_client",
        lambda: httpx.AsyncClient(base_url="http://comfyui.test", transport=transport),
    )


def _wait_status(client: TestClient, predicate, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        data = client.get("/api/status").json()
        if predicate(data):
            return data
        time.sleep(0.02)
    raise AssertionError(f"/api/status n'a pas atteint l'état attendu : {data}")


def test_status_idle(client: TestClient, mock_comfyui_success: None) -> None:
    data = client.get("/api/status").json()
    assert data == {
        "busy": False,
        "current": None,
        "waiting": 0,
        "running_batches": [],
        "comfyui_reachable": True,
    }


def test_health_identifies_the_app(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok", "app": "ShowMe-5WH"}


def test_status_busy_during_generate(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    release = threading.Event()
    _install(monkeypatch, _blocking_transport(release))
    results: list[httpx.Response] = []

    def _generate() -> None:
        results.append(
            client.post(
                "/api/generate",
                json={"script": "a fox", "model_id": "sdxl_default", "seed": 1},
            )
        )

    thread = threading.Thread(target=_generate)
    thread.start()
    try:
        busy = _wait_status(client, lambda d: d["busy"])
        assert busy["current"]["model_id"] == "sdxl_default"
        assert busy["current"]["source"] == "generate"
        assert busy["current"]["batch_id"] is None
        assert busy["waiting"] == 0
    finally:
        release.set()
        thread.join(timeout=5)

    assert results and results[0].status_code == 200
    assert _wait_status(client, lambda d: not d["busy"])["current"] is None


def test_status_reports_running_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    release = threading.Event()
    _install(monkeypatch, _blocking_transport(release))

    # `with` : une seule boucle asyncio pour toute la durée du test, sinon la
    # tâche de fond du batch meurt avec la boucle de la requête POST.
    with TestClient(app) as client:
        batch_id = client.post(
            "/api/batches", json={"items": [{"script": "a fox", "model_id": "sdxl_default"}]}
        ).json()["batch_id"]
        try:
            busy = _wait_status(client, lambda d: d["busy"])
            assert busy["current"]["source"] == "batch"
            assert busy["current"]["batch_id"] == batch_id
            assert busy["running_batches"] == [batch_id]
        finally:
            release.set()

        _wait_status(client, lambda d: not d["busy"] and d["running_batches"] == [])


@pytest.mark.asyncio
async def test_concurrent_generations_are_serialized(monkeypatch: pytest.MonkeyPatch) -> None:
    active = 0
    max_active = 0
    waiting_seen: list[int] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active, max_active
        if request.url.path == "/prompt":
            active += 1
            max_active = max(max_active, active)
            waiting_seen.append(activity.waiting_count())
            await asyncio.sleep(0.05)
            active -= 1
        return _success_handler(request)

    _install(monkeypatch, httpx.MockTransport(handler))
    model = resolve_model(None, "sdxl_default")
    request = GenerateRequest(script="a fox", model_id="sdxl_default")

    results = await asyncio.gather(
        dispatch_generation(request, model, 1, None),
        dispatch_generation(request, model, 2, None),
        dispatch_generation(request, model, 3, None),
    )

    assert [r.seed_used for r in results] == [1, 2, 3]
    assert max_active == 1, "deux générations ont tourné en même temps"
    # Le 1er appel prend le verrou avant même que les autres n'aient démarré
    # (gather les lance dans l'ordre) ; ensuite la file se vide : 1 puis 0.
    assert waiting_seen[1:] == [1, 0]
    assert not activity.is_busy()
    assert activity.waiting_count() == 0
