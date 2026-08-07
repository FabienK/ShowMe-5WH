import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../src/api/client";
import { useGenerationFlow } from "../src/state/useGenerationFlow";
import type { QuestionDefinition } from "../src/types";

vi.mock("../src/api/client");

const mockedApi = vi.mocked(api);

const QUESTIONS: QuestionDefinition[] = [
  { key: "what", label: "What", options: ["Bande dessinée", "Photoréaliste"] },
  { key: "who", label: "Who", options: ["Personnage humain seul", "Duo de personnages"] },
  { key: "where", label: "Where", options: ["Forêt", "Ville futuriste"] },
  { key: "when", label: "When", options: ["Aube", "Matin"] },
  { key: "how", label: "How", options: ["Plan large", "Gros plan"] },
];

beforeEach(() => {
  vi.resetAllMocks();
  mockedApi.getQuestions.mockResolvedValue(QUESTIONS);
  mockedApi.getComfyUIStatus.mockResolvedValue(true);
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
    });
    mockedApi.postGenerate.mockResolvedValue({
      status: "success",
      image_base64: "data:image/png;base64,AAAA",
      prompt_id: "p1",
      seed_used: 1,
      preset_used: {
        style: "Bande dessinée",
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
    expect(result.current.generateResult?.image_base64).toBe("data:image/png;base64,AAAA");
    expect(result.current.error).toBeNull();
  });

  it("surfaces an error and stays on the result screen when generation fails", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "free_prompt",
      answers: null,
      script: "un chat en armure",
      style: null,
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
    expect(result.current.generateResult).toBeNull();
    expect(result.current.error?.errorType).toBe("comfyui_unreachable");
  });
});
