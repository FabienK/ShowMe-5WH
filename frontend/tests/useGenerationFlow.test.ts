import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../src/api/client";
import { useGenerationFlow } from "../src/state/useGenerationFlow";
import type { ModelOption, QuestionDefinition } from "../src/types";

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

const MODELS_WITH_FLUX_SCHNELL: ModelOption[] = [
  ...MODELS,
  {
    id: "flux-schnell-1",
    label: "Flux",
    version: "schnell",
    estimated_time: "~2 min 30",
    description: "Modèle rapide",
    engine_type: "flux_schnell",
    checkpoint: null,
    lora: null,
    sampler: "euler",
    scheduler: "simple",
    steps: 4,
    cfg: 3.5,
    width: 1024,
    height: 1024,
    negative_prompt: "",
  },
];

const MODELS_WITH_FLUX_KONTEXT: ModelOption[] = [
  ...MODELS,
  {
    id: "flux-kontext-1",
    label: "Flux Kontext",
    version: "dev",
    estimated_time: "~12 min",
    description: "Modèle d'édition",
    engine_type: "flux_kontext",
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

beforeEach(() => {
  vi.resetAllMocks();
  mockedApi.getQuestions.mockResolvedValue(QUESTIONS);
  mockedApi.getComfyUIStatus.mockResolvedValue(true);
  mockedApi.getOpenAIBalance.mockResolvedValue({
    balance_usd: 5,
    price_per_text_input_token_usd: 0.000005,
    price_per_image_input_token_usd: 0.000008,
    price_per_cached_image_input_token_usd: 0.000002,
    price_per_output_token_usd: 0.00003,
    estimated_cost_per_generation_usd: 0.03,
  });
});

describe("useGenerationFlow", () => {
  it("loads questions and comfy status on mount", async () => {
    const { result } = renderHook(() => useGenerationFlow());

    await waitFor(() => expect(result.current.questionsLoading).toBe(false));
    expect(result.current.questions).toEqual(QUESTIONS);
    expect(result.current.comfyReachable).toBe(true);
  });

  it("walks the full per-question happy path to the result screen", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "per_question",
      answers: null,
      script: "Bande dessinée, Personnage humain seul, Forêt, Aube, Plan large",
      style: "Bande dessinée",
      models: MODELS,
    });
    mockedApi.postGenerate.mockResolvedValue({
      status: "success",
      image_base64: "data:image/png;base64,AAAA",
      prompt_id: "p1",
      seed_used: 1,
      preset_used: {
        style: "Bande dessinée",
        model_id: "model-1",
        model_label: "Modèle 1",
        checkpoint: "x",
        lora: null,
        sampler: "euler",
        scheduler: "normal",
        steps: 20,
        cfg: 7,
        width: 512,
        height: 512,
      },
    });

    const { result } = renderHook(() => useGenerationFlow());
    await waitFor(() => expect(result.current.questionsLoading).toBe(false));

    act(() => result.current.chooseAnswerQuestionByQuestion());
    expect(result.current.step).toBe("question");

    for (let i = 0; i < 5; i++) {
      await act(async () => {
        await result.current.submitAnswerForCurrentQuestion({ source: "list", index: 1 });
      });
    }

    expect(result.current.step).toBe("preview");
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

    await act(async () => {
      await result.current.confirmAndGenerate();
    });

    expect(result.current.step).toBe("result");
    expect(result.current.results[0]?.image_base64).toBe("data:image/png;base64,AAAA");
    expect(result.current.error).toBeNull();
  });

  it("surfaces an error and stays on the result screen when generation fails", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "free_prompt",
      answers: null,
      script: "un chat en armure",
      style: null,
      models: MODELS,
    });
    mockedApi.postGenerate.mockRejectedValue({
      status: 503,
      errorType: "comfyui_unreachable",
      detail: "Impossible de contacter ComfyUI",
    });

    const { result } = renderHook(() => useGenerationFlow());
    await waitFor(() => expect(result.current.questionsLoading).toBe(false));

    await act(async () => {
      await result.current.chooseFreePrompt("un chat en armure");
    });
    expect(result.current.step).toBe("preview");

    await act(async () => {
      await result.current.confirmAndGenerate();
    });

    expect(result.current.step).toBe("result");
    expect(result.current.results).toHaveLength(0);
    expect(result.current.error?.errorType).toBe("comfyui_unreachable");
  });

  it("chooseImageReference sets referenceImage and moves to preview", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "free_prompt",
      answers: null,
      script: "",
      style: null,
      models: MODELS,
    });

    const { result } = renderHook(() => useGenerationFlow());
    await waitFor(() => expect(result.current.questionsLoading).toBe(false));

    await act(async () => {
      await result.current.chooseImageReference("data:image/png;base64,AAAA", "", 0.4);
    });

    expect(result.current.step).toBe("preview");
    expect(result.current.referenceImage).toBe("data:image/png;base64,AAAA");
    expect(result.current.denoiseStrength).toBe(0.4);
    expect(mockedApi.postScript).toHaveBeenCalledWith({ mode: "free_prompt", prompt: "" });
  });

  it("availableModels excludes flux_kontext until a reference image is set", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "free_prompt",
      answers: null,
      script: "un chat en armure",
      style: null,
      models: MODELS_WITH_FLUX_KONTEXT,
    });

    const { result } = renderHook(() => useGenerationFlow());
    await waitFor(() => expect(result.current.questionsLoading).toBe(false));

    await act(async () => {
      await result.current.chooseFreePrompt("un chat en armure");
    });
    expect(result.current.availableModels).toEqual(MODELS);

    await act(async () => {
      await result.current.chooseImageReference("data:image/png;base64,AAAA", "", 0.6);
    });
    expect(result.current.availableModels).toEqual(MODELS_WITH_FLUX_KONTEXT);
  });

  it("availableModels excludes flux_schnell only when a reference image is set", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "free_prompt",
      answers: null,
      script: "un chat en armure",
      style: null,
      models: MODELS_WITH_FLUX_SCHNELL,
    });

    const { result } = renderHook(() => useGenerationFlow());
    await waitFor(() => expect(result.current.questionsLoading).toBe(false));

    await act(async () => {
      await result.current.chooseFreePrompt("un chat en armure");
    });
    expect(result.current.availableModels).toEqual(MODELS_WITH_FLUX_SCHNELL);

    await act(async () => {
      await result.current.chooseImageReference("data:image/png;base64,AAAA", "", 0.6);
    });
    expect(result.current.availableModels).toEqual(MODELS);
  });

  it("generateForModels sends reference_image and denoise_strength when set", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "free_prompt",
      answers: null,
      script: "",
      style: null,
      models: MODELS,
    });
    mockedApi.postGenerate.mockResolvedValue({
      status: "success",
      image_base64: "data:image/png;base64,AAAA",
      prompt_id: "p1",
      seed_used: 1,
      preset_used: {
        style: "default",
        model_id: "model-1",
        model_label: "Modèle 1",
        checkpoint: "x",
        lora: null,
        sampler: "euler",
        scheduler: "normal",
        steps: 20,
        cfg: 7,
        width: 512,
        height: 512,
      },
    });

    const { result } = renderHook(() => useGenerationFlow());
    await waitFor(() => expect(result.current.questionsLoading).toBe(false));

    await act(async () => {
      await result.current.chooseImageReference("data:image/png;base64,AAAA", "", 0.35);
    });
    await act(async () => {
      await result.current.confirmAndGenerate();
    });

    expect(mockedApi.postGenerate).toHaveBeenCalledWith(
      expect.objectContaining({
        reference_image: "data:image/png;base64,AAAA",
        denoise_strength: 0.35,
      }),
    );
  });

  it("availableModels excludes openai once a reference image is set", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "free_prompt",
      answers: null,
      script: "un chat en armure",
      style: null,
      models: MODELS_WITH_OPENAI,
    });

    const { result } = renderHook(() => useGenerationFlow());
    await waitFor(() => expect(result.current.questionsLoading).toBe(false));

    await act(async () => {
      await result.current.chooseFreePrompt("un chat en armure");
    });
    expect(result.current.availableModels).toEqual(MODELS_WITH_OPENAI);

    await act(async () => {
      await result.current.chooseImageReference("data:image/png;base64,AAAA", "", 0.6);
    });
    expect(result.current.availableModels).toEqual(MODELS);
  });

  it("refreshes the OpenAI balance after a successful openai generation, not for local engines", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "free_prompt",
      answers: null,
      script: "un chat en armure",
      style: null,
      models: MODELS_WITH_OPENAI,
    });
    mockedApi.postGenerate.mockResolvedValue({
      status: "success",
      image_base64: "data:image/png;base64,AAAA",
      prompt_id: "openai-p1",
      seed_used: 1,
      preset_used: {
        style: "default",
        model_id: "openai-1",
        model_label: "GPT Image 2",
        checkpoint: "gpt-image-2",
        lora: null,
        sampler: "-",
        scheduler: "-",
        steps: 0,
        cfg: 0,
        width: 1024,
        height: 1024,
      },
    });

    const { result } = renderHook(() => useGenerationFlow());
    await waitFor(() => expect(result.current.questionsLoading).toBe(false));
    // Un appel au montage — voir "loads questions and comfy status on mount".
    await waitFor(() => expect(mockedApi.getOpenAIBalance).toHaveBeenCalledTimes(1));

    await act(async () => {
      await result.current.chooseFreePrompt("un chat en armure");
    });
    act(() => result.current.toggleModelSelection("openai-1"));

    await act(async () => {
      await result.current.confirmAndGenerate();
    });

    // Un seul modèle (openai) généré -> un seul refresh en plus de celui du montage.
    expect(mockedApi.getOpenAIBalance).toHaveBeenCalledTimes(2);
  });
});
