from app.data.questions import QUESTION_ORDER, QUESTIONS
from app.models.schemas import (
    AnswerInput,
    FreeTextAnswerInput,
    ListAnswerInput,
    QuestionKey,
    RandomAnswerInput,
    ResolvedAnswer,
)
from app.services.random_draw import draw_random_index


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


def build_script(answers: dict[QuestionKey, ResolvedAnswer]) -> str:
    """Assemble le script final, façon tags Stable Diffusion séparés par virgules."""
    return ", ".join(answers[key].text for key in QUESTION_ORDER)
