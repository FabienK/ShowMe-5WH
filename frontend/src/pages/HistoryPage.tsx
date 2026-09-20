import { useEffect, useState } from "react";
import * as api from "../api/client";
import { Loader } from "../components/Loader";
import { AppleActivityCard } from "../components/AppleActivityCard";
import type { ActivityRingData } from "../components/ActivityRing";
import type { BatchDetail, BatchSummary } from "../types";

function buildBatchProgressRings(detail: BatchDetail): ActivityRingData[] {
  const total = detail.items.length;
  const completed = detail.items.filter((item) => item.status === "success").length;
  const errors = detail.items.filter((item) => item.status === "error").length;
  const safeTotal = total || 1;

  return [
    {
      label: "Done",
      value: (completed / safeTotal) * 100,
      color: "var(--accent)",
      colorEnd: "var(--accent2)",
      size: 140,
      current: completed,
      target: total,
      unit: "img",
    },
    {
      label: "Errors",
      value: (errors / safeTotal) * 100,
      color: "var(--error-text)",
      colorEnd: "var(--error-text)",
      size: 100,
      current: errors,
      target: total,
      unit: "err",
    },
  ];
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleString("en-GB", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function statusLabel(status: BatchSummary["status"]): string {
  if (status === "running") return "Running";
  if (status === "interrupted") return "Interrupted";
  return "Completed";
}

function BatchRow({ summary, onOpen }: { summary: BatchSummary; onOpen: () => void }) {
  return (
    <button type="button" className="history-page__row" onClick={onOpen}>
      <span className={`history-page__status history-page__status--${summary.status}`}>
        {statusLabel(summary.status)}
      </span>
      <span className="history-page__row-title">Batch from {formatDate(summary.created_at)}</span>
      <span className="history-page__row-progress">
        {summary.completed_items}/{summary.total_items} image
        {summary.total_items > 1 ? "s" : ""}
        {summary.error_items > 0 && ` · ${summary.error_items} error${summary.error_items > 1 ? "s" : ""}`}
      </span>
    </button>
  );
}

function BatchItemThumbnail({ item }: { item: BatchDetail["items"][number] }) {
  if (item.status === "success" && item.image_path) {
    return (
      <a
        className="history-page__thumbnail"
        href={`/generated/${item.image_path}`}
        target="_blank"
        rel="noreferrer"
      >
        <img src={`/generated/${item.image_path}`} alt={item.request.script} />
      </a>
    );
  }
  if (item.status === "error") {
    return (
      <div className="history-page__thumbnail history-page__thumbnail--error">
        <p>{item.error_detail ?? "Unknown error"}</p>
      </div>
    );
  }
  return (
    <div className="history-page__thumbnail history-page__thumbnail--pending">
      {item.status === "running" ? <Loader label="Running…" /> : "Waiting"}
    </div>
  );
}

function CurrentlyGeneratingPrompt({ script }: { script: string }) {
  return (
    <div className="history-page__current-prompt">
      <Loader label="" />
      <p className="history-page__current-prompt-script">{script}</p>
    </div>
  );
}

function BatchDetailView({ batchId }: { batchId: string }) {
  const [detail, setDetail] = useState<BatchDetail | null>(null);

  useEffect(() => {
    let cancelled = false;
    let intervalId: number | undefined;

    async function load() {
      try {
        const data = await api.getBatch(batchId);
        if (cancelled) return;
        setDetail(data);
        if (data.status !== "running" && intervalId) {
          window.clearInterval(intervalId);
        }
      } catch {
        // Best-effort : on garde le dernier détail connu en cas d'échec ponctuel.
      }
    }

    load();
    intervalId = window.setInterval(load, 3000);

    return () => {
      cancelled = true;
      if (intervalId) window.clearInterval(intervalId);
    };
  }, [batchId]);

  if (!detail) return <Loader label="Loading batch…" />;

  // Le runner traite les items strictement en série : au plus un item
  // "running" à la fois. On ne l'affiche que si le batch tourne encore
  // réellement (un item resté "running" après un crash/redémarrage ne doit
  // pas laisser croire qu'une génération est en cours).
  const runningItem =
    detail.status === "running" ? detail.items.find((item) => item.status === "running") : undefined;

  return (
    <div className="history-page__detail">
      <AppleActivityCard title="Batch progress" rings={buildBatchProgressRings(detail)} />
      {runningItem && <CurrentlyGeneratingPrompt script={runningItem.request.script} />}
      <div className="history-page__detail-grid">
        {detail.items.map((item) => (
          <div className="history-page__detail-item" key={item.index}>
            <BatchItemThumbnail item={item} />
            {item.preset_used && (
              <p className="history-page__detail-model">{item.preset_used.model_label}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export function HistoryPage() {
  const [batches, setBatches] = useState<BatchSummary[] | null>(null);
  const [openBatchId, setOpenBatchId] = useState<string | null>(null);

  useEffect(() => {
    api.getBatches().then(setBatches).catch(() => setBatches([]));
  }, []);

  return (
    <div className="history-page">
      <h2>History</h2>

      {batches === null && <Loader label="Loading history…" />}

      {batches !== null && batches.length === 0 && (
        <p className="history-page__empty">No batches yet.</p>
      )}

      {batches !== null && batches.length > 0 && (
        <ul className="history-page__list">
          {batches.map((summary) => (
            <li key={summary.batch_id}>
              <BatchRow
                summary={summary}
                onOpen={() =>
                  setOpenBatchId(openBatchId === summary.batch_id ? null : summary.batch_id)
                }
              />
              {openBatchId === summary.batch_id && <BatchDetailView batchId={summary.batch_id} />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
