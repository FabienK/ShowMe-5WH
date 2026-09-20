from app.data.questions import QUESTION_ORDER, QUESTIONS
from app.data.translations import OPTION_TRANSLATIONS
from app.models.schemas import (
    AnswerInput,
    FreeTextAnswerInput,
    ListAnswerInput,
    QuestionKey,
    RandomAnswerInput,
    ResolvedAnswer,
)
from app.services.random_draw import draw_random_index
from app.services.translation import translate_to_english

# Cas particulier : une "Vue aérienne" combinée à un sujet humain/animal produit
# un sujet minuscule et quasi invisible (le modèle rend une échelle réaliste,
# comme une vraie photo aérienne). On bascule alors sur un cadrage plus proche
# qui garde le sujet visible tout en conservant l'idée de vue plongeante.
_AERIAL_VIEW_TEXT = "Vue aérienne"
_NO_SUBJECT_TEXT = "Aucun sujet (paysage pur)"
_AERIAL_VIEW_WITH_SUBJECT_TRANSLATION = "top-down view"


def resolve_answer(key: QuestionKey, answer_input: AnswerInput) -> ResolvedAnswer:
    options = QUESTIONS[key]["options"]

    if isinstance(answer_input, ListAnswerInput):
        if answer_input.index < 1 or answer_input.index > len(options):
            raise ValueError(
                f"Index {answer_input.index} hors limites pour la question '{key}' "
                f"({len(options)} propositions)."
            )
        text = options[answer_input.index - 1]
        return ResolvedAnswer(
            key=key, label=text, source="list", index=answer_input.index, text=text
        )

    if isinstance(answer_input, FreeTextAnswerInput):
        text = answer_input.text.strip()
        if not text:
            raise ValueError(f"Réponse libre vide pour la question '{key}'.")
        return ResolvedAnswer(key=key, label=text, source="free_text", index=None, text=text)

    if isinstance(answer_input, RandomAnswerInput):
        index = draw_random_index(len(options))
        text = options[index - 1]
        return ResolvedAnswer(key=key, label=text, source="random", index=index, text=text)

    raise TypeError(f"Type de réponse non supporté : {type(answer_input)!r}")


def resolve_global_random() -> dict[QuestionKey, ResolvedAnswer]:
    """Tire une réponse aléatoire pour les 5 questions ('tout générer pour moi')."""
    return {key: resolve_answer(key, RandomAnswerInput()) for key in QUESTION_ORDER}


def _translate_answer(key: QuestionKey, answers: dict[QuestionKey, ResolvedAnswer]) -> str:
    """Traduit une réponse en anglais pour l'envoi au modèle (voir data/translations.py).

    Le texte libre passe par le modèle de traduction local (voir
    services/translation.py) plutôt que par la table statique.
    """
    answer = answers[key]

    if answer.source == "free_text":
        return translate_to_english(answer.text)

    if key == "how" and answer.text == _AERIAL_VIEW_TEXT:
        who = answers.get("who")
        if who is not None and who.text != _NO_SUBJECT_TEXT:
            return _AERIAL_VIEW_WITH_SUBJECT_TRANSLATION

    return OPTION_TRANSLATIONS[key].get(answer.text, answer.text)


def build_script(answers: dict[QuestionKey, ResolvedAnswer]) -> str:
    """Assemble le script final en anglais, façon tags Stable Diffusion séparés par virgules."""
    return ", ".join(_translate_answer(key, answers) for key in QUESTION_ORDER)
