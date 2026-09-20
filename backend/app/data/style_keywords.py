"""Mots-clés de détection de style pour le prompt libre (CAS 2).

Source : backend/presets/style_engine_map.md (colonne "Mots-clés
déclencheurs"), calibrés manuellement style par style. Un style absent
de ce dictionnaire ne peut pas être détecté depuis du texte libre et
retombe sur le preset généraliste.
"""

STYLE_KEYWORDS: dict[str, list[str]] = {
    "Bande dessinée": ["bande dessinée", "comics", "bd", "planche"],
    "Photoréaliste": ["photo réaliste", "photoréaliste", "réaliste", "photographie"],
    "Anime": ["anime", "manga"],
    "Peinture à l'huile": ["peinture à l'huile", "huile", "oil painting"],
    "Aquarelle": ["aquarelle", "watercolor"],
    "Pixel art": ["pixel art", "8-bit", "8 bit"],
    "3D render": ["3d render", "3d", "pixar"],
    "Croquis crayon": ["croquis", "crayon", "sketch"],
    "Cyberpunk": ["cyberpunk"],
    "Fantasy médiéval": ["fantasy", "médiéval", "medieval"],
    "Noir et blanc argentique": ["noir et blanc", "argentique"],
    "Pop art": ["pop art"],
    "Minimaliste vectoriel": ["minimaliste", "vectoriel"],
    "Surréaliste": ["surréaliste"],
    "Steampunk": ["steampunk"],
    "Gothique": ["gothique", "gothic"],
    "Art nouveau": ["art nouveau"],
    "Cartoon": ["cartoon"],
    "Isométrique": ["isométrique", "isometric"],
    "Impressionniste": ["impressionniste"],
}
