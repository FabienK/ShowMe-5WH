from fastapi import APIRouter

from app.config import settings
from app.models.schemas import OpenAIBalanceUpdateRequest, OpenAIState
from app.services import openai_state_store

router = APIRouter(prefix="/openai", tags=["openai"])


def _estimated_cost_per_generation() -> float:
    """Estimation affichée avant l'appel (voir config.py) — le coût réel
    décrémenté après une génération vient toujours des tokens effectivement
    consommés (openai_generator.py::cost_from_usage), jamais de cette
    estimation."""
    return (
        settings.openai_estimated_text_input_tokens
        * settings.openai_price_per_text_input_token_usd
        + settings.openai_estimated_output_tokens_per_image
        * settings.openai_price_per_output_token_usd
    )


def _state() -> OpenAIState:
    return OpenAIState(
        balance_usd=openai_state_store.read_balance(),
        price_per_text_input_token_usd=settings.openai_price_per_text_input_token_usd,
        price_per_image_input_token_usd=settings.openai_price_per_image_input_token_usd,
        price_per_cached_image_input_token_usd=settings.openai_price_per_cached_image_input_token_usd,
        price_per_output_token_usd=settings.openai_price_per_output_token_usd,
        estimated_cost_per_generation_usd=_estimated_cost_per_generation(),
    )


@router.get("/balance", response_model=OpenAIState)
async def get_balance() -> OpenAIState:
    return _state()


@router.put("/balance", response_model=OpenAIState)
async def put_balance(request: OpenAIBalanceUpdateRequest) -> OpenAIState:
    """Resynchronisation manuelle — l'utilisateur renseigne le solde réel de
    son compte OpenAI après un rechargement (aucun endpoint OpenAI fiable
    n'existe pour le lire automatiquement, voir
    openai-fallback-implementation.md)."""
    openai_state_store.set_balance(request.balance_usd)
    return _state()
