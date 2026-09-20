from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    FreePromptScriptRequest,
    GlobalRandomScriptRequest,
    PerQuestionScriptRequest,
    ResolvedAnswer,
    ScriptRequest,
    ScriptResponse,
)
from app.services.presets import resolve_style_models
from app.services.script_builder import build_script, resolve_answer, resolve_global_random
from app.services.style_detection import detect_style
from app.services.translation import translate_to_english

router = APIRouter(tags=["script"])


def _resolve_what_style(what_answer: ResolvedAnswer) -> str | None:
    """Style connu tel quel (liste/tirage) ou détecté par mots-clés (texte libre)."""
    if what_answer.source == "free_text":
        return detect_style(what_answer.text)
    return what_answer.text


@router.post("/script", response_model=ScriptResponse)
def post_script(request: ScriptRequest) -> ScriptResponse:
    if isinstance(request, FreePromptScriptRequest):
        # Détection de style sur le texte original : les mots-clés (voir
        # style_keywords.py) sont en français, avant toute traduction.
        # Un prompt vide (mode image de référence sans texte de guidage) saute
        # la détection de style et la traduction : pas de style, pas de script.
        if not request.prompt.strip():
            return ScriptResponse(
                mode=request.mode,
                answers=None,
                script="",
                style=None,
                models=resolve_style_models(None),
            )
        style = detect_style(request.prompt)
        return ScriptResponse(
            mode=request.mode,
            answers=None,
            script=translate_to_english(request.prompt),
            style=style,
            models=resolve_style_models(style),
        )

    if isinstance(request, GlobalRandomScriptRequest):
        answers = resolve_global_random()
        style = _resolve_what_style(answers["what"])
        return ScriptResponse(
            mode=request.mode,
            answers=answers,
            script=build_script(answers),
            style=style,
            models=resolve_style_models(style),
        )

    if isinstance(request, PerQuestionScriptRequest):
        try:
            answers = {key: resolve_answer(key, value) for key, value in request.answers.items()}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        style = _resolve_what_style(answers["what"])
        return ScriptResponse(
            mode=request.mode,
            answers=answers,
            script=build_script(answers),
            style=style,
            models=resolve_style_models(style),
        )

    raise HTTPException(status_code=422, detail="Mode de script inconnu.")
