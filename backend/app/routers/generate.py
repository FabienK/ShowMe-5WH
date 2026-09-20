import base64
import random

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.schemas import (
    ComfyUIStatusResponse,
    CurrentJobInfo,
    ErrorResponse,
    GenerateRequest,
    GenerateResponse,
    ModelOption,
    PresetUsed,
    StatusResponse,
)
from app.services import activity, batch_store, comfyui_client
from app.services.generation_dispatch import dispatch_generation, validate_engine_constraints
from app.services.image_validation import InvalidReferenceImageError, decode_and_validate_reference_image
from app.services.openai_generator import OpenAIGenerationError, OpenAIMissingApiKeyError, save_image
from app.services.presets import resolve_model

router = APIRouter(tags=["generate"])

_SEED_MAX = 2**32 - 1


@router.get("/comfyui/status", response_model=ComfyUIStatusResponse)
async def get_comfyui_status() -> ComfyUIStatusResponse:
    reachable = await comfyui_client.is_reachable()
    return ComfyUIStatusResponse(reachable=reachable)


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    current = activity.current_job()
    return StatusResponse(
        busy=activity.is_busy(),
        current=CurrentJobInfo(**current.model_dump()) if current else None,
        waiting=activity.waiting_count(),
        running_batches=[
            summary.batch_id
            for summary in batch_store.list_batches()
            if summary.status == "running"
        ],
        comfyui_reachable=await comfyui_client.is_reachable(),
    )


def preset_used(
    style: str | None, model: ModelOption, denoise_strength: float | None = None
) -> PresetUsed:
    if model.engine_type == "flux":
        checkpoint, sampler, scheduler = settings.flux_unet_name, "euler", "simple"
        steps, cfg = settings.flux_steps, 1.0
        width, height = settings.flux_width, settings.flux_height
    elif model.engine_type == "anima":
        checkpoint, sampler, scheduler = settings.anima_unet_name, "euler", "simple"
        steps, cfg = settings.anima_steps, settings.anima_cfg
        width, height = settings.anima_width, settings.anima_height
    elif model.engine_type == "flux_schnell":
        checkpoint, sampler, scheduler = settings.flux_schnell_model_version, "-", "-"
        steps, cfg = settings.flux_schnell_steps, settings.flux_schnell_guidance
        width, height = settings.flux_schnell_width, settings.flux_schnell_height
    elif model.engine_type == "flux_kontext":
        checkpoint, sampler, scheduler = settings.flux_kontext_unet_name, "euler", "simple"
        steps, cfg = settings.flux_kontext_steps, 1.0
        width, height = settings.flux_kontext_width, settings.flux_kontext_height
    elif model.engine_type == "openai":
        checkpoint, sampler, scheduler = "gpt-image-2", "-", "-"
        steps, cfg = 0, 0.0
        width, height = model.width, model.height
    else:
        assert model.checkpoint is not None
        checkpoint, sampler, scheduler = model.checkpoint, model.sampler, model.scheduler
        steps, cfg = model.steps, model.cfg
        width, height = model.width, model.height

    return PresetUsed(
        style=style or "default",
        model_id=model.id,
        model_label=model.label,
        model_version=model.version,
        estimated_time=model.estimated_time,
        checkpoint=checkpoint,
        lora=model.lora,
        sampler=sampler,
        scheduler=scheduler,
        steps=steps,
        cfg=cfg,
        width=width,
        height=height,
        denoise_strength=denoise_strength,
    )


@router.post("/generate", response_model=GenerateResponse)
async def post_generate(request: GenerateRequest) -> GenerateResponse:
    seed = request.seed if request.seed is not None else random.randint(0, _SEED_MAX)

    try:
        model = resolve_model(request.style, request.model_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(error_type="invalid_model_id", detail=str(exc)).model_dump(),
        ) from exc

    try:
        validate_engine_constraints(request, model)
    except ValueError as exc:
        error_type = (
            "img2img_not_supported_for_model"
            if model.engine_type in ("flux_schnell", "openai")
            else "reference_image_required_for_model"
        )
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(error_type=error_type, detail=str(exc)).model_dump(),
        ) from exc

    reference_image_bytes = None
    if request.reference_image is not None:
        try:
            reference_image_bytes = decode_and_validate_reference_image(request.reference_image)
        except InvalidReferenceImageError as exc:
            raise HTTPException(
                status_code=422,
                detail=ErrorResponse(
                    error_type="invalid_reference_image", detail=str(exc)
                ).model_dump(),
            ) from exc

    try:
        result = await dispatch_generation(request, model, seed, reference_image_bytes)
    except comfyui_client.ComfyUIUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(error_type="comfyui_unreachable", detail=str(exc)).model_dump(),
        ) from exc
    except comfyui_client.ComfyUITimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=ErrorResponse(error_type="comfyui_timeout", detail=str(exc)).model_dump(),
        ) from exc
    except comfyui_client.ComfyUIGenerationError as exc:
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(error_type="comfyui_generation_failed", detail=str(exc)).model_dump(),
        ) from exc
    except OpenAIMissingApiKeyError as exc:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(error_type="openai_api_key_missing", detail=str(exc)).model_dump(),
        ) from exc
    except OpenAIGenerationError as exc:
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(error_type="openai_generation_failed", detail=str(exc)).model_dump(),
        ) from exc

    if model.engine_type == "openai":
        save_image(result.image_bytes)

    image_base64 = "data:image/png;base64," + base64.b64encode(result.image_bytes).decode()

    return GenerateResponse(
        image_base64=image_base64,
        prompt_id=result.prompt_id,
        seed_used=result.seed_used,
        preset_used=preset_used(
            request.style,
            model,
            request.denoise_strength
            if request.reference_image is not None and model.engine_type != "flux_kontext"
            else None,
        ),
    )
