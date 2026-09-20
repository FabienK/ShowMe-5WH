import { useState } from "react";
import { ModeSelector } from "../components/ModeSelector";
import { ImageReferenceUploader } from "../components/ImageReferenceUploader";
import { Loader } from "../components/Loader";
import { SparkleIcon, WarningIcon } from "../components/icons";
import { trackSpotlight } from "../utils/spotlight";
import heroBird from "../assets/hero-bird.webp";

interface HomePageProps {
  comfyReachable: boolean | null;
  loading: boolean;
  onFreePrompt: (text: string) => void;
  onGlobalRandom: () => void;
  onPerQuestion: () => void;
  onImageReference: (imageDataUrl: string, guidanceText: string, denoise: number) => void;
}

function denoiseHint(denoise: number): string {
  if (denoise < 0.35) return "Very close to the original image";
  if (denoise <= 0.6) return "Keeps the composition, changes the details";
  return "Moves further from the original image, more creative freedom";
}

export function HomePage({
  comfyReachable,
  loading,
  onFreePrompt,
  onGlobalRandom,
  onPerQuestion,
  onImageReference,
}: HomePageProps) {
  const [showFreePromptInput, setShowFreePromptInput] = useState(false);
  const [freePromptText, setFreePromptText] = useState("");

  const [showImageReferenceInput, setShowImageReferenceInput] = useState(false);
  const [referenceImageDataUrl, setReferenceImageDataUrl] = useState<string | null>(null);
  const [guidanceText, setGuidanceText] = useState("");
  const [denoise, setDenoise] = useState(0.6);

  const submitFreePrompt = (event: React.FormEvent) => {
    event.preventDefault();
    if (!freePromptText.trim()) return;
    onFreePrompt(freePromptText.trim());
  };

  const cancelImageReference = () => {
    setShowImageReferenceInput(false);
    setReferenceImageDataUrl(null);
    setGuidanceText("");
    setDenoise(0.6);
  };

  const submitImageReference = (event: React.FormEvent) => {
    event.preventDefault();
    if (!referenceImageDataUrl) return;
    onImageReference(referenceImageDataUrl, guidanceText, denoise);
  };

  return (
    <div className="home-page">
      <header className="home-page__hero">
        <span className="home-page__eyebrow">
          <SparkleIcon />
          Image generation studio
        </span>
        <h1 className="home-page__title">
          Show<span className="home-page__title-accent">Me</span>-5WH
        </h1>
        <p className="home-page__tagline">
          Describe your scene, let chance compose one, or start from an image — you decide, the
          studio does the rest.
        </p>
        <img
          className="home-page__hero-bird"
          src={heroBird}
          alt=""
          aria-hidden="true"
        />
      </header>

      {comfyReachable === false && (
        <div className="comfy-warning" role="status">
          <WarningIcon />
          <p>
            ComfyUI isn't detected on this machine. You can still prepare your script, but image
            generation will fail until ComfyUI is started.
          </p>
        </div>
      )}

      {loading ? (
        <Loader label="Preparing the script…" />
      ) : showFreePromptInput ? (
        <form
          className="home-page__panel card"
          onSubmit={submitFreePrompt}
          onMouseMove={trackSpotlight}
        >
          <label htmlFor="free-prompt-textarea">Your full prompt</label>
          <textarea
            id="free-prompt-textarea"
            value={freePromptText}
            onChange={(event) => setFreePromptText(event.target.value)}
            rows={4}
            placeholder="E.g. a cyberpunk cat in a futuristic city, at night, wide shot…"
          />
          <div className="home-page__free-prompt-actions">
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => setShowFreePromptInput(false)}
            >
              Cancel
            </button>
            <button type="submit" className="btn btn--primary" disabled={!freePromptText.trim()}>
              Continue
            </button>
          </div>
        </form>
      ) : showImageReferenceInput ? (
        <form
          className="home-page__panel card"
          onSubmit={submitImageReference}
          onMouseMove={trackSpotlight}
        >
          <ImageReferenceUploader value={referenceImageDataUrl} onChange={setReferenceImageDataUrl} />

          <label htmlFor="image-reference-guidance">
            Describe the changes you want (optional)
          </label>
          <textarea
            id="image-reference-guidance"
            value={guidanceText}
            onChange={(event) => setGuidanceText(event.target.value)}
            rows={3}
            placeholder="E.g. turn into a watercolor painting…"
          />

          <label htmlFor="image-reference-denoise">
            Transformation strength: {denoise.toFixed(2)}
          </label>
          <input
            id="image-reference-denoise"
            type="range"
            min={0.1}
            max={1}
            step={0.05}
            value={denoise}
            onChange={(event) => setDenoise(Number(event.target.value))}
          />
          <span className="home-page__denoise-hint">{denoiseHint(denoise)}</span>

          <div className="home-page__image-reference-actions">
            <button type="button" className="btn btn--secondary" onClick={cancelImageReference}>
              Cancel
            </button>
            <button type="submit" className="btn btn--primary" disabled={!referenceImageDataUrl}>
              Continue
            </button>
          </div>
        </form>
      ) : (
        <div className="home-page__modes">
          <p className="home-page__section-label">How would you like to start?</p>
          <ModeSelector
            onFreePrompt={() => setShowFreePromptInput(true)}
            onGlobalRandom={onGlobalRandom}
            onPerQuestion={onPerQuestion}
            onImageReference={() => setShowImageReferenceInput(true)}
          />
        </div>
      )}
    </div>
  );
}
