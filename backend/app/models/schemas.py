from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    prompt: str = ""


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


# --- Résolution style → modèle(s) ---
#
# Voir backend/presets/style_engine_map.md pour la logique CAS 1 / CAS 2 :
# un style avec plusieurs modèles calibrés propose le choix (avec leurs
# caractéristiques) ; un style avec un seul modèle génère automatiquement ;
# l'absence de style (prompt libre sans mot-clé détecté) utilise le modèle
# généraliste.


class ModelOption(BaseModel):
    id: str
    label: str
    version: str = ""
    estimated_time: str = ""
    description: str
    engine_type: Literal[
        "sd_checkpoint", "flux", "anima", "flux_schnell", "flux_kontext", "openai"
    ] = "sd_checkpoint"
    checkpoint: str | None = None
    lora: str | None = None
    lora_strength: float = 1.0
    sampler: str = "euler"
    scheduler: str = "normal"
    steps: int = 20
    cfg: float = 7.0
    width: int = 512
    height: int = 512
    negative_prompt: str = ""


class ScriptResponse(BaseModel):
    mode: Literal["free_prompt", "global_random", "per_question"]
    answers: dict[QuestionKey, ResolvedAnswer] | None = None
    script: str
    style: str | None = None
    models: list[ModelOption]


# --- Génération d'image ---


class GenerateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    script: str = ""
    style: str | None = None
    seed: int | None = None
    model_id: str | None = None
    reference_image: str | None = None
    denoise_strength: float = Field(default=0.6, ge=0.1, le=1.0)

    @field_validator("style")
    @classmethod
    def style_must_be_known(cls, value: str | None) -> str | None:
        if value is not None and value not in QUESTIONS["what"]["options"]:
            raise ValueError(f"Style inconnu : {value}")
        return value

    @model_validator(mode="after")
    def script_or_reference_image_required(self) -> "GenerateRequest":
        if not self.script.strip() and self.reference_image is None:
            raise ValueError("Un script ou une image de référence est requis.")
        return self


class PresetConfig(BaseModel):
    checkpoint: str
    lora: str | None = None
    lora_strength: float = 1.0
    sampler: str
    scheduler: str
    steps: int
    cfg: float
    width: int
    height: int
    negative_prompt: str = ""


class PresetUsed(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    style: str
    model_id: str
    model_label: str
    model_version: str
    estimated_time: str
    checkpoint: str
    lora: str | None
    sampler: str
    scheduler: str
    steps: int
    cfg: float
    width: int
    height: int
    denoise_strength: float | None = None


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


# --- Génération via OpenAI (GPT Image 2) ---
#
# Solde purement local et estimatif : aucun endpoint OpenAI fiable n'existe
# pour lire le vrai solde de crédit du compte, voir
# openai-fallback-implementation.md. L'utilisateur le resynchronise
# manuellement (PUT /api/openai/balance) après un rechargement ; l'app le
# décrémente automatiquement après chaque génération réussie, à partir du
# coût réel calculé depuis les tokens consommés (services/openai_generator.py).


class OpenAIState(BaseModel):
    balance_usd: float
    price_per_text_input_token_usd: float
    price_per_image_input_token_usd: float
    price_per_cached_image_input_token_usd: float
    price_per_output_token_usd: float
    estimated_cost_per_generation_usd: float


class OpenAIBalanceUpdateRequest(BaseModel):
    balance_usd: float = Field(ge=0)


# --- Génération par lot (batch) ---
#
# Un batch est une liste de GenerateRequest indépendantes (script/style/
# model_id/image de référence propres à chacune), exécutées en séquence côté
# serveur (jamais en parallèle — ComfyUI ne traite qu'un job à la fois). Pas
# de base de données : chaque batch est un dossier sur disque contenant un
# manifest.json (ce modèle sérialisé) réécrit après chaque item, voir
# services/batch_store.py et services/batch_runner.py.

BatchItemStatus = Literal["pending", "running", "success", "error"]
BatchStatus = Literal["running", "completed", "interrupted"]


class BatchItemResult(BaseModel):
    index: int
    request: GenerateRequest
    status: BatchItemStatus = "pending"
    image_path: str | None = None
    prompt_id: str | None = None
    seed_used: int | None = None
    preset_used: PresetUsed | None = None
    error_type: str | None = None
    error_detail: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class BatchCreateRequest(BaseModel):
    items: list[GenerateRequest] = Field(min_length=1)


class BatchCreateResponse(BaseModel):
    batch_id: str


class BatchSummary(BaseModel):
    batch_id: str
    status: BatchStatus
    created_at: str
    total_items: int
    completed_items: int
    error_items: int


class BatchListResponse(BaseModel):
    batches: list[BatchSummary]


class BatchDetailResponse(BaseModel):
    batch_id: str
    status: BatchStatus
    created_at: str
    items: list[BatchItemResult]
