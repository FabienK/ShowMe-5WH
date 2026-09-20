"""Décodage et validation d'une image de référence envoyée en base64 (mode img2img).

Seul point d'entrée où des octets contrôlés par l'utilisateur sont transmis vers
une écriture disque côté ComfyUI (POST /upload/image -> ComfyUI/input/). On
vérifie ici que les octets décodent réellement comme une image avant de les
transmettre, et on les ré-encode en PNG pour ne renvoyer que ce que Pillow a
effectivement décodé comme pixels (pas seulement des octets qui commencent par
un header valide).
"""

import base64
import binascii
import re
from io import BytesIO

from PIL import Image, UnidentifiedImageError

_DATA_URL_PATTERN = re.compile(r"^data:image/(png|jpe?g|webp);base64,(.+)$", re.IGNORECASE | re.DOTALL)
_MAX_BYTES = 10 * 1024 * 1024


class InvalidReferenceImageError(ValueError):
    """L'image de référence fournie n'est pas exploitable (format, taille, corruption)."""


def decode_and_validate_reference_image(data_url: str) -> bytes:
    match = _DATA_URL_PATTERN.match(data_url.strip())
    if not match:
        raise InvalidReferenceImageError(
            "Format d'image invalide : attendu une data URL data:image/(png|jpeg|webp);base64,..."
        )

    try:
        raw = base64.b64decode(match.group(2), validate=True)
    except binascii.Error as exc:
        raise InvalidReferenceImageError("Image de référence : contenu base64 invalide.") from exc

    if len(raw) > _MAX_BYTES:
        raise InvalidReferenceImageError("Image de référence trop volumineuse (10 Mo max).")

    try:
        with Image.open(BytesIO(raw)) as image:
            image.load()
            rgb_image = image.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidReferenceImageError("Image de référence illisible ou corrompue.") from exc

    output = BytesIO()
    rgb_image.save(output, format="PNG")
    return output.getvalue()
