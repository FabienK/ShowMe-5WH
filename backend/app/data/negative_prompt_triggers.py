"""Déclencheurs français indiquant qu'un terme du prompt négatif est en fait recherché.

Chaque terme du prompt négatif (en anglais, tel qu'envoyé au modèle) est associé à
~5 expressions qu'un utilisateur francophone emploierait pour demander explicitement
cet effet dans son prompt libre — pas des synonymes stricts du terme, mais les
formulations réelles d'une intention artistique (ex. "flou artistique" plutôt que
"trouble" pour "blurry").
"""

NEGATIVE_TERM_TRIGGERS: dict[str, list[str]] = {
    "low quality": [
        "basse qualité",
        "qualité amateur",
        "esthétique vhs",
        "rendu lo-fi",
        "qualité dégradée",
    ],
    "worst quality": [
        "basse qualité",
        "qualité amateur",
        "esthétique vhs",
        "rendu lo-fi",
        "qualité dégradée",
    ],
    "blurry": [
        "flou",
        "flou artistique",
        "flou de mouvement",
        "mise au point douce",
        "bokeh",
    ],
    "deformed": [
        "déformé",
        "difforme",
        "anatomie surréaliste",
        "corps déformé",
        "monstrueux",
    ],
    "extra limbs": [
        "membres en trop",
        "bras supplémentaires",
        "plusieurs bras",
        "plusieurs têtes",
        "anatomie multiple",
    ],
    "watermark": [
        "watermark",
        "filigrane",
        "signature visible",
        "tampon",
        "logo visible",
    ],
    "jpeg artifacts": [
        "artefacts jpeg",
        "compression jpeg",
        "pixelisation",
        "effet de compression",
        "glitch de compression",
    ],
    "sepia": [
        "sépia",
        "ton sépia",
        "photo ancienne",
        "teinte brune vintage",
        "vieille photographie",
    ],
}

NEGATION_MARKERS: list[str] = [
    "sans",
    "pas de",
    "pas d'",
    "aucun",
    "aucune",
    "non ",
    "évite",
    "éviter",
    "évitez",
    "ni ",
    "jamais",
    "surtout pas",
]
