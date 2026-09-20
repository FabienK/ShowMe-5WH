import pytest

from app.data.questions import QUESTION_ORDER, QUESTIONS
from app.data.translations import OPTION_TRANSLATIONS
from app.models.schemas import (
    FreeTextAnswerInput,
    ListAnswerInput,
    RandomAnswerInput,
    ResolvedAnswer,
)
from app.services.script_builder import build_script, resolve_answer, resolve_global_random


def test_resolve_answer_list() -> None:
    resolved = resolve_answer("what", ListAnswerInput(index=1))
    assert resolved.source == "list"
    assert resolved.index == 1
    assert resolved.text == QUESTIONS["what"]["options"][0]


def test_resolve_answer_list_out_of_range() -> None:
    with pytest.raises(ValueError):
        resolve_answer("what", ListAnswerInput(index=21))


def test_resolve_answer_free_text() -> None:
    resolved = resolve_answer("who", FreeTextAnswerInput(text="  Un dragon curieux  "))
    assert resolved.source == "free_text"
    assert resolved.text == "Un dragon curieux"
    assert resolved.index is None


def test_resolve_answer_free_text_rejects_blank() -> None:
    with pytest.raises(ValueError):
        resolve_answer("who", FreeTextAnswerInput(text="   "))


def test_resolve_answer_random_picks_from_options(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.script_builder.draw_random_index", lambda n: 3)
    resolved = resolve_answer("where", RandomAnswerInput())
    assert resolved.source == "random"
    assert resolved.index == 3
    assert resolved.text == QUESTIONS["where"]["options"][2]


def test_resolve_global_random_covers_all_questions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.script_builder.draw_random_index", lambda n: 1)
    answers = resolve_global_random()
    assert set(answers.keys()) == set(QUESTION_ORDER)
    for key in QUESTION_ORDER:
        assert answers[key].text == QUESTIONS[key]["options"][0]


def test_build_script_orders_by_question_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.script_builder.draw_random_index", lambda n: 1)
    answers = resolve_global_random()
    script = build_script(answers)
    expected = ", ".join(
        OPTION_TRANSLATIONS[key][QUESTIONS[key]["options"][0]] for key in QUESTION_ORDER
    )
    assert script == expected


def test_build_script_translates_to_english() -> None:
    answers = {
        "what": resolve_answer("what", ListAnswerInput(index=2)),  # Photoréaliste
        "who": resolve_answer("who", ListAnswerInput(index=11)),  # Guerrier
        "where": resolve_answer("where", ListAnswerInput(index=3)),  # Désert
        "when": resolve_answer("when", ListAnswerInput(index=17)),  # Préhistoire
        "how": resolve_answer("how", ListAnswerInput(index=1)),  # Plan large
    }
    script = build_script(answers)
    assert script == "photorealistic, a warrior, a desert, prehistoric times, wide shot"


def test_build_script_translates_free_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.script_builder.translate_to_english",
        lambda text: text.replace("dragon curieux", "curious dragon"),
    )
    answers: dict[str, ResolvedAnswer] = {
        "what": resolve_answer("what", ListAnswerInput(index=1)),
        "who": resolve_answer("who", FreeTextAnswerInput(text="Un dragon curieux")),
        "where": resolve_answer("where", ListAnswerInput(index=1)),
        "when": resolve_answer("when", ListAnswerInput(index=1)),
        "how": resolve_answer("how", ListAnswerInput(index=1)),
    }
    script = build_script(answers)
    assert "Un curious dragon" in script
    assert "Un dragon curieux" not in script


def test_build_script_falls_back_to_original_when_translation_model_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.translation._get_translation", lambda: None)
    answers: dict[str, ResolvedAnswer] = {
        "what": resolve_answer("what", ListAnswerInput(index=1)),
        "who": resolve_answer("who", FreeTextAnswerInput(text="Un dragon curieux")),
        "where": resolve_answer("where", ListAnswerInput(index=1)),
        "when": resolve_answer("when", ListAnswerInput(index=1)),
        "how": resolve_answer("how", ListAnswerInput(index=1)),
    }
    script = build_script(answers)
    assert "Un dragon curieux" in script


def test_build_script_aerial_view_with_subject_becomes_top_down() -> None:
    answers = {
        "what": resolve_answer("what", ListAnswerInput(index=1)),
        "who": resolve_answer("who", ListAnswerInput(index=11)),  # Guerrier (un sujet)
        "where": resolve_answer("where", ListAnswerInput(index=3)),
        "when": resolve_answer("when", ListAnswerInput(index=17)),
        "how": resolve_answer("how", ListAnswerInput(index=3)),  # Vue aérienne
    }
    script = build_script(answers)
    assert "top-down view" in script
    assert "aerial view" not in script


def test_build_script_aerial_view_without_subject_stays_aerial() -> None:
    answers = {
        "what": resolve_answer("what", ListAnswerInput(index=1)),
        "who": resolve_answer("who", ListAnswerInput(index=20)),  # Aucun sujet (paysage pur)
        "where": resolve_answer("where", ListAnswerInput(index=3)),
        "when": resolve_answer("when", ListAnswerInput(index=17)),
        "how": resolve_answer("how", ListAnswerInput(index=3)),  # Vue aérienne
    }
    script = build_script(answers)
    assert "aerial view" in script
    assert "top-down view" not in script
