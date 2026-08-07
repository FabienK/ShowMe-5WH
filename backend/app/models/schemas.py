from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from app.data.questions import QUESTION_ORDER, QUESTIONS

QuestionKey = Literal["what", "who", "where", "when", "how"]


class QuestionDefinition(BaseModel):
    key: QuestionKey
    label: str
    options: list[str]


class QuestionsResponse(BaseModel):
    questions: list[QuestionDefinition]


# --- Réponse à une question isolée ---


class ListAnswerInput(BaseModel):
    source: Literal["list"] = "list"
    index: int = Field(ge=1, le=20)


class FreeTextAnswerInput(BaseModel):
    source: Literal["free_text"] = "free_text"
    text: str = Field(min_length=1)


class RandomAnswerInput(BaseModel):
    source: Literal["random"] = "random"


AnswerInput = Annotated[
    Union[ListAnswerInput, FreeTextAnswerInput, RandomAnswerInput],
    Field(discriminator="source"),
]


class ResolvedAnswer(BaseModel):
    key: QuestionKey
    label: str
    source: Literal["list", "free_text", "random"]
    index: int | None = None
    text: str


# --- Requête d'assemblage de script ---


class FreePromptScriptRequest(BaseModel):
    mode: Literal["free_prompt"] = "free_prompt"
    prompt: str = Field(min_length=1)


class GlobalRandomScriptRequest(BaseModel):
    mode: Literal["global_random"] = "global_random"


class PerQuestionScriptRequest(BaseModel):
    mode: Literal["per_question"] = "per_question"
    answers: dict[QuestionKey, AnswerInput]

    @model_validator(mode="after")
    def check_all_questions_answered(self) -> "PerQuestionScriptRequest":
        missing = [key for key in QUESTION_ORDER if key not in self.answers]
        if missing:
            raise ValueError(f"Réponses manquantes pour : {', '.join(missing)}")
        return self


ScriptRequest = Annotated[
    Union[FreePromptScriptRequest, GlobalRandomScriptRequest, PerQuestionScriptRequest],
    Field(discriminator="mode"),
]


class ScriptResponse(BaseModel):
    mode: Literal["free_prompt", "global_random", "per_question"]
    answers: dict[QuestionKey, ResolvedAnswer] | None = None
    script: str
    style: str | None = None


# --- Génération d'image ---


class GenerateRequest(BaseModel):
    script: str = Field(min_length=1)
    style: str | None = None
    seed: int | None = None

    @field_validator("style")
    @classmethod
    def style_must_be_known(cls, value: str | None) -> str | None:
        if value is not None and value not in QUESTIONS["what"]["options"]:
            raise ValueError(f"Style inconnu : {value}")
        return value


class PresetConfig(BaseModel):
    checkpoint: str
    lora: str | None = None
    sampler: str
    scheduler: str
    steps: int
    cfg: float
    width: int
    height: int
    negative_prompt: str = ""


class PresetUsed(BaseModel):
    style: str
    checkpoint: str
    lora: str | None
    sampler: str
    scheduler: str
    steps: int
    cfg: float
    width: int
    height: int


class GenerateResponse(BaseModel):
    status: Literal["success"] = "success"
    image_base64: str
    prompt_id: str
    seed_used: int
    preset_used: PresetUsed


class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    error_type: str
    detail: str


class ComfyUIStatusResponse(BaseModel):
    reachable: bool
