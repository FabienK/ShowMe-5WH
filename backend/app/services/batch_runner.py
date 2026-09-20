"""Exécution d'un batch en tâche de fond, in-process (asyncio.create_task,
voir routers/batches.py) — pas de scheduler/queue externe : ComfyUI ne
traite qu'un job à la fois (VRAM 24 Go unifiée, voir comfyui_client.py et le
commentaire sur flux_kontext_timeout_seconds dans config.py), donc le runner
exécute les items strictement en séquence, jamais en parallèle.

Point central : une erreur sur un item est consignée (status="error",
error_type/error_detail) et n'interrompt PAS le batch, contrairement à la
boucle actuelle côté frontend (useGenerationFlow.ts::generateForModels, qui
s'arrête à la première erreur) — c'est précisément ce qui rend un batch
utilisable sans surveillance, la nuit."""

import logging
import random
from datetime import datetime, timezone

from app.models.schemas import BatchDetailResponse, BatchItemResult, GenerateRequest
from app.routers.generate import preset_used
from app.services import batch_store, comfyui_client
from app.services.generation_dispatch import dispatch_generation, validate_engine_constraints
from app.services.image_validation import InvalidReferenceImageError, decode_and_validate_reference_image
from app.services.presets import resolve_model

logger = logging.getLogger(__name__)

_SEED_MAX = 2**32 - 1


class _EngineConstraintError(ValueError):
    """Lève avec le même error_type que /api/generate pour cette contrainte —
    distingue une contrainte image/moteur (validate_engine_constraints) d'un
    model_id simplement inconnu (resolve_model), qui lèvent toutes deux
    ValueError sinon indistinguables pour le manifest."""

    def __init__(self, error_type: str, message: str) -> None:
        super().__init__(message)
        self.error_type = error_type


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _classify_error(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, _EngineConstraintError):
        return exc.error_type, str(exc)
    if isinstance(exc, InvalidReferenceImageError):
        return "invalid_reference_image", str(exc)
    if isinstance(exc, ValueError):
        return "invalid_model_id", str(exc)
    if isinstance(exc, comfyui_client.ComfyUIUnavailableError):
        return "comfyui_unreachable", str(exc)
    if isinstance(exc, comfyui_client.ComfyUITimeoutError):
        return "comfyui_timeout", str(exc)
    if isinstance(exc, comfyui_client.ComfyUIGenerationError):
        return "comfyui_generation_failed", str(exc)
    return "unexpected_error", str(exc)


async def _run_one_item(batch_id: str, item: BatchItemResult) -> None:
    request = item.request
    seed = request.seed if request.seed is not None else random.randint(0, _SEED_MAX)

    model = resolve_model(request.style, request.model_id)
    try:
        validate_engine_constraints(request, model)
    except ValueError as exc:
        error_type = (
            "img2img_not_supported_for_model"
            if model.engine_type == "flux_schnell"
            else "reference_image_required_for_model"
        )
        raise _EngineConstraintError(error_type, str(exc)) from exc

    reference_image_bytes = None
    if request.reference_image is not None:
        reference_image_bytes = decode_and_validate_reference_image(request.reference_image)

    result = await dispatch_generation(request, model, seed, reference_image_bytes)

    image_file = batch_store.image_path(batch_id, item.index)
    image_file.write_bytes(result.image_bytes)

    item.image_path = f"{batch_id}/{item.index}.png"
    item.prompt_id = result.prompt_id
    item.seed_used = result.seed_used
    item.preset_used = preset_used(
        request.style,
        model,
        request.denoise_strength
        if request.reference_image is not None and model.engine_type != "flux_kontext"
        else None,
    )


async def run_batch(batch_id: str, items: list[GenerateRequest]) -> None:
    detail = BatchDetailResponse(
        batch_id=batch_id,
        status="running",
        created_at=_now(),
        items=[BatchItemResult(index=i, request=req) for i, req in enumerate(items)],
    )
    batch_store.write_manifest(batch_id, detail)

    for item in detail.items:
        item.status = "running"
        item.started_at = _now()
        batch_store.write_manifest(batch_id, detail)

        try:
            await _run_one_item(batch_id, item)
            item.status = "success"
        except Exception as exc:  # un item raté ne doit jamais arrêter le batch
            item.status = "error"
            item.error_type, item.error_detail = _classify_error(exc)
            logger.warning("Batch %s item %d échoué : %s", batch_id, item.index, exc)
        finally:
            item.finished_at = _now()
            batch_store.write_manifest(batch_id, detail)

    detail.status = "completed"
    batch_store.write_manifest(batch_id, detail)
