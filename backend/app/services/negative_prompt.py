"""Résolution des conflits entre le prompt positif libre et le prompt négatif du modèle.

Si l'utilisateur demande explicitement un effet couvert par le prompt négatif
(ex. "flou artistique"), le terme correspondant est retiré du négatif — sauf si
sa formulation est en réalité une négation (ex. "sans flou"), auquel cas le
négatif est conservé tel quel.
"""

from app.data.negative_prompt_triggers import NEGATION_MARKERS, NEGATIVE_TERM_TRIGGERS

_NEGATION_WINDOW_CHARS = 30


def _is_negated(lowered_prompt: str, trigger_start: int) -> bool:
    window = lowered_prompt[max(0, trigger_start - _NEGATION_WINDOW_CHARS) : trigger_start]
    return any(marker in window for marker in NEGATION_MARKERS)


def strip_negative_conflicts(positive_prompt: str, negative_prompt: str) -> str:
    """Retire du prompt négatif les termes explicitement demandés dans le prompt positif."""
    if not negative_prompt:
        return negative_prompt

    lowered_positive = positive_prompt.lower()
    kept_terms = []

    for raw_term in negative_prompt.split(","):
        term = raw_term.strip()
        if not term:
            continue

        triggers = NEGATIVE_TERM_TRIGGERS.get(term.lower(), [])
        conflict = any(
            (index := lowered_positive.find(trigger)) != -1 and not _is_negated(lowered_positive, index)
            for trigger in triggers
        )

        if not conflict:
            kept_terms.append(term)

    return ", ".join(kept_terms)
