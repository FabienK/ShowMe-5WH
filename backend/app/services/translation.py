"""Traduction français -> anglais du texte libre saisi par l'utilisateur.

Utilise Argos Translate (modèle NMT embarqué, CTranslate2) plutôt qu'une API
externe : la traduction reste 100% locale une fois le modèle installé via
scripts/install_translation_model.sh (voir data/translations.py pour les
options fixes, déjà traduites statiquement et non concernées par ce module).
"""

import logging
from functools import lru_cache

import argostranslate.translate

logger = logging.getLogger(__name__)

_FROM_CODE = "fr"
_TO_CODE = "en"


@lru_cache(maxsize=1)
def _get_translation() -> argostranslate.translate.ITranslation | None:
    installed = argostranslate.translate.get_installed_languages()
    from_lang = next((lang for lang in installed if lang.code == _FROM_CODE), None)
    to_lang = next((lang for lang in installed if lang.code == _TO_CODE), None)
    if from_lang is None or to_lang is None:
        logger.warning(
            "Modèle de traduction %s->%s introuvable (lancez "
            "scripts/install_translation_model.sh). Texte libre envoyé tel quel, "
            "non traduit.",
            _FROM_CODE,
            _TO_CODE,
        )
        return None
    return from_lang.get_translation(to_lang)


def translate_to_english(text: str) -> str:
    """Traduit du texte libre français vers l'anglais pour le prompt image.

    Repli sur le texte original si le modèle de traduction n'est pas installé,
    pour ne jamais bloquer une génération.
    """
    translation = _get_translation()
    if translation is None:
        return text
    return translation.translate(text)
