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


def _build_graph(positive_prompt: str, preset: PresetConfig, seed: int) -> dict:
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
                "strength_model": 1.0,
                "strength_clip": 1.0,
                "model": [CHECKPOINT_NODE_ID, 0],
                "clip": [CHECKPOINT_NODE_ID, 1],
            },
        }
        graph[SAMPLER_NODE_ID]["inputs"]["model"] = [LORA_NODE_ID, 0]
        graph[POSITIVE_PROMPT_NODE_ID]["inputs"]["clip"] = [LORA_NODE_ID, 1]
        graph[NEGATIVE_PROMPT_NODE_ID]["inputs"]["clip"] = [LORA_NODE_ID, 1]

    return graph


def _unavailable_error(exc: Exception) -> ComfyUIUnavailableError:
    return ComfyUIUnavailableError(
        f"Impossible de contacter ComfyUI sur {settings.comfyui_base_url} — "
        "vérifiez qu'il est démarré."
    )


async def is_reachable() -> bool:
    try:
        async with _build_client() as client:
            response = await client.get("/system_stats", timeout=3.0)
            return response.status_code == 200
    except httpx.HTTPError:
        return False


async def generate_image(prompt: str, preset: PresetConfig, seed: int) -> GenerationResult:
    graph = _build_graph(prompt, preset, seed)

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

        deadline = time.monotonic() + settings.comfyui_timeout_seconds
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
                f"La génération n'a pas abouti après {settings.comfyui_timeout_seconds:.0f}s."
            )

        save_output = outputs.get(SAVE_IMAGE_NODE_ID)
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
