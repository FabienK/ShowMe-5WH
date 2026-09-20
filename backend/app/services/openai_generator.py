"""Génération d'image via l'API OpenAI (GPT Image 2) — moteur "openai" au
même niveau que les moteurs locaux ComfyUI (voir generation_dispatch.py),
pas un fallback caché.

Le coût réel de chaque génération est calculé après coup depuis les tokens
effectivement consommés (ImagesResponse.usage), pas depuis un tarif fixe par
résolution/qualité : la facturation OpenAI est au token
(developers.openai.com/api/docs/pricing), un prix par image serait une
approximation supplémentaire sur une valeur déjà estimative (voir
openai_state_store.py). Les tarifs $/token vérifiés sont dans config.py.
"""

import base64
import uuid
from datetime import datetime, timezone
from pathlib import Path

import openai

from app.config import settings
from app.services.comfyui_client import GenerationResult

# GPT Image 2 n'accepte que ces trois tailles (openai.types.ImagesResponse.size) ;
# les modèles locaux du projet utilisent d'autres résolutions (512x512 SDXL,
# etc.), donc on retombe sur le carré 1024 par défaut pour toute résolution
# non supportée plutôt que de faire échouer l'appel.
_SUPPORTED_SIZES = {"1024x1024", "1536x1024", "1024x1536"}


class OpenAIMissingApiKeyError(Exception):
    """OPENAI_API_KEY absente/vide — vérifié avant tout appel SDK pour un
    échec explicite et lisible, plutôt que de laisser l'erreur d'auth du SDK
    remonter telle quelle."""


class OpenAIGenerationError(Exception):
    """Échec de l'appel OpenAI : réseau, quota/rate-limit, refus de
    modération, erreur d'auth au moment de l'appel, ou toute autre exception
    du SDK. openai.OpenAIError est la classe de base commune à toutes les
    exceptions du SDK (APIConnectionError, APITimeoutError,
    AuthenticationError, RateLimitError, BadRequestError...) ; on ne les
    distingue pas plus finement en V1, le message d'origine est conservé."""


def _client() -> openai.AsyncOpenAI:
    """Point d'extension unique pour les tests : monkeypatcher cette
    fonction pour injecter un client lié à un httpx2.MockTransport, même
    principe que comfyui_client._build_client."""
    return openai.AsyncOpenAI(api_key=settings.openai_api_key)


def _resolve_size(width: int, height: int) -> str:
    size = f"{width}x{height}"
    return size if size in _SUPPORTED_SIZES else "1024x1024"


def save_image(image_bytes: bytes) -> Path:
    """Copie sur disque une image GPT Image 2 générée hors batch (voir
    routers/generate.py), pour ne pas la perdre si l'utilisateur ne clique
    pas sur télécharger — même besoin que generated_batches_dir pour le
    batch, mais un simple fichier par génération, pas de manifest."""
    settings.generated_openai_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    image_path = settings.generated_openai_dir / f"{stamp}_{uuid.uuid4().hex[:8]}.png"
    image_path.write_bytes(image_bytes)
    return image_path


def cost_from_usage(usage: openai.types.images_response.Usage | None) -> float:
    """Calcule le coût réel en USD à partir des tokens effectivement
    consommés — voir les tarifs $/token vérifiés dans config.py."""
    if usage is None:
        return 0.0
    details = usage.input_tokens_details
    return (
        details.text_tokens * settings.openai_price_per_text_input_token_usd
        + details.image_tokens * settings.openai_price_per_image_input_token_usd
        + usage.output_tokens * settings.openai_price_per_output_token_usd
    )


async def generate_via_openai(
    prompt: str, width: int, height: int, seed: int
) -> tuple[GenerationResult, float]:
    """Ne décrémente PAS le solde local — c'est la responsabilité de
    l'appelant (generation_dispatch.py), uniquement après un retour réussi
    de cette fonction. seed n'a aucun effet sur GPT Image 2 (pas de contrôle
    de seed exposé par l'API) : renvoyé tel quel dans le GenerationResult
    pour satisfaire le schéma GenerateResponse existant (seed_used non
    optionnel)."""
    if not settings.openai_api_key:
        raise OpenAIMissingApiKeyError(
            "OPENAI_API_KEY n'est pas configurée — renseignez-la dans backend/.env "
            "pour activer la génération via GPT Image 2."
        )

    try:
        async with _client() as client:
            response = await client.images.generate(
                model="gpt-image-2",
                prompt=prompt,
                size=_resolve_size(width, height),
                quality=settings.openai_default_quality,
                n=1,
            )
    except openai.OpenAIError as exc:
        raise OpenAIGenerationError(str(exc)) from exc

    if not response.data or response.data[0].b64_json is None:
        raise OpenAIGenerationError("Réponse OpenAI sans image (aucune donnée b64_json).")

    image_bytes = base64.b64decode(response.data[0].b64_json)
    cost_usd = cost_from_usage(response.usage)

    result = GenerationResult(
        image_bytes=image_bytes,
        prompt_id=f"openai-{uuid.uuid4().hex}",
        seed_used=seed,
    )
    return result, cost_usd
