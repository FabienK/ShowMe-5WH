"""Validation des contraintes par moteur et dispatch vers ComfyUI — logique
partagée entre /api/generate (routers/generate.py) et le runner de batch
(services/batch_runner.py), pour ne pas dupliquer le branchement 5 voies sur
model.engine_type."""

from app.config import settings
from app.models.schemas import GenerateRequest, ModelOption, PresetConfig
from app.services import activity, comfyui_client, openai_generator, openai_state_store
from app.services.comfyui_client import GenerationResult
from app.services.negative_prompt import strip_negative_conflicts


def validate_engine_constraints(request: GenerateRequest, model: ModelOption) -> None:
    """Lève ValueError si l'image de référence est incompatible avec le
    moteur choisi (non supportée par flux_schnell/openai, requise par
    flux_kontext)."""
    if request.reference_image is not None and model.engine_type in (
        "flux_schnell",
        "openai",
    ):
        raise ValueError(
            "L'image de référence n'est pas prise en charge pour ce modèle."
        )
    if request.reference_image is None and model.engine_type == "flux_kontext":
        raise ValueError(
            "Une image de référence est requise pour ce modèle (Flux Kontext)."
        )


async def dispatch_generation(
    request: GenerateRequest,
    model: ModelOption,
    seed: int,
    reference_image_bytes: bytes | None,
    *,
    source: activity.JobSource = "generate",
    batch_id: str | None = None,
) -> GenerationResult:
    """Suppose que model a déjà été résolu (resolve_model), que
    validate_engine_constraints() est passée, et que l'image de référence a
    déjà été décodée par l'appelant.

    Une seule génération à la fois, tous appelants confondus (voir
    services/activity.py) : les appels concurrents attendent leur tour ici,
    avant que le timeout ComfyUI ne commence à courir."""
    async with activity.generation_slot(model.id, source, batch_id):
        return await _dispatch_unlocked(request, model, seed, reference_image_bytes)


async def _dispatch_unlocked(
    request: GenerateRequest,
    model: ModelOption,
    seed: int,
    reference_image_bytes: bytes | None,
) -> GenerationResult:
    if model.engine_type == "flux":
        return await comfyui_client.generate_image_flux(
            request.script, seed, reference_image_bytes, request.denoise_strength
        )
    if model.engine_type == "anima":
        negative_prompt = strip_negative_conflicts(request.script, settings.anima_negative_prompt)
        return await comfyui_client.generate_image_anima(
            request.script, negative_prompt, seed, reference_image_bytes, request.denoise_strength
        )
    if model.engine_type == "flux_schnell":
        return await comfyui_client.generate_image_flux_schnell(request.script, seed)
    if model.engine_type == "flux_kontext":
        assert reference_image_bytes is not None
        return await comfyui_client.generate_image_flux_kontext(
            request.script, seed, reference_image_bytes
        )
    if model.engine_type == "openai":
        # Le solde local n'est qu'une estimation (voir
        # openai_state_store.py) : on ne bloque pas ici sur un solde
        # insuffisant, seule la vraie réponse de l'API fait foi. Le
        # décrément n'a lieu qu'après un retour réussi de
        # generate_via_openai — jamais dans un except/finally.
        result, cost_usd = await openai_generator.generate_via_openai(
            request.script, model.width, model.height, seed
        )
        openai_state_store.decrement_balance(cost_usd)
        return result
    assert model.checkpoint is not None
    negative_prompt = strip_negative_conflicts(request.script, model.negative_prompt)
    preset = PresetConfig(
        checkpoint=model.checkpoint,
        lora=model.lora,
        lora_strength=model.lora_strength,
        sampler=model.sampler,
        scheduler=model.scheduler,
        steps=model.steps,
        cfg=model.cfg,
        width=model.width,
        height=model.height,
        negative_prompt=negative_prompt,
    )
    return await comfyui_client.generate_image(
        request.script, preset, seed, reference_image_bytes, request.denoise_strength
    )
