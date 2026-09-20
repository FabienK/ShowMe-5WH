import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "../api/client";
import { buildGenerationQueue } from "../utils/estimate";
import { toAnswerInput } from "../utils/answers";
import type {
  AnswerInput,
  ApiError,
  GenerateRequest,
  ModelOption,
  QuestionDefinition,
  QuestionKey,
  ResolvedAnswer,
} from "../types";

export type BatchItemInputMode = "free_text" | "assistant";

export interface BatchDraftItem {
  id: string;
  inputMode: BatchItemInputMode;
  script: string;
  style: string | null;
  models: ModelOption[];
  modelIds: string[];
  referenceImage: string | null;
  denoiseStrength: number;
  // État du mini-questionnaire "Assistant", ignoré en mode "free_text".
  assistantAnswers: Partial<Record<QuestionKey, AnswerInput>>;
  assistantQuestionIndex: number;
  assistantComplete: boolean;
  // Réponses résolues par le backend une fois le questionnaire terminé —
  // alimente le tableau d'édition (AnswerFieldEditor), null tant qu'il n'y
  // a pas encore de script résolu via le mode "per_question".
  resolvedAnswers: Record<QuestionKey, ResolvedAnswer> | null;
}

// GPT Image 2 est exclu du composeur de batch en V1 : un batch tourne sans
// surveillance, en série, potentiellement plusieurs items × plusieurs images
// — l'exposer ici créerait une dépense réelle sans confirmation par item.
// Il reste sélectionnable dans le flux "Générateur" (une génération à la
// fois, décision explicite à chaque clic).
function excludeOpenAI(models: ModelOption[]): ModelOption[] {
  return models.filter((model) => model.engine_type !== "openai");
}

function makeId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `item-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function emptyItem(): BatchDraftItem {
  return {
    id: makeId(),
    inputMode: "free_text",
    script: "",
    style: null,
    models: [],
    modelIds: [],
    referenceImage: null,
    denoiseStrength: 0.6,
    assistantAnswers: {},
    assistantQuestionIndex: 0,
    assistantComplete: false,
    resolvedAnswers: null,
  };
}

export function useBatchComposer() {
  const [items, setItems] = useState<BatchDraftItem[]>([emptyItem()]);
  const [questions, setQuestions] = useState<QuestionDefinition[]>([]);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [removingIds, setRemovingIds] = useState<Set<string>>(new Set());
  const removeTimeouts = useRef<Record<string, number>>({});

  // Durée alignée sur la plus longue transition CSS de
  // .batch-composer-page__item (transform, 220ms) pour laisser l'animation
  // de sortie finir avant le retrait réel de l'item.
  const ITEM_EXIT_MS = 220;

  useEffect(() => {
    return () => {
      Object.values(removeTimeouts.current).forEach((timeoutId) => window.clearTimeout(timeoutId));
    };
  }, []);

  useEffect(() => {
    api
      .getQuestions()
      .then(setQuestions)
      .catch(() => {
        // Le mode "Assistant" reste simplement indisponible si /api/questions
        // échoue — le mode texte libre continue de fonctionner.
      });
  }, []);

  const addItem = useCallback(() => {
    setItems((prev) => [...prev, emptyItem()]);
  }, []);

  const removeItem = useCallback(
    (id: string) => {
      if (removingIds.has(id)) return;
      const remainingCount = items.length - removingIds.size;
      if (remainingCount <= 1) return;

      setRemovingIds((prev) => new Set(prev).add(id));
      removeTimeouts.current[id] = window.setTimeout(() => {
        setItems((prev) => prev.filter((item) => item.id !== id));
        setRemovingIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
        delete removeTimeouts.current[id];
      }, ITEM_EXIT_MS);
    },
    [items, removingIds],
  );

  const updateItem = useCallback((id: string, patch: Partial<BatchDraftItem>) => {
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }, []);

  const setItemMode = useCallback(
    (id: string, mode: BatchItemInputMode) => {
      updateItem(id, { inputMode: mode });
    },
    [updateItem],
  );

  // Compteur par item : ignore une réponse arrivée après une requête plus
  // récente pour le même item (ex: frappe rapide déclenchant plusieurs
  // appels en parallèle) — évite qu'une réponse lente écrase le résultat
  // d'une requête plus fraîche déjà arrivée.
  const requestSeq = useRef<Record<string, number>>({});

  const resolveModelsForItem = useCallback(async (id: string, script: string) => {
    updateItem(id, { script });
    const seq = (requestSeq.current[id] ?? 0) + 1;
    requestSeq.current[id] = seq;

    if (!script.trim()) {
      updateItem(id, { models: [], modelIds: [], style: null });
      return;
    }
    try {
      const result = await api.postScript({ mode: "free_prompt", prompt: script });
      if (requestSeq.current[id] !== seq) return;
      const models = excludeOpenAI(result.models);
      updateItem(id, {
        models,
        style: result.style,
        modelIds: models.length === 1 ? [models[0].id] : [],
      });
    } catch {
      // La résolution du style/des modèles est un confort d'UI — en cas
      // d'échec (ex: backend injoignable), l'utilisateur garde la main pour
      // réessayer, le batch reste composable sans modèle résolu pour cet item.
    }
  }, [updateItem]);

  const submitAssistantAnswer = useCallback(
    async (id: string, input: AnswerInput) => {
      const item = items.find((existing) => existing.id === id);
      if (!item) return;
      const question = questions[item.assistantQuestionIndex];
      if (!question) return;

      const nextAnswers = { ...item.assistantAnswers, [question.key]: input };

      if (item.assistantQuestionIndex < questions.length - 1) {
        updateItem(id, {
          assistantAnswers: nextAnswers,
          assistantQuestionIndex: item.assistantQuestionIndex + 1,
        });
        return;
      }

      try {
        const result = await api.postScript({
          mode: "per_question",
          answers: nextAnswers as Record<QuestionKey, AnswerInput>,
        });
        const models = excludeOpenAI(result.models);
        updateItem(id, {
          assistantAnswers: nextAnswers,
          assistantComplete: true,
          script: result.script,
          style: result.style,
          models,
          modelIds: models.length === 1 ? [models[0].id] : [],
          resolvedAnswers: result.answers,
        });
      } catch (err) {
        setError(err as ApiError);
      }
    },
    [items, questions, updateItem],
  );

  // Édition d'une seule réponse depuis le tableau final (prompt libre /
  // liste / aléatoire par question) — renvoie les 5 réponses à /api/script
  // en ne changeant que celle visée, comme le fait ScriptPreviewPage pour
  // le flux "Générateur".
  const updateAssistantAnswerField = useCallback(
    async (id: string, key: QuestionKey, input: AnswerInput) => {
      const item = items.find((existing) => existing.id === id);
      if (!item?.resolvedAnswers) return;

      const nextAnswers = Object.fromEntries(
        (Object.entries(item.resolvedAnswers) as [QuestionKey, ResolvedAnswer][]).map(
          ([k, resolved]) => [k, k === key ? input : toAnswerInput(resolved)],
        ),
      ) as Record<QuestionKey, AnswerInput>;

      try {
        const result = await api.postScript({ mode: "per_question", answers: nextAnswers });
        const models = excludeOpenAI(result.models);
        updateItem(id, {
          assistantAnswers: nextAnswers,
          script: result.script,
          style: result.style,
          models,
          modelIds: models.length === 1 ? [models[0].id] : [],
          resolvedAnswers: result.answers,
        });
      } catch (err) {
        setError(err as ApiError);
      }
    },
    [items, updateItem],
  );

  const goToPreviousAssistantQuestion = useCallback(
    (id: string) => {
      const item = items.find((existing) => existing.id === id);
      if (!item) return;
      updateItem(id, { assistantQuestionIndex: Math.max(0, item.assistantQuestionIndex - 1) });
    },
    [items, updateItem],
  );

  const resetAssistant = useCallback(
    (id: string) => {
      updateItem(id, {
        assistantAnswers: {},
        assistantQuestionIndex: 0,
        assistantComplete: false,
        script: "",
        style: null,
        models: [],
        modelIds: [],
        resolvedAnswers: null,
      });
    },
    [updateItem],
  );

  const toggleItemModel = useCallback((id: string, modelId: string) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === id
          ? {
              ...item,
              modelIds: item.modelIds.includes(modelId)
                ? item.modelIds.filter((existing) => existing !== modelId)
                : [...item.modelIds, modelId],
            }
          : item,
      ),
    );
  }, []);

  const canLaunch =
    items.every((item) => item.script.trim() && item.modelIds.length > 0) && items.length > 0;

  const launchBatch = useCallback(async (): Promise<string | null> => {
    if (!canLaunch) return null;
    setLaunching(true);
    setError(null);
    try {
      const requests: GenerateRequest[] = items.flatMap((item) => {
        const selectedModels = item.models.filter((model) => item.modelIds.includes(model.id));
        return buildGenerationQueue(selectedModels).map((model) => ({
          script: item.script,
          style: item.style,
          model_id: model.id,
          reference_image: item.referenceImage,
          denoise_strength: item.referenceImage ? item.denoiseStrength : undefined,
        }));
      });
      const { batch_id } = await api.postBatch(requests);
      Object.values(removeTimeouts.current).forEach((timeoutId) => window.clearTimeout(timeoutId));
      removeTimeouts.current = {};
      setRemovingIds(new Set());
      setItems([emptyItem()]);
      return batch_id;
    } catch (err) {
      setError(err as ApiError);
      return null;
    } finally {
      setLaunching(false);
    }
  }, [items, canLaunch]);

  return {
    items,
    questions,
    addItem,
    removeItem,
    removingIds,
    updateItem,
    setItemMode,
    resolveModelsForItem,
    submitAssistantAnswer,
    updateAssistantAnswerField,
    goToPreviousAssistantQuestion,
    resetAssistant,
    toggleItemModel,
    canLaunch,
    launching,
    error,
    launchBatch,
  };
}
