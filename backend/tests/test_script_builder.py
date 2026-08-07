import pytest

from app.data.questions import QUESTION_ORDER, QUESTIONS
from app.models.schemas import FreeTextAnswerInput, ListAnswerInput, RandomAnswerInput
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
    expected = ", ".join(QUESTIONS[key]["options"][0] for key in QUESTION_ORDER)
    assert script == expected
