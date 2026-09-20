from app.data.style_keywords import STYLE_KEYWORDS


def detect_style(text: str) -> str | None:
    """Détecte un style à partir de mots-clés dans un texte libre (CAS 2).

    Voir backend/presets/style_engine_map.md pour la logique de résolution
    style -> modèle. En cas de mots-clés de styles différents présents dans
    le même texte, le mot-clé le plus long l'emporte (favorise les
    correspondances les plus spécifiques, ex. "aquarelle" plutôt que
    "peinture").
    """
    lowered = text.lower()
    best_style: str | None = None
    best_length = 0
    for style, keywords in STYLE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered and len(keyword) > best_length:
                best_style = style
                best_length = len(keyword)
    return best_style
