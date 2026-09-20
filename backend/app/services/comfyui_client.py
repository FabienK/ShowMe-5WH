"""Client HTTP contre l'API réelle de ComfyUI (POST /prompt, GET /history, GET /view).

Contrat implémenté (par défaut sur http://127.0.0.1:8188) :
  1. POST /prompt      -> soumet le graphe, renvoie {"prompt_id", "node_errors"}
  2. GET  /history/{id} -> poll jusqu'à ce que "outputs" soit renseigné
  3. GET  /view         -> récupère les octets de l'image générée

Le flux WebSocket (/ws) documenté par ComfyUI pour la progression live n'est
pas utilisé en V1 (polling HTTP suffisant pour une app mono-utilisateur) —
volontairement laissé pour une évolution V2.
"""

import asyncio
import copy
import json
import logging
import time
import uuid
from dataclasses import dataclass

import httpx

from app.config import settings
from app.models.schemas import PresetConfig

logger = logging.getLogger(__name__)

CHECKPOINT_NODE_ID = "4"
POSITIVE_PROMPT_NODE_ID = "6"
NEGATIVE_PROMPT_NODE_ID = "7"
SAMPLER_NODE_ID = "3"
LATENT_IMAGE_NODE_ID = "5"
SAVE_IMAGE_NODE_ID = "9"
LORA_NODE_ID = "10"

# Nœuds img2img injectés conditionnellement (LoadImage -> VAEEncode, en
# remplacement de la source de latent vide) — mêmes ID réutilisés dans les 3
# graphes standards (base/flux/anima), chacun opère sur son propre dict copié.
IMG2IMG_LOAD_IMAGE_NODE_ID = "20"
IMG2IMG_VAE_ENCODE_NODE_ID = "21"
IMG2IMG_SCALE_NODE_ID = "22"

# Nœuds du workflow Flux (backend/app/workflows/flux_workflow.json) — architecture
# différente d'un checkpoint classique : UNet/CLIP/VAE sont chargés séparément et
# il n'y a pas de vrai negative prompt (guidance distillée, cfg=1 sur le KSampler).
FLUX_UNET_NODE_ID = "1"
FLUX_CLIP_NODE_ID = "2"
FLUX_VAE_NODE_ID = "3"
FLUX_PROMPT_NODE_ID = "4"
FLUX_SAMPLING_NODE_ID = "7"
FLUX_LATENT_NODE_ID = "8"
FLUX_SAMPLER_NODE_ID = "9"
FLUX_SAVE_IMAGE_NODE_ID = "11"

# Nœuds du workflow Anima (backend/app/workflows/anima_workflow.json) — UNet +
# CLIP (encodeur Qwen3) + VAE chargés séparément, comme Flux, mais avec un vrai
# negative prompt (pas de guidance distillée) et une architecture différente.
ANIMA_UNET_NODE_ID = "1"
ANIMA_CLIP_NODE_ID = "2"
ANIMA_VAE_NODE_ID = "3"
ANIMA_POSITIVE_PROMPT_NODE_ID = "4"
ANIMA_NEGATIVE_PROMPT_NODE_ID = "5"
ANIMA_LATENT_NODE_ID = "6"
ANIMA_SAMPLER_NODE_ID = "7"
ANIMA_SAVE_IMAGE_NODE_ID = "9"

# Nœuds du workflow Flux schnell (backend/app/workflows/flux_schnell_workflow.json) —
# backend MLX natif (custom node Mflux-ComfyUI) au lieu de GGUF/MPS : le modèle
# quantifié 4-bit est téléchargé/mis en cache par MfluxModelsDownloader puis
# généré en 4 steps par QuickMfluxNode. Pas de negative prompt (comme Flux dev).
FLUX_SCHNELL_DOWNLOADER_NODE_ID = "1"
FLUX_SCHNELL_GENERATE_NODE_ID = "2"
FLUX_SCHNELL_SAVE_IMAGE_NODE_ID = "3"

# Nœuds du workflow Flux Kontext (backend/app/workflows/flux_kontext_workflow.json) —
# modèle d'édition d'image par instruction : contrairement à flux/anima/sd_checkpoint,
# l'image de référence n'est PAS injectée via un denoise partiel (_inject_img2img_nodes)
# mais via ReferenceLatent, qui conditionne la génération sur le latent de l'image
# tout en gardant denoise=1 (débruitage complet). Image de référence obligatoire —
# ce graphe n'a pas de mode txt2img.
FLUX_KONTEXT_UNET_NODE_ID = "1"
FLUX_KONTEXT_CLIP_NODE_ID = "2"
FLUX_KONTEXT_VAE_NODE_ID = "3"
FLUX_KONTEXT_PROMPT_NODE_ID = "4"
FLUX_KONTEXT_LOAD_IMAGE_NODE_ID = "6"
FLUX_KONTEXT_GUIDANCE_NODE_ID = "10"
FLUX_KONTEXT_SAMPLER_NODE_ID = "11"
FLUX_KONTEXT_SAVE_IMAGE_NODE_ID = "13"

_CLIENT_ID = str(uuid.uuid4())


class ComfyUIUnavailableError(Exception):
    """ComfyUI n'est pas joignable (connexion refusée / hôte injoignable)."""


class ComfyUIGenerationError(Exception):
    """ComfyUI a rejeté ou échoué la génération (node_errors, sortie absente)."""


class ComfyUITimeoutError(Exception):
    """La génération n'a pas abouti dans le délai imparti."""


@dataclass
class GenerationResult:
    image_bytes: bytes
    prompt_id: str
    seed_used: int


def _build_client() -> httpx.AsyncClient:
    """Point d'extension unique pour les tests : monkeypatcher cette fonction
    pour injecter un client lié à un httpx.MockTransport."""
    return httpx.AsyncClient(
        base_url=settings.comfyui_base_url, timeout=settings.comfyui_timeout_seconds
    )


def _load_workflow_template() -> dict:
    return json.loads(settings.workflow_template_path.read_text(encoding="utf-8"))


def _load_flux_workflow_template() -> dict:
    return json.loads(settings.flux_workflow_template_path.read_text(encoding="utf-8"))


def _load_anima_workflow_template() -> dict:
    return json.loads(settings.anima_workflow_template_path.read_text(encoding="utf-8"))


def _inject_img2img_nodes(
    graph: dict,
    load_image_node_id: str,
    vae_encode_node_id: str,
    scale_node_id: str,
    sampler_node_id: str,
    vae_source: list,
    reference_image_name: str,
    denoise: float,
    width: int,
    height: int,
) -> None:
    """Remplace la source de latent vide du graphe par LoadImage -> ImageScale
    -> VAEEncode, et fixe le denoise du sampler en conséquence. Le nœud
    ImageScale est indispensable : une photo de référence en pleine résolution
    (ex. 4000x3000 depuis un téléphone) fait exploser le buffer d'attention du
    VAE au moment de l'encodage (RuntimeError "Invalid buffer size: X GiB" sur
    MPS/CUDA) — on la ramène donc à la résolution cible du preset avant
    VAEEncode, comme le fait déjà EmptyLatentImage pour le txt2img. Le nœud
    EmptyLatentImage / EmptySD3LatentImage d'origine reste présent mais
    orphelin dans le dict : ComfyUI n'exécute que le sous-graphe atteignable
    depuis SaveImage."""
    graph[load_image_node_id] = {
        "class_type": "LoadImage",
        "inputs": {"image": reference_image_name},
    }
    graph[scale_node_id] = {
        "class_type": "ImageScale",
        "inputs": {
            "image": [load_image_node_id, 0],
            "upscale_method": "lanczos",
            "width": width,
            "height": height,
            "crop": "disabled",
        },
    }
    graph[vae_encode_node_id] = {
        "class_type": "VAEEncode",
        "inputs": {"pixels": [scale_node_id, 0], "vae": vae_source},
    }
    graph[sampler_node_id]["inputs"]["latent_image"] = [vae_encode_node_id, 0]
    graph[sampler_node_id]["inputs"]["denoise"] = denoise


def _build_graph(
    positive_prompt: str,
    preset: PresetConfig,
    seed: int,
    reference_image_name: str | None = None,
    denoise: float = 1.0,
) -> dict:
    graph = copy.deepcopy(_load_workflow_template())

    graph[CHECKPOINT_NODE_ID]["inputs"]["ckpt_name"] = preset.checkpoint
    graph[POSITIVE_PROMPT_NODE_ID]["inputs"]["text"] = positive_prompt
    graph[NEGATIVE_PROMPT_NODE_ID]["inputs"]["text"] = preset.negative_prompt
    graph[SAMPLER_NODE_ID]["inputs"].update(
        {
            "seed": seed,
            "steps": preset.steps,
            "cfg": preset.cfg,
            "sampler_name": preset.sampler,
            "scheduler": preset.scheduler,
        }
    )
    graph[LATENT_IMAGE_NODE_ID]["inputs"].update({"width": preset.width, "height": preset.height})

    if preset.lora:
        graph[LORA_NODE_ID] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": preset.lora,
                "strength_model": preset.lora_strength,
                "strength_clip": preset.lora_strength,
                "model": [CHECKPOINT_NODE_ID, 0],
                "clip": [CHECKPOINT_NODE_ID, 1],
            },
        }
        graph[SAMPLER_NODE_ID]["inputs"]["model"] = [LORA_NODE_ID, 0]
        graph[POSITIVE_PROMPT_NODE_ID]["inputs"]["clip"] = [LORA_NODE_ID, 1]
        graph[NEGATIVE_PROMPT_NODE_ID]["inputs"]["clip"] = [LORA_NODE_ID, 1]

    if reference_image_name:
        _inject_img2img_nodes(
            graph,
            IMG2IMG_LOAD_IMAGE_NODE_ID,
            IMG2IMG_VAE_ENCODE_NODE_ID,
            IMG2IMG_SCALE_NODE_ID,
            SAMPLER_NODE_ID,
            [CHECKPOINT_NODE_ID, 2],
            reference_image_name,
            denoise,
            preset.width,
            preset.height,
        )

    return graph


def _build_flux_graph(
    positive_prompt: str,
    seed: int,
    reference_image_name: str | None = None,
    denoise: float = 1.0,
) -> dict:
    graph = copy.deepcopy(_load_flux_workflow_template())

    graph[FLUX_UNET_NODE_ID]["inputs"]["unet_name"] = settings.flux_unet_name
    graph[FLUX_CLIP_NODE_ID]["inputs"]["clip_name1"] = settings.flux_clip_name1
    graph[FLUX_CLIP_NODE_ID]["inputs"]["clip_name2"] = settings.flux_clip_name2
    graph[FLUX_VAE_NODE_ID]["inputs"]["vae_name"] = settings.flux_vae_name
    graph[FLUX_PROMPT_NODE_ID]["inputs"]["text"] = positive_prompt
    graph[FLUX_SAMPLING_NODE_ID]["inputs"].update(
        {"width": settings.flux_width, "height": settings.flux_height}
    )
    graph[FLUX_LATENT_NODE_ID]["inputs"].update(
        {"width": settings.flux_width, "height": settings.flux_height}
    )
    graph[FLUX_SAMPLER_NODE_ID]["inputs"].update({"seed": seed, "steps": settings.flux_steps})

    if reference_image_name:
        _inject_img2img_nodes(
            graph,
            IMG2IMG_LOAD_IMAGE_NODE_ID,
            IMG2IMG_VAE_ENCODE_NODE_ID,
            IMG2IMG_SCALE_NODE_ID,
            FLUX_SAMPLER_NODE_ID,
            [FLUX_VAE_NODE_ID, 0],
            reference_image_name,
            denoise,
            settings.flux_width,
            settings.flux_height,
        )

    return graph


def _build_anima_graph(
    positive_prompt: str,
    negative_prompt: str,
    seed: int,
    reference_image_name: str | None = None,
    denoise: float = 1.0,
) -> dict:
    graph = copy.deepcopy(_load_anima_workflow_template())

    graph[ANIMA_UNET_NODE_ID]["inputs"]["unet_name"] = settings.anima_unet_name
    graph[ANIMA_CLIP_NODE_ID]["inputs"]["clip_name"] = settings.anima_clip_name
    graph[ANIMA_CLIP_NODE_ID]["inputs"]["type"] = settings.anima_clip_type
    graph[ANIMA_VAE_NODE_ID]["inputs"]["vae_name"] = settings.anima_vae_name
    graph[ANIMA_POSITIVE_PROMPT_NODE_ID]["inputs"]["text"] = positive_prompt
    graph[ANIMA_NEGATIVE_PROMPT_NODE_ID]["inputs"]["text"] = negative_prompt
    graph[ANIMA_LATENT_NODE_ID]["inputs"].update(
        {"width": settings.anima_width, "height": settings.anima_height}
    )
    graph[ANIMA_SAMPLER_NODE_ID]["inputs"].update(
        {"seed": seed, "steps": settings.anima_steps, "cfg": settings.anima_cfg}
    )

    if reference_image_name:
        _inject_img2img_nodes(
            graph,
            IMG2IMG_LOAD_IMAGE_NODE_ID,
            IMG2IMG_VAE_ENCODE_NODE_ID,
            IMG2IMG_SCALE_NODE_ID,
            ANIMA_SAMPLER_NODE_ID,
            [ANIMA_VAE_NODE_ID, 0],
            reference_image_name,
            denoise,
            settings.anima_width,
            settings.anima_height,
        )

    return graph


def _load_flux_schnell_workflow_template() -> dict:
    return json.loads(settings.flux_schnell_workflow_template_path.read_text(encoding="utf-8"))


def _build_flux_schnell_graph(positive_prompt: str, seed: int) -> dict:
    graph = copy.deepcopy(_load_flux_schnell_workflow_template())

    graph[FLUX_SCHNELL_DOWNLOADER_NODE_ID]["inputs"]["model_version"] = (
        settings.flux_schnell_model_version
    )
    graph[FLUX_SCHNELL_GENERATE_NODE_ID]["inputs"].update(
        {
            "prompt": positive_prompt,
            "seed": seed,
            "width": settings.flux_schnell_width,
            "height": settings.flux_schnell_height,
            "steps": settings.flux_schnell_steps,
            "guidance": settings.flux_schnell_guidance,
        }
    )

    return graph


def _load_flux_kontext_workflow_template() -> dict:
    return json.loads(settings.flux_kontext_workflow_template_path.read_text(encoding="utf-8"))


def _build_flux_kontext_graph(
    positive_prompt: str,
    seed: int,
    reference_image_name: str,
) -> dict:
    """Graphe autonome — ne réutilise pas _inject_img2img_nodes() : l'image de
    référence est conditionnée via ReferenceLatent (pas un denoise partiel),
    voir flux_kontext_workflow.json. settings.flux_kontext_width/height ne
    sont pas câblés dans le graphe (FluxKontextImageScale calcule sa propre
    résolution cible à partir de l'image d'entrée) — reportés uniquement pour
    l'affichage UI."""
    graph = copy.deepcopy(_load_flux_kontext_workflow_template())

    graph[FLUX_KONTEXT_UNET_NODE_ID]["inputs"]["unet_name"] = settings.flux_kontext_unet_name
    graph[FLUX_KONTEXT_CLIP_NODE_ID]["inputs"]["clip_name1"] = settings.flux_kontext_clip_name1
    graph[FLUX_KONTEXT_CLIP_NODE_ID]["inputs"]["clip_name2"] = settings.flux_kontext_clip_name2
    graph[FLUX_KONTEXT_VAE_NODE_ID]["inputs"]["vae_name"] = settings.flux_kontext_vae_name
    graph[FLUX_KONTEXT_PROMPT_NODE_ID]["inputs"]["text"] = positive_prompt
    graph[FLUX_KONTEXT_LOAD_IMAGE_NODE_ID]["inputs"]["image"] = reference_image_name
    graph[FLUX_KONTEXT_GUIDANCE_NODE_ID]["inputs"]["guidance"] = settings.flux_kontext_guidance
    graph[FLUX_KONTEXT_SAMPLER_NODE_ID]["inputs"].update(
        {"seed": seed, "steps": settings.flux_kontext_steps}
    )

    return graph


def _unavailable_error(exc: Exception) -> ComfyUIUnavailableError:
    return ComfyUIUnavailableError(
        f"Impossible de contacter ComfyUI sur {settings.comfyui_base_url} — "
        "vérifiez qu'il est démarré."
    )


async def upload_reference_image(image_bytes: bytes) -> str:
    """POST /upload/image — voir ComfyUI/server.py::image_upload(). Renvoie le nom
    de fichier (+ sous-dossier éventuel) à utiliser dans le nœud LoadImage. Un nom
    aléatoire par requête évite toute collision entre générations concurrentes."""
    filename = f"ref_{uuid.uuid4().hex}.png"
    async with _build_client() as client:
        try:
            response = await client.post(
                "/upload/image",
                files={"image": (filename, image_bytes, "image/png")},
                data={"type": "input"},
            )
        except httpx.HTTPError as exc:
            raise _unavailable_error(exc) from exc

        if response.status_code != 200:
            raise ComfyUIGenerationError(
                f"Échec de l'upload de l'image de référence ({response.status_code})."
            )

        data = response.json()
        subfolder = data.get("subfolder") or ""
        return f"{subfolder}/{data['name']}" if subfolder else data["name"]


async def is_reachable() -> bool:
    try:
        async with _build_client() as client:
            response = await client.get("/system_stats", timeout=3.0)
            return response.status_code == 200
    except httpx.HTTPError:
        return False


async def _submit_and_wait(
    graph: dict, save_image_node_id: str, seed: int, timeout_seconds: float
) -> GenerationResult:
    async with _build_client() as client:
        try:
            submit_response = await client.post(
                "/prompt", json={"prompt": graph, "client_id": _CLIENT_ID}
            )
        except httpx.HTTPError as exc:
            raise _unavailable_error(exc) from exc

        if submit_response.status_code != 200:
            raise ComfyUIGenerationError(
                f"ComfyUI a refusé la requête ({submit_response.status_code}) : "
                f"{submit_response.text}"
            )

        submit_data = submit_response.json()
        node_errors = submit_data.get("node_errors") or {}
        if node_errors:
            raise ComfyUIGenerationError(f"Erreurs de graphe ComfyUI : {node_errors}")

        prompt_id = submit_data["prompt_id"]

        deadline = time.monotonic() + timeout_seconds
        outputs = None
        while time.monotonic() < deadline:
            try:
                history_response = await client.get(f"/history/{prompt_id}")
            except httpx.HTTPError as exc:
                raise _unavailable_error(exc) from exc

            history = history_response.json()
            entry = history.get(prompt_id)
            if entry and entry.get("outputs"):
                outputs = entry["outputs"]
                break

            await asyncio.sleep(settings.comfyui_poll_interval_seconds)

        if outputs is None:
            raise ComfyUITimeoutError(
                f"La génération n'a pas abouti après {timeout_seconds:.0f}s."
            )

        save_output = outputs.get(save_image_node_id)
        if not save_output or not save_output.get("images"):
            raise ComfyUIGenerationError("Aucune image produite par le nœud SaveImage attendu.")

        image_info = save_output["images"][0]
        try:
            view_response = await client.get(
                "/view",
                params={
                    "filename": image_info["filename"],
                    "subfolder": image_info.get("subfolder", ""),
                    "type": image_info.get("type", "output"),
                },
            )
        except httpx.HTTPError as exc:
            raise _unavailable_error(exc) from exc

        if view_response.status_code != 200:
            raise ComfyUIGenerationError(
                f"Impossible de récupérer l'image générée ({view_response.status_code})."
            )

        return GenerationResult(
            image_bytes=view_response.content, prompt_id=prompt_id, seed_used=seed
        )


async def generate_image(
    prompt: str,
    preset: PresetConfig,
    seed: int,
    reference_image_bytes: bytes | None = None,
    denoise: float = 0.6,
) -> GenerationResult:
    reference_image_name = (
        await upload_reference_image(reference_image_bytes) if reference_image_bytes else None
    )
    graph = _build_graph(prompt, preset, seed, reference_image_name, denoise)
    return await _submit_and_wait(
        graph, SAVE_IMAGE_NODE_ID, seed, settings.comfyui_timeout_seconds
    )


async def generate_image_flux(
    prompt: str,
    seed: int,
    reference_image_bytes: bytes | None = None,
    denoise: float = 0.6,
) -> GenerationResult:
    reference_image_name = (
        await upload_reference_image(reference_image_bytes) if reference_image_bytes else None
    )
    graph = _build_flux_graph(prompt, seed, reference_image_name, denoise)
    return await _submit_and_wait(
        graph, FLUX_SAVE_IMAGE_NODE_ID, seed, settings.flux_timeout_seconds
    )


async def generate_image_anima(
    prompt: str,
    negative_prompt: str,
    seed: int,
    reference_image_bytes: bytes | None = None,
    denoise: float = 0.6,
) -> GenerationResult:
    reference_image_name = (
        await upload_reference_image(reference_image_bytes) if reference_image_bytes else None
    )
    graph = _build_anima_graph(prompt, negative_prompt, seed, reference_image_name, denoise)
    return await _submit_and_wait(
        graph, ANIMA_SAVE_IMAGE_NODE_ID, seed, settings.anima_timeout_seconds
    )


async def generate_image_flux_schnell(prompt: str, seed: int) -> GenerationResult:
    graph = _build_flux_schnell_graph(prompt, seed)
    return await _submit_and_wait(
        graph, FLUX_SCHNELL_SAVE_IMAGE_NODE_ID, seed, settings.flux_schnell_timeout_seconds
    )


async def generate_image_flux_kontext(
    prompt: str, seed: int, reference_image_bytes: bytes
) -> GenerationResult:
    reference_image_name = await upload_reference_image(reference_image_bytes)
    graph = _build_flux_kontext_graph(prompt, seed, reference_image_name)
    return await _submit_and_wait(
        graph, FLUX_KONTEXT_SAVE_IMAGE_NODE_ID, seed, settings.flux_kontext_timeout_seconds
    )
