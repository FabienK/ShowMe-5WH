import { useCallback, useState } from "react";
import * as api from "../api/client";
import type { AnswerInput, ApiError, QuestionDefinition, QuestionKey, ScriptResponse } from "../types";

// Portion pure "questionnaire" du flux 5 questions (What/Who/Where/When/How) :
// accumule les réponses et résout le script final via /api/script en mode
// per_question. Ne gère rien après ça (pas de génération/résultats) —
// réutilisé à la fois par le flux "Générateur" (useGenerationFlow) et par le
// mode "Assistant" du composer de batch.
export function useQuestionFlow(questions: QuestionDefinition[]) {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Partial<Record<QuestionKey, AnswerInput>>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const submitAnswer = useCallback(
    async (input: AnswerInput): Promise<ScriptResponse | null> => {
      const question = questions[currentQuestionIndex];
      if (!question) return null;

      const nextAnswers = { ...answers, [question.key]: input };
      setAnswers(nextAnswers);

      if (currentQuestionIndex < questions.length - 1) {
        setCurrentQuestionIndex((index) => index + 1);
        return null;
      }

      setLoading(true);
      setError(null);
      try {
        const result = await api.postScript({
          mode: "per_question",
          answers: nextAnswers as Record<QuestionKey, AnswerInput>,
        });
        return result;
      } catch (err) {
        setError(err as ApiError);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [answers, currentQuestionIndex, questions],
  );

  const goToPreviousQuestion = useCallback(() => {
    setCurrentQuestionIndex((index) => Math.max(0, index - 1));
  }, []);

  const reset = useCallback(() => {
    setAnswers({});
    setCurrentQuestionIndex(0);
    setError(null);
  }, []);

  return {
    currentQuestionIndex,
    answers,
    setAnswers,
    loading,
    error,
    submitAnswer,
    goToPreviousQuestion,
    reset,
  };
}
