import json
import logging
import re
from functools import lru_cache

from app.config import settings
from app.models.schemas import ModelOption

logger = logging.getLogger(__name__)

_FLUX_LABEL = "Flux"
_FLUX_VERSION = "dev"
_FLUX_ESTIMATED_TIME = "~12 min"
_FLUX_DESCRIPTION = "Le rendu le plus fidèle et le plus détaillé disponible pour ce style."
_FLUX_NEGATIVE_PROMPT = "low quality, blurry, deformed, extra limbs, watermark"

_FLUX_SCHNELL_VERSION = "schnell"
_FLUX_SCHNELL_ESTIMATED_TIME = "~2 min 30"
_FLUX_SCHNELL_DESCRIPTION = "Aussi rapide qu'un modèle standard, avec la composition de Flux."
_FLUX_SCHNELL_NEGATIVE_PROMPT = "low quality, blurry, deformed, extra limbs, watermark"

_FLUX_KONTEXT_LABEL = "Flux Kontext"
_FLUX_KONTEXT_VERSION = "dev"
# Mesuré deux fois sur ce Mac (24 Go RAM unifiée) : ~25-26 min à chaque fois, pas
# seulement au premier chargement — ComfyUI ne garde qu'un seul gros modèle en
# mémoire à la fois, donc le GGUF (9.85 Go) est rechargé dès qu'un autre modèle a
# tourné entre-temps, ce qui est le cas courant vu l'usage multi-moteurs de l'app.
_FLUX_KONTEXT_ESTIMATED_TIME = "~26 min"
_FLUX_KONTEXT_DESCRIPTION = "Modifie ta photo en gardant la pose et l'identité intactes."

_OPENAI_LABEL = "GPT Image 2"
_OPENAI_VERSION = "cloud"
_OPENAI_ESTIMATED_TIME = "~20s"
_OPENAI_DESCRIPTION = (
    "Génération via l'API OpenAI, payante — voir le solde estimé sur le bouton."
)

_ACCENTS = str.maketrans(
    {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "î": "i", "ï": "i",
        "ô": "o", "ö": "o",
        "û": "u", "ü": "u", "ù": "u",
        "ç": "c",
        "'": " ",
    }
)


def _slugify(style: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", style.lower().translate(_ACCENTS)).strip("_")


def _ensure_flux_option(style: str, models: list[ModelOption]) -> list[ModelOption]:
    """Le modèle Flux doit être proposé quel que soit le style : s'il n'est pas
    déjà défini dans presets.json pour ce style, on l'ajoute automatiquement
    (le moteur flux ignore de toute façon checkpoint/sampler/résolution du
    preset, voir routers/generate.py::_preset_used)."""
    if any(model.engine_type == "flux" for model in models):
        return models
    flux_option = ModelOption(
        id=f"flux_{_slugify(style)}",
        label=_FLUX_LABEL,
        version=_FLUX_VERSION,
        estimated_time=_FLUX_ESTIMATED_TIME,
        description=_FLUX_DESCRIPTION,
        engine_type="flux",
        negative_prompt=_FLUX_NEGATIVE_PROMPT,
    )
    return [*models, flux_option]


def _ensure_flux_schnell_option(style: str, models: list[ModelOption]) -> list[ModelOption]:
    """Le modèle Flux schnell doit être proposé quel que soit le style, comme
    Flux dev (voir _ensure_flux_option) : s'il n'est pas déjà défini dans
    presets.json pour ce style, on l'ajoute automatiquement."""
    if any(model.engine_type == "flux_schnell" for model in models):
        return models
    flux_schnell_option = ModelOption(
        id=f"flux_schnell_{_slugify(style)}",
        label=_FLUX_LABEL,
        version=_FLUX_SCHNELL_VERSION,
        estimated_time=_FLUX_SCHNELL_ESTIMATED_TIME,
        description=_FLUX_SCHNELL_DESCRIPTION,
        engine_type="flux_schnell",
        negative_prompt=_FLUX_SCHNELL_NEGATIVE_PROMPT,
    )
    return [*models, flux_schnell_option]


def _ensure_flux_kontext_option(style: str, models: list[ModelOption]) -> list[ModelOption]:
    """Flux Kontext doit être proposé quel que soit le style, comme Flux dev/
    schnell (voir _ensure_flux_option) : s'il n'est pas déjà défini dans
    presets.json pour ce style, on l'ajoute automatiquement. Contrairement à
    flux/flux_schnell, ce moteur exige une image de référence (voir
    routers/generate.py) — la visibilité réelle est filtrée côté frontend
    (n'apparaît que si une image de référence est attachée), le backend
    reste le garde-fou (422 si absente, défense en profondeur comme pour
    flux_schnell)."""
    if any(model.engine_type == "flux_kontext" for model in models):
        return models
    flux_kontext_option = ModelOption(
        id=f"flux_kontext_{_slugify(style)}",
        label=_FLUX_KONTEXT_LABEL,
        version=_FLUX_KONTEXT_VERSION,
        estimated_time=_FLUX_KONTEXT_ESTIMATED_TIME,
        description=_FLUX_KONTEXT_DESCRIPTION,
        engine_type="flux_kontext",
    )
    return [*models, flux_kontext_option]


def _ensure_openai_option(style: str, models: list[ModelOption]) -> list[ModelOption]:
    """GPT Image 2 doit être proposé quel que soit le style, comme Flux dev/
    schnell/Kontext (voir _ensure_flux_option) : s'il n'est pas déjà défini
    dans presets.json pour ce style, on l'ajoute automatiquement. Contrairement
    aux moteurs ComfyUI, ce moteur est payant — checkpoint/sampler/résolution
    du preset sont ignorés (voir routers/generate.py::preset_used), la
    résolution utilisée est width/height (1024x1024 par défaut, voir
    services/openai_generator.py)."""
    if any(model.engine_type == "openai" for model in models):
        return models
    openai_option = ModelOption(
        id=f"openai_{_slugify(style)}",
        label=_OPENAI_LABEL,
        version=_OPENAI_VERSION,
        estimated_time=_OPENAI_ESTIMATED_TIME,
        description=_OPENAI_DESCRIPTION,
        engine_type="openai",
        width=1024,
        height=1024,
    )
    return [*models, openai_option]


@lru_cache(maxsize=1)
def load_style_models() -> dict[str, list[ModelOption]]:
    if not settings.presets_path.exists():
        raise FileNotFoundError(
            f"Fichier de presets introuvable : {settings.presets_path}. "
            "Voir backend/presets/presets.json."
        )
    raw = json.loads(settings.presets_path.read_text(encoding="utf-8"))
    styles = {
        style: [ModelOption(**model) for model in config["models"]]
        for style, config in raw.items()
    }
    if not styles.get("default"):
        raise ValueError(
            "Le fichier de presets doit contenir une entrée 'default' avec au moins un modèle."
        )
    return styles


def resolve_style_models(style: str | None) -> list[ModelOption]:
    """CAS 1 / CAS 2 (voir style_engine_map.md) : modèles disponibles pour un
    style, ou modèle généraliste si aucun style n'est identifié. Flux dev,
    Flux schnell, Flux Kontext et GPT Image 2 sont toujours proposés en plus,
    quel que soit le style."""
    styles = load_style_models()
    if style is None:
        models = styles["default"]
        source_style = "default"
    else:
        models = styles.get(style)
        if not models:
            logger.warning(
                "Aucun modèle pour le style '%s', utilisation du modèle généraliste.", style
            )
            models = styles["default"]
            source_style = "default"
        else:
            source_style = style
    models = _ensure_flux_option(source_style, models)
    models = _ensure_flux_schnell_option(source_style, models)
    models = _ensure_flux_kontext_option(source_style, models)
    return _ensure_openai_option(source_style, models)


def resolve_model(style: str | None, model_id: str | None) -> ModelOption:
    """Résout le ModelOption à utiliser pour la génération.

    Un seul modèle disponible pour le style -> auto-sélection (model_id
    peut être omis). Plusieurs modèles -> model_id doit désigner l'un
    d'eux.
    """
    models = resolve_style_models(style)
    if model_id is None:
        if len(models) == 1:
            return models[0]
        raise ValueError(
            "Plusieurs modèles sont disponibles pour ce style, model_id est requis "
            f"(choix possibles : {', '.join(model.id for model in models)})."
        )
    for model in models:
        if model.id == model_id:
            return model
    raise ValueError(f"model_id inconnu pour ce style : {model_id}")
