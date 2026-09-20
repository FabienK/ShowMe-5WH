import { QuestionCard } from "../components/QuestionCard";
import { PromptPreview } from "../components/PromptPreview";
import { Loader } from "../components/Loader";
import { ActivityRing } from "../components/ActivityRing";
import { ArrowLeftIcon } from "../components/icons";
import type { AnswerInput, QuestionDefinition, QuestionKey } from "../types";

interface QuestionPageProps {
  questions: QuestionDefinition[];
  currentQuestionIndex: number;
  answers: Partial<Record<QuestionKey, AnswerInput>>;
  loading: boolean;
  onAnswer: (input: AnswerInput) => void;
  onBack: () => void;
}

export function QuestionPage({
  questions,
  currentQuestionIndex,
  answers,
  loading,
  onAnswer,
  onBack,
}: QuestionPageProps) {
  const question = questions[currentQuestionIndex];
  if (!question) return null;

  const isFirstQuestion = currentQuestionIndex === 0;
  // Reflète les réponses déjà données, pas la question affichée : 0 sur la
  // première question (aucune réponse encore), 100 une fois la dernière
  // validée (juste avant de passer à l'aperçu du script).
  const progressPercent = (currentQuestionIndex / questions.length) * 100;
  const remainingQuestions = questions.length - currentQuestionIndex;

  return (
    <div className="question-page">
      <div className="question-page__header">
        <ActivityRing
          ring={{
            label: "Questions left",
            value: progressPercent,
            color: "var(--accent)",
            colorEnd: "var(--accent2)",
            size: 56,
          }}
          strokeWidth={6}
          centerLabel={String(remainingQuestions)}
        />
        <PromptPreview questions={questions} answers={answers} />
      </div>

      {loading ? (
        <Loader label="Assembling the script…" />
      ) : (
        <QuestionCard question={question} onAnswer={onAnswer} />
      )}

      {!isFirstQuestion && (
        <div className="question-page__nav">
          <button
            type="button"
            className="icon-button question-page__back"
            onClick={onBack}
            disabled={loading}
            aria-label="Previous question"
            title="Previous question"
          >
            <ArrowLeftIcon />
          </button>
        </div>
      )}
    </div>
  );
}
