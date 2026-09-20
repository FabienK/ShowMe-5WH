import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../src/api/client";
import { HistoryPage } from "../src/pages/HistoryPage";
import type { BatchDetail, BatchSummary } from "../src/types";

vi.mock("../src/api/client");

const mockedApi = vi.mocked(api);

const RUNNING_SUMMARY: BatchSummary = {
  batch_id: "batch-running",
  status: "running",
  created_at: "2026-08-18T07:00:00Z",
  total_items: 2,
  completed_items: 1,
  error_items: 0,
};

const COMPLETED_SUMMARY: BatchSummary = {
  batch_id: "batch-done",
  status: "completed",
  created_at: "2026-08-17T22:00:00Z",
  total_items: 1,
  completed_items: 1,
  error_items: 0,
};

const RUNNING_DETAIL: BatchDetail = {
  batch_id: "batch-running",
  status: "running",
  created_at: "2026-08-18T07:00:00Z",
  items: [
    {
      index: 0,
      request: { script: "un chat", style: null },
      status: "success",
      image_path: "batch-running/0.png",
      prompt_id: "p1",
      seed_used: 1,
      preset_used: null,
      error_type: null,
      error_detail: null,
      started_at: null,
      finished_at: null,
    },
    {
      index: 1,
      request: { script: "un chien", style: null },
      status: "running",
      image_path: null,
      prompt_id: null,
      seed_used: null,
      preset_used: null,
      error_type: null,
      error_detail: null,
      started_at: null,
      finished_at: null,
    },
  ],
};

const INTERRUPTED_DETAIL: BatchDetail = {
  ...RUNNING_DETAIL,
  batch_id: "batch-interrupted",
  status: "interrupted",
};

beforeEach(() => {
  vi.resetAllMocks();
});

describe("HistoryPage", () => {
  it("lists past batches with their status", async () => {
    mockedApi.getBatches.mockResolvedValue([RUNNING_SUMMARY, COMPLETED_SUMMARY]);

    render(<HistoryPage />);

    expect(await screen.findByText(/running/i)).toBeInTheDocument();
    expect(screen.getByText(/completed/i)).toBeInTheDocument();
    expect(screen.getByText(/1\/2 image/i)).toBeInTheDocument();
  });

  it("shows an empty state when there are no batches", async () => {
    mockedApi.getBatches.mockResolvedValue([]);

    render(<HistoryPage />);

    expect(await screen.findByText(/no batches/i)).toBeInTheDocument();
  });

  it("opens a batch and shows its per-item thumbnails, polling while running", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockedApi.getBatches.mockResolvedValue([RUNNING_SUMMARY]);
    mockedApi.getBatch.mockResolvedValue(RUNNING_DETAIL);

    const user = userEvent.setup({ delay: null });
    render(<HistoryPage />);

    await screen.findByText(/running/i);
    await user.click(screen.getByText(/batch from/i));

    // "un chat" (item terminé) : la légende tronquée sous la vignette a été
    // retirée — on vérifie via l'alt text de l'image à la place.
    expect(await screen.findByAltText("un chat")).toBeInTheDocument();
    expect(screen.queryByText("un chat")).not.toBeInTheDocument();

    // "un chien" (item en cours) : affiché en entier dans le bandeau "En cours".
    const currentPrompt = screen.getByText("un chien");
    expect(currentPrompt.closest(".history-page__current-prompt")).not.toBeNull();
    expect(mockedApi.getBatch).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(3000);
    expect(mockedApi.getBatch).toHaveBeenCalledTimes(2);

    vi.useRealTimers();
  });

  it("hides the currently-generating banner once the batch is no longer running", async () => {
    mockedApi.getBatches.mockResolvedValue([COMPLETED_SUMMARY]);
    mockedApi.getBatch.mockResolvedValue({
      batch_id: "batch-done",
      status: "completed",
      created_at: "2026-08-17T22:00:00Z",
      items: [
        {
          index: 0,
          request: { script: "un chat", style: null },
          status: "success",
          image_path: "batch-done/0.png",
          prompt_id: "p1",
          seed_used: 1,
          preset_used: null,
          error_type: null,
          error_detail: null,
          started_at: null,
          finished_at: null,
        },
      ],
    });

    const user = userEvent.setup();
    render(<HistoryPage />);

    await screen.findByText(/completed/i);
    await user.click(screen.getByText(/batch from/i));

    await screen.findByAltText("un chat");
    expect(document.querySelector(".history-page__current-prompt")).toBeNull();
  });

  it("does not show a stale 'running' item as currently generating once the batch is interrupted", async () => {
    mockedApi.getBatches.mockResolvedValue([
      { ...RUNNING_SUMMARY, batch_id: "batch-interrupted", status: "interrupted" },
    ]);
    mockedApi.getBatch.mockResolvedValue(INTERRUPTED_DETAIL);

    const user = userEvent.setup();
    render(<HistoryPage />);

    await screen.findByText(/interrupted/i);
    await user.click(screen.getByText(/batch from/i));

    await screen.findByAltText("un chat");
    expect(document.querySelector(".history-page__current-prompt")).toBeNull();
    expect(screen.queryByText("un chien")).not.toBeInTheDocument();
  });
});
