from fastapi.testclient import TestClient

from app.data.questions import QUESTION_ORDER


def test_get_questions_returns_five_questions_of_twenty_options(client: TestClient) -> None:
    response = client.get("/api/questions")
    assert response.status_code == 200

    data = response.json()
    assert [q["key"] for q in data["questions"]] == QUESTION_ORDER
    for question in data["questions"]:
        assert len(question["options"]) == 20


def test_post_script_free_prompt(client: TestClient) -> None:
    response = client.post("/api/script", json={"mode": "free_prompt", "prompt": "un chat en armure"})
    assert response.status_code == 200
    data = response.json()
    assert data["script"] == "un chat en armure"
    assert data["answers"] is None
    assert data["style"] is None


def test_post_script_global_random(client: TestClient) -> None:
    response = client.post("/api/script", json={"mode": "global_random"})
    assert response.status_code == 200
    data = response.json()
    assert set(data["answers"].keys()) == set(QUESTION_ORDER)
    assert data["script"].count(",") == 4
    assert data["style"] == data["answers"]["what"]["text"]


def test_post_script_per_question(client: TestClient) -> None:
    response = client.post(
        "/api/script",
        json={
            "mode": "per_question",
            "answers": {
                "what": {"source": "list", "index": 3},
                "who": {"source": "free_text", "text": "Un vieux marin"},
                "where": {"source": "random"},
                "when": {"source": "list", "index": 6},
                "how": {"source": "list", "index": 1},
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answers"]["what"]["text"] == "Anime"
    assert data["answers"]["who"]["text"] == "Un vieux marin"
    assert data["style"] == "Anime"


def test_post_script_per_question_missing_answer_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/script",
        json={"mode": "per_question", "answers": {"what": {"source": "list", "index": 1}}},
    )
    assert response.status_code == 422
