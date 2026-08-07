import { QuestionCard } from "../components/QuestionCard";
import { Loader } from "../components/Loader";
import type { AnswerInput, QuestionDefinition } from "../types";

interface QuestionPageProps {
  questions: QuestionDefinition[];
  currentQuestionIndex: number;
  loading: boolean;
  onAnswer: (input: AnswerInput) => void;
  onBack: () => void;
}

export function QuestionPage({
  questions,
  currentQuestionIndex,
  loading,
  onAnswer,
  onBack,
}: QuestionPageProps) {
  const question = questions[currentQuestionIndex];
  if (!question) return null;

  return (
    <div className="question-page">
      <p className="question-page__progress">
        Question {currentQuestionIndex + 1} / {questions.length}
      </p>

      {loading ? (
        <Loader label="Assemblage du script…" />
      ) : (
        <QuestionCard question={question} onAnswer={onAnswer} />
      )}

      <button
        type="button"
        className="question-page__back"
        onClick={onBack}
        disabled={currentQuestionIndex === 0 || loading}
      >
        ← Question précédente
      </button>
    </div>
  );
}
