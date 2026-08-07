import { useCallback, useEffect, useState } from "react";
import * as api from "../api/client";
import type {
  AnswerInput,
  ApiError,
  GenerateResponse,
  QuestionDefinition,
  QuestionKey,
  ScriptResponse,
} from "../types";

export type Step = "home" | "question" | "preview" | "result";

export function useGenerationFlow() {
  const [questions, setQuestions] = useState<QuestionDefinition[]>([]);
  const [questionsLoading, setQuestionsLoading] = useState(true);
  const [comfyReachable, setComfyReachable] = useState<boolean | null>(null);

  const [step, setStep] = useState<Step>("home");
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Partial<Record<QuestionKey, AnswerInput>>>({});

  const [scriptResult, setScriptResult] = useState<ScriptResponse | null>(null);
  const [generateResult, setGenerateResult] = useState<GenerateResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    api
      .getQuestions()
      .then(setQuestions)
      .catch((err: ApiError) => setError(err))
      .finally(() => setQuestionsLoading(false));

    api
      .getComfyUIStatus()
      .then(setComfyReachable)
      .catch(() => setComfyReachable(false));
  }, []);

  const chooseFreePrompt = useCallback(async (text: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.postScript({ mode: "free_prompt", prompt: text });
      setScriptResult(result);
      setStep("preview");
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setLoading(false);
    }
  }, []);

  const chooseGlobalRandom = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.postScript({ mode: "global_random" });
      setScriptResult(result);
      setStep("preview");
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setLoading(false);
    }
  }, []);

  const chooseAnswerQuestionByQuestion = useCallback(() => {
    setAnswers({});
    setCurrentQuestionIndex(0);
    setError(null);
    setStep("question");
  }, []);

  const submitAnswerForCurrentQuestion = useCallback(
    async (input: AnswerInput) => {
      const question = questions[currentQuestionIndex];
      if (!question) return;

      const nextAnswers = { ...answers, [question.key]: input };
      setAnswers(nextAnswers);

      if (currentQuestionIndex < questions.length - 1) {
        setCurrentQuestionIndex((index) => index + 1);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const result = await api.postScript({
          mode: "per_question",
          answers: nextAnswers as Record<QuestionKey, AnswerInput>,
        });
        setScriptResult(result);
        setStep("preview");
      } catch (err) {
        setError(err as ApiError);
      } finally {
        setLoading(false);
      }
    },
    [answers, currentQuestionIndex, questions],
  );

  const goToPreviousQuestion = useCallback(() => {
    setCurrentQuestionIndex((index) => Math.max(0, index - 1));
  }, []);

  const confirmAndGenerate = useCallback(async () => {
    if (!scriptResult) return;
    setLoading(true);
    setError(null);
    setStep("result");
    try {
      const result = await api.postGenerate({
        script: scriptResult.script,
        style: scriptResult.style,
      });
      setGenerateResult(result);
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setLoading(false);
    }
  }, [scriptResult]);

  const regenerate = useCallback(async () => {
    if (!scriptResult) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.postGenerate({
        script: scriptResult.script,
        style: scriptResult.style,
      });
      setGenerateResult(result);
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setLoading(false);
    }
  }, [scriptResult]);

  const restart = useCallback(() => {
    setStep("home");
    setAnswers({});
    setCurrentQuestionIndex(0);
    setScriptResult(null);
    setGenerateResult(null);
    setError(null);
  }, []);

  return {
    questions,
    questionsLoading,
    comfyReachable,
    step,
    currentQuestionIndex,
    answers,
    scriptResult,
    generateResult,
    loading,
    error,
    chooseFreePrompt,
    chooseGlobalRandom,
    chooseAnswerQuestionByQuestion,
    submitAnswerForCurrentQuestion,
    goToPreviousQuestion,
    confirmAndGenerate,
    regenerate,
    restart,
  };
}
