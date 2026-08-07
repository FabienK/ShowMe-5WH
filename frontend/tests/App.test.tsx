import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import * as api from "../src/api/client";
import type { QuestionDefinition } from "../src/types";

vi.mock("../src/api/client");

const mockedApi = vi.mocked(api);

const QUESTIONS: QuestionDefinition[] = [
  { key: "what", label: "What", options: ["Bande dessinée"] },
  { key: "who", label: "Who", options: ["Personnage humain seul"] },
  { key: "where", label: "Where", options: ["Forêt"] },
  { key: "when", label: "When", options: ["Aube"] },
  { key: "how", label: "How", options: ["Plan large"] },
];

beforeEach(() => {
  vi.resetAllMocks();
  mockedApi.getQuestions.mockResolvedValue(QUESTIONS);
  mockedApi.getComfyUIStatus.mockResolvedValue(false);
});

describe("App", () => {
  it("shows a warning banner when ComfyUI is unreachable", async () => {
    render(<App />);
    expect(await screen.findByText(/ComfyUI n'est pas détecté/i)).toBeInTheDocument();
  });

  it("walks the global-random path through to a real error banner on generate failure", async () => {
    mockedApi.postScript.mockResolvedValue({
      mode: "global_random",
      answers: null,
      script: "Bande dessinée, Personnage humain seul, Forêt, Aube, Plan large",
      style: "Bande dessinée",
    });
    mockedApi.postGenerate.mockRejectedValue({
      status: 503,
      errorType: "comfyui_unreachable",
      detail: "Impossible de contacter ComfyUI sur http://127.0.0.1:8188",
    });

    const user = userEvent.setup();
    render(<App />);

    await screen.findByText(/ComfyUI n'est pas détecté/i);
    await user.click(screen.getByRole("button", { name: /tout générer pour moi/i }));

    await screen.findByText(/script assemblé/i);
    await user.click(screen.getByRole("button", { name: /lancer la génération/i }));

    expect(await screen.findByText(/Impossible de contacter ComfyUI/i)).toBeInTheDocument();
  });
});
