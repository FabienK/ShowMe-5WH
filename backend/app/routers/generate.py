import base64
import random

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ComfyUIStatusResponse,
    ErrorResponse,
    GenerateRequest,
    GenerateResponse,
    PresetUsed,
)
from app.services import comfyui_client
from app.services.presets import resolve_preset

router = APIRouter(tags=["generate"])

_SEED_MAX = 2**32 - 1


@router.get("/comfyui/status", response_model=ComfyUIStatusResponse)
async def get_comfyui_status() -> ComfyUIStatusResponse:
    reachable = await comfyui_client.is_reachable()
    return ComfyUIStatusResponse(reachable=reachable)


@router.post("/generate", response_model=GenerateResponse)
async def post_generate(request: GenerateRequest) -> GenerateResponse:
    preset = resolve_preset(request.style)
    seed = request.seed if request.seed is not None else random.randint(0, _SEED_MAX)

    try:
        result = await comfyui_client.generate_image(request.script, preset, seed)
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

    image_base64 = "data:image/png;base64," + base64.b64encode(result.image_bytes).decode()

    return GenerateResponse(
        image_base64=image_base64,
        prompt_id=result.prompt_id,
        seed_used=result.seed_used,
        preset_used=PresetUsed(
            style=request.style or "default",
            checkpoint=preset.checkpoint,
            lora=preset.lora,
            sampler=preset.sampler,
            scheduler=preset.scheduler,
            steps=preset.steps,
            cfg=preset.cfg,
            width=preset.width,
            height=preset.height,
        ),
    )
