import time

from fastapi.testclient import TestClient

from app.config import settings
from app.services import batch_store
from app.models.schemas import BatchDetailResponse, BatchItemResult


def _wait_until_completed(client: TestClient, batch_id: str, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/batches/{batch_id}")
        data = response.json()
        if data["status"] == "completed":
            return data
        time.sleep(0.05)
    raise AssertionError(f"Batch {batch_id} non terminé après {timeout}s : {data}")


def test_create_batch_returns_id_immediately(client: TestClient, mock_comfyui_success: None) -> None:
    response = client.post(
        "/api/batches",
        json={
            "items": [
                {"script": "a fox in a forest", "model_id": "sdxl_default"},
                {"script": "a watercolor mountain", "style": "Aquarelle", "model_id": "flux_aquarelle"},
            ]
        },
    )
    assert response.status_code == 202
    batch_id = response.json()["batch_id"]
    assert batch_id

    data = _wait_until_completed(client, batch_id)
    assert data["status"] == "completed"
    assert len(data["items"]) == 2
    assert all(item["status"] == "success" for item in data["items"])


def test_batch_continues_after_item_error(client: TestClient, mock_comfyui_success: None) -> None:
    response = client.post(
        "/api/batches",
        json={
            "items": [
                {"script": "a fox in a forest", "model_id": "sdxl_default"},
                {"script": "un prompt quelconque", "model_id": "nope_does_not_exist"},
                {"script": "a watercolor mountain", "style": "Aquarelle", "model_id": "flux_aquarelle"},
            ]
        },
    )
    batch_id = response.json()["batch_id"]

    data = _wait_until_completed(client, batch_id)
    assert data["status"] == "completed"
    assert data["items"][0]["status"] == "success"
    assert data["items"][1]["status"] == "error"
    assert data["items"][1]["error_type"] == "invalid_model_id"
    assert data["items"][2]["status"] == "success"


def test_batch_list_returns_summaries(client: TestClient, mock_comfyui_success: None) -> None:
    ids = []
    for _ in range(2):
        response = client.post(
            "/api/batches", json={"items": [{"script": "un chat", "model_id": "sdxl_default"}]}
        )
        ids.append(response.json()["batch_id"])
        _wait_until_completed(client, ids[-1])

    response = client.get("/api/batches")
    assert response.status_code == 200
    listed_ids = {summary["batch_id"] for summary in response.json()["batches"]}
    assert set(ids).issubset(listed_ids)
    for summary in response.json()["batches"]:
        if summary["batch_id"] in ids:
            assert summary["total_items"] == 1
            assert summary["completed_items"] == 1


def test_batch_detail_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get("/api/batches/does-not-exist")
    assert response.status_code == 404


def test_batch_images_written_to_disk(client: TestClient, mock_comfyui_success: None) -> None:
    from PIL import Image

    response = client.post(
        "/api/batches", json={"items": [{"script": "un chat", "model_id": "sdxl_default"}]}
    )
    batch_id = response.json()["batch_id"]
    data = _wait_until_completed(client, batch_id)

    image_file = settings.generated_batches_dir / batch_id / "0.png"
    assert image_file.exists()
    with Image.open(image_file) as img:
        img.verify()
    assert data["items"][0]["image_path"] == f"{batch_id}/0.png"


def test_batch_unreachable_comfyui_marks_all_items_error(
    client: TestClient, mock_comfyui_unreachable: None
) -> None:
    response = client.post(
        "/api/batches",
        json={
            "items": [
                {"script": "un chat", "model_id": "sdxl_default"},
                {"script": "un chien", "model_id": "sdxl_default"},
            ]
        },
    )
    batch_id = response.json()["batch_id"]
    data = _wait_until_completed(client, batch_id)

    assert data["status"] == "completed"
    assert all(item["status"] == "error" for item in data["items"])
    assert all(item["error_type"] == "comfyui_unreachable" for item in data["items"])


def test_startup_scan_marks_running_batch_as_interrupted() -> None:
    batch_id = batch_store.new_batch_id()
    detail = BatchDetailResponse(
        batch_id=batch_id,
        status="running",
        created_at="2026-01-01T00:00:00+00:00",
        items=[
            BatchItemResult(
                index=0,
                request={"script": "un chat", "model_id": "sdxl_default"},
                status="success",
            )
        ],
    )
    batch_store.write_manifest(batch_id, detail)

    batch_store.mark_interrupted_batches_on_startup()

    reloaded = batch_store.read_manifest(batch_id)
    assert reloaded.status == "interrupted"
    assert reloaded.items[0].status == "success"
