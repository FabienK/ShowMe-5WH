from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    FreePromptScriptRequest,
    GlobalRandomScriptRequest,
    PerQuestionScriptRequest,
    ScriptRequest,
    ScriptResponse,
)
from app.services.script_builder import build_script, resolve_answer, resolve_global_random

router = APIRouter(tags=["script"])


@router.post("/script", response_model=ScriptResponse)
def post_script(request: ScriptRequest) -> ScriptResponse:
    if isinstance(request, FreePromptScriptRequest):
        return ScriptResponse(mode=request.mode, answers=None, script=request.prompt, style=None)

    if isinstance(request, GlobalRandomScriptRequest):
        answers = resolve_global_random()
        return ScriptResponse(
            mode=request.mode,
            answers=answers,
            script=build_script(answers),
            style=answers["what"].text,
        )

    if isinstance(request, PerQuestionScriptRequest):
        try:
            answers = {key: resolve_answer(key, value) for key, value in request.answers.items()}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return ScriptResponse(
            mode=request.mode,
            answers=answers,
            script=build_script(answers),
            style=answers["what"].text,
        )

    raise HTTPException(status_code=422, detail="Mode de script inconnu.")
