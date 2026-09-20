import { useCallback, useEffect, useMemo, useState } from "react";
import * as api from "../api/client";
import { buildGenerationQueue } from "../utils/estimate";
import { toAnswerInput } from "../utils/answers";
import { useQuestionFlow } from "./useQuestionFlow";
import type {
  AnswerInput,
  ApiError,
  GenerateResponse,
  ModelOption,
  OpenAIState,
  QuestionDefinition,
  QuestionKey,
  ResolvedAnswer,
  ScriptResponse,
} from "../types";

export type Step = "home" | "question" | "preview" | "result";

export function useGenerationFlow() {
  const [questions, setQuestions] = useState<QuestionDefinition[]>([]);
  const [questionsLoading, setQuestionsLoading] = useState(true);
  const [comfyReachable, setComfyReachable] = useState<boolean | null>(null);

  const [step, setStep] = useState<Step>("home");
  const questionFlow = useQuestionFlow(questions);

  const [scriptResult, setScriptResult] = useState<ScriptResponse | null>(null);
  const [freePromptText, setFreePromptText] = useState("");
  const [results, setResults] = useState<GenerateResponse[]>([]);
  const [pendingModels, setPendingModels] = useState<ModelOption[]>([]);
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);
  const [referenceImage, setReferenceImage] = useState<string | null>(null);
  const [denoiseStrength, setDenoiseStrength] = useState(0.6);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [openaiBalance, setOpenaiBalance] = useState<OpenAIState | null>(null);

  const refreshOpenAIBalance = useCallback(() => {
    api.getOpenAIBalance().then(setOpenaiBalance).catch(() => {});
  }, []);

  // Flux schnell (moteur MLX) et OpenAI ne supportent pas l'img2img en V1 :
  // on les retire tant qu'une image de référence est active. Flux Kontext, à
  // l'inverse, exige une image de référence (édition d'image par
  // instruction) : on ne le propose que lorsqu'une image est attachée.
  const availableModels = useMemo(() => {
    if (!scriptResult) return [];
    return referenceImage
      ? scriptResult.models.filter(
          (model) => model.engine_type !== "flux_schnell" && model.engine_type !== "openai",
        )
      : scriptResult.models.filter((model) => model.engine_type !== "flux_kontext");
  }, [scriptResult, referenceImage]);

  useEffect(() => {
    // Un seul modèle disponible pour ce style -> auto-sélection (CAS 1.2).
    // Plusieurs modèles -> l'utilisateur choisit un sous-ensemble (CAS 1.1).
    setSelectedModelIds(availableModels.length === 1 ? [availableModels[0].id] : []);
  }, [availableModels]);

  const toggleModelSelection = useCallback((id: string) => {
    setSelectedModelIds((prev) =>
      prev.includes(id) ? prev.filter((existing) => existing !== id) : [...prev, id],
    );
  }, []);

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

    refreshOpenAIBalance();
  }, [refreshOpenAIBalance]);

  const chooseFreePrompt = useCallback(async (text: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.postScript({ mode: "free_prompt", prompt: text });
      setFreePromptText(text);
      setScriptResult(result);
      setStep("preview");
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setLoading(false);
    }
  }, []);

  const chooseImageReference = useCallback(
    async (imageDataUrl: string, guidanceText: string, denoise: number) => {
      setLoading(true);
      setError(null);
      try {
        const trimmed = guidanceText.trim();
        const result = await api.postScript({ mode: "free_prompt", prompt: trimmed });
        setFreePromptText(trimmed);
        setReferenceImage(imageDataUrl);
        setDenoiseStrength(denoise);
        setScriptResult(result);
        setStep("preview");
      } catch (err) {
        setError(err as ApiError);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

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
    questionFlow.reset();
    setError(null);
    setStep("question");
  }, [questionFlow]);

  const submitAnswerForCurrentQuestion = useCallback(
    async (input: AnswerInput) => {
      const result = await questionFlow.submitAnswer(input);
      if (result) {
        setScriptResult(result);
        setStep("preview");
      }
    },
    [questionFlow],
  );

  const goToPreviousQuestion = questionFlow.goToPreviousQuestion;

  const generateForModels = useCallback(
    async (models: ModelOption[]) => {
      if (!scriptResult || models.length === 0) return;
      setError(null);
      // File ordonnée du plus rapide au plus lent, un modèle répété selon
      // son nombre d'images — affichée telle quelle pendant toute la
      // génération pour que l'UI connaisse la file complète et la
      // progression (résultats déjà arrivés vs jobs restants).
      const jobs = buildGenerationQueue(models);
      setPendingModels(jobs);
      setResults([]);

      setLoading(true);
      try {
        for (const model of jobs) {
          const generated = await api.postGenerate({
            script: scriptResult.script,
            style: scriptResult.style,
            model_id: model.id,
            reference_image: referenceImage ?? undefined,
            denoise_strength: referenceImage ? denoiseStrength : undefined,
          });
          // Ajouté dès que reçu : l'image la plus rapide s'affiche sans
          // attendre les suivantes.
          setResults((prev) => [...prev, generated]);
          if (model.engine_type === "openai") {
            // Reflète la vérité persistée côté backend plutôt que de
            // décrémenter optimistiquement côté client (voir
            // openai_state_store.py — le solde n'est décrémenté que sur
            // succès confirmé).
            refreshOpenAIBalance();
          }
        }
      } catch (err) {
        setError(err as ApiError);
      } finally {
        setLoading(false);
        setPendingModels([]);
      }
    },
    [scriptResult, referenceImage, denoiseStrength, refreshOpenAIBalance],
  );

  const selectedModels = useCallback(
    () => availableModels.filter((model) => selectedModelIds.includes(model.id)),
    [availableModels, selectedModelIds],
  );

  const confirmAndGenerate = useCallback(async () => {
    const models = selectedModels();
    if (models.length === 0) return;
    setStep("result");
    await generateForModels(models);
  }, [selectedModels, generateForModels]);

  const regenerate = useCallback(async () => {
    const models = selectedModels();
    if (models.length === 0) return;
    await generateForModels(models);
  }, [selectedModels, generateForModels]);

  const backToPreview = useCallback(() => {
    if (!scriptResult) return;
    setError(null);
    setStep("preview");
  }, [scriptResult]);

  const updateAnswerField = useCallback(
    async (key: QuestionKey, input: AnswerInput) => {
      if (!scriptResult?.answers) return;

      const nextAnswers = Object.fromEntries(
        (Object.entries(scriptResult.answers) as [QuestionKey, ResolvedAnswer][]).map(
          ([k, resolved]) => [k, k === key ? input : toAnswerInput(resolved)],
        ),
      ) as Record<QuestionKey, AnswerInput>;

      setLoading(true);
      setError(null);
      try {
        const result = await api.postScript({ mode: "per_question", answers: nextAnswers });
        setScriptResult(result);
        questionFlow.setAnswers(nextAnswers);
      } catch (err) {
        setError(err as ApiError);
      } finally {
        setLoading(false);
      }
    },
    [scriptResult, questionFlow],
  );

  const restart = useCallback(() => {
    setStep("home");
    questionFlow.reset();
    setScriptResult(null);
    setResults([]);
    setPendingModels([]);
    setSelectedModelIds([]);
    setError(null);
    setReferenceImage(null);
    setDenoiseStrength(0.6);
  }, [questionFlow]);

  return {
    questions,
    questionsLoading,
    comfyReachable,
    step,
    currentQuestionIndex: questionFlow.currentQuestionIndex,
    answers: questionFlow.answers,
    scriptResult,
    freePromptText,
    results,
    pendingModels,
    selectedModelIds,
    toggleModelSelection,
    referenceImage,
    denoiseStrength,
    setDenoiseStrength,
    availableModels,
    openaiBalance,
    refreshOpenAIBalance,
    loading: loading || questionFlow.loading,
    error: error ?? questionFlow.error,
    chooseFreePrompt,
    chooseGlobalRandom,
    chooseAnswerQuestionByQuestion,
    chooseImageReference,
    submitAnswerForCurrentQuestion,
    goToPreviousQuestion,
    confirmAndGenerate,
    regenerate,
    backToPreview,
    updateAnswerField,
    restart,
  };
}
