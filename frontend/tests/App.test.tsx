import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import * as api from "../src/api/client";
import type { ModelOption, QuestionDefinition } from "../src/types";

vi.mock("../src/api/client");

const mockedApi = vi.mocked(api);

const QUESTIONS: QuestionDefinition[] = [
  { key: "what", label: "What", options: ["Bande dessinée"] },
  { key: "who", label: "Who", options: ["Personnage humain seul"] },
  { key: "where", label: "Where", options: ["Forêt"] },
  { key: "when", label: "When", options: ["Aube"] },
  { key: "how", label: "How", options: ["Plan large"] },
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

beforeEach(() => {
  vi.resetAllMocks();
  mockedApi.getQuestions.mockResolvedValue(QUESTIONS);
  mockedApi.getComfyUIStatus.mockResolvedValue(false);
  mockedApi.getOpenAIBalance.mockResolvedValue({
    balance_usd: 5,
    price_per_text_input_token_usd: 0.000005,
    price_per_image_input_token_usd: 0.000008,
    price_per_cached_image_input_token_usd: 0.000002,
    price_per_output_token_usd: 0.00003,
    estimated_cost_per_generation_usd: 0.03,
  });
});

describe("App", () => {
  it("shows a warning banner when ComfyUI is unreachable", async () => {
    render(<App />);
    expect(await screen.findByText(/ComfyUI isn't detected/i)).toBeInTheDocument();
  });

  it("walks the global-random path through to a real error banner on generate failure", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "global_random",
      answers: null,
      script: "Bande dessinée, Personnage humain seul, Forêt, Aube, Plan large",
      style: "Bande dessinée",
      models: MODELS,
    });
    mockedApi.postGenerate.mockRejectedValue({
      status: 503,
      errorType: "comfyui_unreachable",
      detail: "Could not reach ComfyUI at http://127.0.0.1:8188",
    });

    const user = userEvent.setup();
    render(<App />);

    await screen.findByText(/ComfyUI isn't detected/i);
    await user.click(screen.getByRole("button", { name: /random/i }));

    await screen.findByText(/Bande dessinée, Personnage humain seul/i);
    await user.click(screen.getByRole("button", { name: /generate/i }));

    expect(await screen.findByText(/Could not reach ComfyUI/i)).toBeInTheDocument();
  });

  it("reveals the image reference upload form when its tile is clicked", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText(/ComfyUI isn't detected/i);
    await user.click(screen.getByRole("button", { name: /reference image/i }));

    expect(
      await screen.findByText(/drag and drop an image, or click to choose one/i),
    ).toBeInTheDocument();
  });
});
