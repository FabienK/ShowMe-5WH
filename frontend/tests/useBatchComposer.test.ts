import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../src/api/client";
import { useBatchComposer } from "../src/state/useBatchComposer";
import type { ModelOption, QuestionDefinition, QuestionKey, ResolvedAnswer } from "../src/types";

vi.mock("../src/api/client");

const mockedApi = vi.mocked(api);

const QUESTIONS: QuestionDefinition[] = [
  { key: "what", label: "What", options: ["Bande dessinée", "Photoréaliste"] },
  { key: "who", label: "Who", options: ["Personnage humain seul", "Duo de personnages"] },
  { key: "where", label: "Where", options: ["Forêt", "Ville futuriste"] },
  { key: "when", label: "When", options: ["Aube", "Matin"] },
  { key: "how", label: "How", options: ["Plan large", "Gros plan"] },
];

const MODELS: ModelOption[] = [
  {
    id: "model-1",
    label: "Modèle 1",
    version: "v1",
    estimated_time: "~20s",
    description: "Modèle de test",
    engine_type: "sd_checkpoint",
    checkpoint: "checkpoint.safetensors",
    lora: null,
    sampler: "euler",
    scheduler: "normal",
    steps: 20,
    cfg: 7,
    width: 512,
    height: 512,
    negative_prompt: "",
  },
];

const MULTI_MODELS: ModelOption[] = [
  {
    id: "model-sd",
    label: "Modèle SD",
    version: "v1",
    estimated_time: "~20s",
    description: "Modèle de test (2 images)",
    engine_type: "sd_checkpoint",
    checkpoint: "checkpoint.safetensors",
    lora: null,
    sampler: "euler",
    scheduler: "normal",
    steps: 20,
    cfg: 7,
    width: 512,
    height: 512,
    negative_prompt: "",
  },
  {
    id: "model-flux",
    label: "Flux dev",
    version: "dev",
    estimated_time: "~12 min",
    description: "Modèle lent (1 image)",
    engine_type: "flux",
    checkpoint: null,
    lora: null,
    sampler: "euler",
    scheduler: "simple",
    steps: 20,
    cfg: 1,
    width: 1024,
    height: 1024,
    negative_prompt: "",
  },
];

const MODELS_WITH_OPENAI: ModelOption[] = [
  ...MODELS,
  {
    id: "openai-1",
    label: "GPT Image 2",
    version: "cloud",
    estimated_time: "~20s",
    description: "Génération via l'API OpenAI, payante.",
    engine_type: "openai",
    checkpoint: null,
    lora: null,
    sampler: "euler",
    scheduler: "normal",
    steps: 0,
    cfg: 0,
    width: 1024,
    height: 1024,
    negative_prompt: "",
  },
];

const RESOLVED_ANSWERS: Record<QuestionKey, ResolvedAnswer> = {
  what: { key: "what", label: "What", source: "list", index: 1, text: "Bande dessinée" },
  who: { key: "who", label: "Who", source: "list", index: 1, text: "Personnage humain seul" },
  where: { key: "where", label: "Where", source: "list", index: 1, text: "Forêt" },
  when: { key: "when", label: "When", source: "list", index: 1, text: "Aube" },
  how: { key: "how", label: "How", source: "list", index: 1, text: "Plan large" },
};

beforeEach(() => {
  vi.resetAllMocks();
  mockedApi.getQuestions.mockResolvedValue(QUESTIONS);
});

describe("useBatchComposer", () => {
  it("starts with a single empty item and cannot launch", () => {
    const { result } = renderHook(() => useBatchComposer());
    expect(result.current.items).toHaveLength(1);
    expect(result.current.canLaunch).toBe(false);
  });

  it("adds and removes items, never going below one", async () => {
    const { result } = renderHook(() => useBatchComposer());

    act(() => result.current.addItem());
    expect(result.current.items).toHaveLength(2);

    // Le retrait est différé (~220ms) pour laisser jouer l'animation de
    // sortie : l'item est d'abord marqué "removingIds" puis effectivement
    // filtré de "items" une fois le délai écoulé.
    const [first] = result.current.items;
    act(() => result.current.removeItem(first.id));
    expect(result.current.items).toHaveLength(2);
    expect(result.current.removingIds.has(first.id)).toBe(true);

    await waitFor(() => expect(result.current.items).toHaveLength(1));
    expect(result.current.removingIds.has(first.id)).toBe(false);

    const [onlyItem] = result.current.items;
    act(() => result.current.removeItem(onlyItem.id));
    expect(result.current.items).toHaveLength(1);
    expect(result.current.removingIds.size).toBe(0);
  });

  it("resolves models via postScript and auto-selects a single model", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "free_prompt",
      answers: null,
      script: "un chat en armure",
      style: "Anime",
      models: MODELS,
    });

    const { result } = renderHook(() => useBatchComposer());
    const [item] = result.current.items;

    await act(async () => {
      await result.current.resolveModelsForItem(item.id, "un chat en armure");
    });

    expect(mockedApi.postScript).toHaveBeenCalledWith({
      mode: "free_prompt",
      prompt: "un chat en armure",
    });
    expect(result.current.items[0].models).toEqual(MODELS);
    expect(result.current.items[0].modelIds).toEqual(["model-1"]);
    expect(result.current.canLaunch).toBe(true);
  });

  it("excludes GPT Image 2 from resolved models — not selectable in an overnight batch", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "free_prompt",
      answers: null,
      script: "un chat en armure",
      style: "Anime",
      models: MODELS_WITH_OPENAI,
    });

    const { result } = renderHook(() => useBatchComposer());
    const [item] = result.current.items;

    await act(async () => {
      await result.current.resolveModelsForItem(item.id, "un chat en armure");
    });

    expect(result.current.items[0].models.map((model) => model.engine_type)).not.toContain(
      "openai",
    );
    // Un seul modèle non-OpenAI restant -> auto-sélection, comme avant l'ajout d'OpenAI.
    expect(result.current.items[0].modelIds).toEqual(["model-1"]);
  });

  it("toggleItemModel adds and removes a model id from the selection", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "free_prompt",
      answers: null,
      script: "un chat en armure",
      style: null,
      models: MULTI_MODELS,
    });

    const { result } = renderHook(() => useBatchComposer());
    const [item] = result.current.items;

    await act(async () => {
      await result.current.resolveModelsForItem(item.id, "un chat en armure");
    });

    // Plusieurs modèles candidats -> pas d'auto-sélection.
    expect(result.current.items[0].modelIds).toEqual([]);

    act(() => result.current.toggleItemModel(item.id, "model-sd"));
    expect(result.current.items[0].modelIds).toEqual(["model-sd"]);

    act(() => result.current.toggleItemModel(item.id, "model-flux"));
    expect(result.current.items[0].modelIds).toEqual(["model-sd", "model-flux"]);

    act(() => result.current.toggleItemModel(item.id, "model-sd"));
    expect(result.current.items[0].modelIds).toEqual(["model-flux"]);
  });

  it("launchBatch expands a single selected model into imagesPerModel requests", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "free_prompt",
      answers: null,
      script: "un chat en armure",
      style: null,
      models: MODELS,
    });
    mockedApi.postBatch.mockResolvedValue({ batch_id: "batch-123" });

    const { result } = renderHook(() => useBatchComposer());
    const [item] = result.current.items;

    await act(async () => {
      await result.current.resolveModelsForItem(item.id, "un chat en armure");
    });
    await waitFor(() => expect(result.current.canLaunch).toBe(true));

    let batchId: string | null = null;
    await act(async () => {
      batchId = await result.current.launchBatch();
    });

    expect(batchId).toBe("batch-123");
    // model-1 est un sd_checkpoint -> imagesPerModel = 2 (pas de flux/flux_kontext).
    expect(mockedApi.postBatch).toHaveBeenCalledWith([
      expect.objectContaining({ script: "un chat en armure", model_id: "model-1" }),
      expect.objectContaining({ script: "un chat en armure", model_id: "model-1" }),
    ]);
    expect(result.current.items).toHaveLength(1);
    expect(result.current.items[0].script).toBe("");
  });

  it("launchBatch expands multiple selected models, respecting the flux/flux_kontext exception", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "free_prompt",
      answers: null,
      script: "un chat en armure",
      style: null,
      models: MULTI_MODELS,
    });
    mockedApi.postBatch.mockResolvedValue({ batch_id: "batch-456" });

    const { result } = renderHook(() => useBatchComposer());
    const [item] = result.current.items;

    await act(async () => {
      await result.current.resolveModelsForItem(item.id, "un chat en armure");
    });
    act(() => result.current.toggleItemModel(item.id, "model-sd"));
    act(() => result.current.toggleItemModel(item.id, "model-flux"));
    await waitFor(() => expect(result.current.canLaunch).toBe(true));

    await act(async () => {
      await result.current.launchBatch();
    });

    const requests = mockedApi.postBatch.mock.calls[0][0];
    // model-sd (sd_checkpoint) -> 2 images ; model-flux (flux) -> 1 image.
    expect(requests).toHaveLength(3);
    expect(requests.filter((r) => r.model_id === "model-sd")).toHaveLength(2);
    expect(requests.filter((r) => r.model_id === "model-flux")).toHaveLength(1);
  });

  it("surfaces an ApiError and keeps the draft when the batch creation fails", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "free_prompt",
      answers: null,
      script: "un chat en armure",
      style: null,
      models: MODELS,
    });
    mockedApi.postBatch.mockRejectedValue({
      status: 503,
      errorType: "comfyui_unreachable",
      detail: "Impossible de contacter ComfyUI",
    });

    const { result } = renderHook(() => useBatchComposer());
    const [item] = result.current.items;

    await act(async () => {
      await result.current.resolveModelsForItem(item.id, "un chat en armure");
    });
    await waitFor(() => expect(result.current.canLaunch).toBe(true));

    await act(async () => {
      await result.current.launchBatch();
    });

    expect(result.current.error?.errorType).toBe("comfyui_unreachable");
    expect(result.current.items).toHaveLength(1);
    expect(result.current.items[0].script).toBe("un chat en armure");
  });

  it("assistant mode walks through the 5 questions and resolves script/models", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "per_question",
      answers: RESOLVED_ANSWERS,
      script: "Bande dessinée, Personnage humain seul, Forêt, Aube, Plan large",
      style: "Bande dessinée",
      models: MODELS,
    });

    const { result } = renderHook(() => useBatchComposer());
    await waitFor(() => expect(result.current.questions).toEqual(QUESTIONS));

    const [item] = result.current.items;
    act(() => result.current.setItemMode(item.id, "assistant"));
    expect(result.current.items[0].inputMode).toBe("assistant");

    for (let i = 0; i < 5; i++) {
      // Le live preview doit refléter les réponses déjà données avant l'envoi final.
      expect(result.current.items[0].assistantQuestionIndex).toBe(i);
      await act(async () => {
        await result.current.submitAssistantAnswer(item.id, { source: "list", index: 1 });
      });
    }

    expect(mockedApi.postScript).toHaveBeenCalledWith({
      mode: "per_question",
      answers: {
        what: { source: "list", index: 1 },
        who: { source: "list", index: 1 },
        where: { source: "list", index: 1 },
        when: { source: "list", index: 1 },
        how: { source: "list", index: 1 },
      },
    });
    expect(result.current.items[0].assistantComplete).toBe(true);
    expect(result.current.items[0].script).toBe(
      "Bande dessinée, Personnage humain seul, Forêt, Aube, Plan large",
    );
    expect(result.current.items[0].modelIds).toEqual(["model-1"]);
    expect(result.current.items[0].resolvedAnswers).toEqual(RESOLVED_ANSWERS);
    expect(result.current.canLaunch).toBe(true);
  });

  it("updateAssistantAnswerField re-resolves the script, keeping the other answers", async () => {
    mockedApi.postScript.mockResolvedValueOnce({
      mode: "per_question",
      answers: RESOLVED_ANSWERS,
      script: "Bande dessinée, Personnage humain seul, Forêt, Aube, Plan large",
      style: "Bande dessinée",
      models: MODELS,
    });

    const { result } = renderHook(() => useBatchComposer());
    await waitFor(() => expect(result.current.questions).toEqual(QUESTIONS));

    const [item] = result.current.items;
    act(() => result.current.setItemMode(item.id, "assistant"));
    for (let i = 0; i < 5; i++) {
      await act(async () => {
        await result.current.submitAssistantAnswer(item.id, { source: "list", index: 1 });
      });
    }

    const updatedAnswers: Record<QuestionKey, ResolvedAnswer> = {
      ...RESOLVED_ANSWERS,
      who: { key: "who", label: "Who", source: "free_text", index: null, text: "un robot" },
    };
    mockedApi.postScript.mockResolvedValueOnce({
      mode: "per_question",
      answers: updatedAnswers,
      script: "Bande dessinée, un robot, Forêt, Aube, Plan large",
      style: "Bande dessinée",
      models: MODELS,
    });

    await act(async () => {
      await result.current.updateAssistantAnswerField(item.id, "who", {
        source: "free_text",
        text: "un robot",
      });
    });

    expect(mockedApi.postScript).toHaveBeenLastCalledWith({
      mode: "per_question",
      answers: {
        what: { source: "list", index: 1 },
        who: { source: "free_text", text: "un robot" },
        where: { source: "list", index: 1 },
        when: { source: "list", index: 1 },
        how: { source: "list", index: 1 },
      },
    });
    expect(result.current.items[0].script).toBe("Bande dessinée, un robot, Forêt, Aube, Plan large");
    expect(result.current.items[0].resolvedAnswers).toEqual(updatedAnswers);
  });

  it("resetAssistant clears the assistant progress for an item", async () => {
    const { result } = renderHook(() => useBatchComposer());
    await waitFor(() => expect(result.current.questions).toEqual(QUESTIONS));

    const [item] = result.current.items;
    act(() => result.current.setItemMode(item.id, "assistant"));
    await act(async () => {
      await result.current.submitAssistantAnswer(item.id, { source: "list", index: 1 });
    });
    expect(result.current.items[0].assistantQuestionIndex).toBe(1);

    act(() => result.current.resetAssistant(item.id));

    expect(result.current.items[0].assistantQuestionIndex).toBe(0);
    expect(result.current.items[0].assistantAnswers).toEqual({});
    expect(result.current.items[0].assistantComplete).toBe(false);
    expect(result.current.items[0].script).toBe("");
  });
});
