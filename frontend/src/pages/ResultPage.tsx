import { useEffect, useRef, useState } from "react";
import { ErrorBanner } from "../components/ErrorBanner";
import { Loader } from "../components/Loader";
import { CloseIcon, DownloadIcon, ExpandIcon } from "../components/icons";
import type { ApiError, GenerateResponse, ModelOption } from "../types";

interface ResultPageProps {
  results: GenerateResponse[];
  pendingModels: ModelOption[];
  loading: boolean;
  error: ApiError | null;
  script: string;
  onRegenerate: () => void;
  onModify: () => void;
  onRestart: () => void;
}

// pendingModels est la file complète (un modèle répété selon son nombre
// d'images, triée du plus rapide au plus lent) — completedCount permet de
// savoir où on en est et quel job est en cours.
function loadingLabelFor(jobs: ModelOption[], completedCount: number): string {
  const total = jobs.length;
  const current = jobs[completedCount];
  if (!current) {
    return "Generating… (can take several minutes on a Mac mini M4)";
  }
  const progress = total > 1 ? `Image ${completedCount + 1}/${total} — ` : "";
  return `${progress}Generating with ${current.label} ${current.version}… (${current.estimated_time} on this Mac)`;
}

function extensionFromDataUrl(dataUrl: string): string {
  const match = /^data:image\/([a-zA-Z0-9.+-]+);base64,/.exec(dataUrl);
  return match ? match[1].split("+")[0] : "png";
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function downloadFileName(result: GenerateResponse): string {
  const ext = extensionFromDataUrl(result.image_base64);
  const slug = slugify(result.preset_used.model_id) || result.preset_used.model_id;
  return `image-${slug}-${result.seed_used}.${ext}`;
}

export function ResultPage({
  results,
  pendingModels,
  loading,
  error,
  script,
  onRegenerate,
  onModify,
  onRestart,
}: ResultPageProps) {
  const [zoomedResult, setZoomedResult] = useState<GenerateResponse | null>(null);
  const [lightboxVisible, setLightboxVisible] = useState(false);
  const lightboxCloseTimeout = useRef<number | undefined>(undefined);

  // Durée de sortie alignée sur la plus longue transition CSS de la lightbox
  // (transform de .lightbox__image, 250ms) pour laisser l'animation finir
  // avant le démontage réel.
  const LIGHTBOX_EXIT_MS = 250;

  function openLightbox(result: GenerateResponse) {
    window.clearTimeout(lightboxCloseTimeout.current);
    setZoomedResult(result);
    requestAnimationFrame(() => setLightboxVisible(true));
  }

  function closeLightbox() {
    setLightboxVisible(false);
    lightboxCloseTimeout.current = window.setTimeout(() => {
      setZoomedResult(null);
    }, LIGHTBOX_EXIT_MS);
  }

  useEffect(() => {
    if (loading) {
      window.clearTimeout(lightboxCloseTimeout.current);
      setLightboxVisible(false);
      setZoomedResult(null);
    }
  }, [loading]);

  useEffect(() => {
    if (!zoomedResult) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeLightbox();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [zoomedResult]);

  useEffect(() => {
    return () => window.clearTimeout(lightboxCloseTimeout.current);
  }, []);

  return (
    <div className="result-page">
      <h2>Result</h2>
      <p className="result-page__script">{script}</p>

      {loading && <Loader label={loadingLabelFor(pendingModels, results.length)} />}

      {!loading && error && <ErrorBanner error={error} />}

      {results.length > 0 && (
        <div className="result-page__results">
          {results.map((result, index) => {
            const sameModelResults = results.filter(
              (other) => other.preset_used.model_id === result.preset_used.model_id,
            );
            const occurrenceIndex =
              results
                .slice(0, index)
                .filter((other) => other.preset_used.model_id === result.preset_used.model_id)
                .length + 1;

            return (
            <div
              className="result-page__result"
              key={`${result.preset_used.model_id}-${index}`}
            >
              {results.length > 1 && (
                <h3 className="result-page__result-title">
                  {result.preset_used.model_label} · {result.preset_used.model_version}
                  {sameModelResults.length > 1 && ` (${occurrenceIndex}/${sameModelResults.length})`}
                </h3>
              )}

              <div className="result-page__image-wrap">
                <button
                  type="button"
                  className="result-page__image-button"
                  onClick={() => openLightbox(result)}
                  aria-label="Enlarge the image"
                >
                  <img className="result-page__image" src={result.image_base64} alt={script} />
                  <span className="result-page__image-zoom-hint" aria-hidden="true">
                    <ExpandIcon />
                  </span>
                </button>
                <a
                  className="icon-button result-page__download"
                  href={result.image_base64}
                  download={downloadFileName(result)}
                  aria-label="Download the image"
                  title="Download the image"
                >
                  <DownloadIcon />
                </a>
              </div>
            </div>
            );
          })}
        </div>
      )}

      {!loading && (
        <div className="result-page__actions">
          <button type="button" onClick={onRegenerate}>
            Regenerate
          </button>
          <button type="button" onClick={onModify}>
            Edit
          </button>
          <button type="button" onClick={onRestart}>
            New
          </button>
        </div>
      )}

      {zoomedResult && (
        <div
          className={`lightbox${lightboxVisible ? " lightbox--visible" : ""}`}
          role="dialog"
          aria-modal="true"
          aria-label="Close-up image"
          onClick={closeLightbox}
        >
          <div className="lightbox__toolbar" onClick={(event) => event.stopPropagation()}>
            <a
              className="icon-button lightbox__download"
              href={zoomedResult.image_base64}
              download={downloadFileName(zoomedResult)}
              aria-label="Download the image"
              title="Download the image"
            >
              <DownloadIcon />
            </a>
            <button
              type="button"
              className="icon-button lightbox__close"
              onClick={closeLightbox}
              aria-label="Close"
              title="Close"
            >
              <CloseIcon />
            </button>
          </div>
          <img
            className="lightbox__image"
            src={zoomedResult.image_base64}
            alt={script}
            onClick={(event) => event.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}
