from fastapi import APIRouter

from app.data.questions import QUESTION_ORDER, QUESTIONS
from app.models.schemas import QuestionDefinition, QuestionsResponse

router = APIRouter(tags=["questions"])


@router.get("/questions", response_model=QuestionsResponse)
def get_questions() -> QuestionsResponse:
    questions = [
        QuestionDefinition(key=key, label=QUESTIONS[key]["label"], options=QUESTIONS[key]["options"])
        for key in QUESTION_ORDER
    ]
    return QuestionsResponse(questions=questions)
