import json
import logging
from functools import lru_cache

from app.config import settings
from app.models.schemas import PresetConfig

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_presets() -> dict[str, PresetConfig]:
    if not settings.presets_path.exists():
        raise FileNotFoundError(
            f"Fichier de presets introuvable : {settings.presets_path}. "
            "Voir backend/presets/presets.json."
        )
    raw = json.loads(settings.presets_path.read_text(encoding="utf-8"))
    presets = {style: PresetConfig(**config) for style, config in raw.items()}
    if "default" not in presets:
        raise ValueError("Le fichier de presets doit contenir une entrée 'default'.")
    return presets


def resolve_preset(style: str | None) -> PresetConfig:
    presets = load_presets()
    if style is None:
        return presets["default"]
    preset = presets.get(style)
    if preset is None:
        logger.warning(
            "Aucun preset pour le style '%s', utilisation du preset 'default'.", style
        )
        return presets["default"]
    return preset
