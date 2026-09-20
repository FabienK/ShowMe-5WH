import asyncio

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    BatchCreateRequest,
    BatchCreateResponse,
    BatchDetailResponse,
    BatchListResponse,
)
from app.services import batch_runner, batch_store

router = APIRouter(prefix="/batches", tags=["batches"])

# Python ne garde qu'une weak-ref sur une asyncio.Task — sans les conserver
# ici, le garbage collector peut tuer une tâche de batch en plein milieu.
_RUNNING_TASKS: set[asyncio.Task] = set()


@router.post("", response_model=BatchCreateResponse, status_code=202)
async def post_batch(request: BatchCreateRequest) -> BatchCreateResponse:
    batch_id = batch_store.new_batch_id()
    task = asyncio.create_task(batch_runner.run_batch(batch_id, request.items))
    _RUNNING_TASKS.add(task)
    task.add_done_callback(_RUNNING_TASKS.discard)
    return BatchCreateResponse(batch_id=batch_id)


@router.get("", response_model=BatchListResponse)
def get_batches() -> BatchListResponse:
    return BatchListResponse(batches=batch_store.list_batches())


@router.get("/{batch_id}", response_model=BatchDetailResponse)
def get_batch(batch_id: str) -> BatchDetailResponse:
    try:
        return batch_store.read_manifest(batch_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Batch introuvable : {batch_id}") from exc
