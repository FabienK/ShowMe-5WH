import { AssistantIcon, DiceIcon, FreePromptIcon, UploadIcon } from "./icons";
import { trackSpotlight } from "../utils/spotlight";

interface ModeSelectorProps {
  onFreePrompt: () => void;
  onGlobalRandom: () => void;
  onPerQuestion: () => void;
  onImageReference: () => void;
  disabled?: boolean;
}

export function ModeSelector({
  onFreePrompt,
  onGlobalRandom,
  onPerQuestion,
  onImageReference,
  disabled,
}: ModeSelectorProps) {
  return (
    <div className="mode-selector">
      <button
        type="button"
        className="mode-selector__featured"
        onClick={onPerQuestion}
        onMouseMove={trackSpotlight}
        disabled={disabled}
      >
        <span className="mode-selector__featured-badge">
          <AssistantIcon />
        </span>
        <span className="mode-selector__featured-text">
          <span className="mode-selector__featured-eyebrow">Recommended</span>
          <span className="mode-selector__featured-label">Assistant</span>
          <span className="mode-selector__featured-hint">Answer 5 guided questions</span>
        </span>
      </button>

      <div className="mode-selector__grid">
        <button
          type="button"
          className="mode-selector__tile"
          onClick={onFreePrompt}
          onMouseMove={trackSpotlight}
          disabled={disabled}
        >
          <span className="mode-selector__badge">
            <FreePromptIcon />
          </span>
          <span className="mode-selector__label">Free prompt</span>
          <span className="mode-selector__hint">Write your own description</span>
        </button>
        <button
          type="button"
          className="mode-selector__tile"
          onClick={onGlobalRandom}
          onMouseMove={trackSpotlight}
          disabled={disabled}
        >
          <span className="mode-selector__badge">
            <DiceIcon />
          </span>
          <span className="mode-selector__label">Random</span>
          <span className="mode-selector__hint">Let chance compose a scene</span>
        </button>
        <button
          type="button"
          className="mode-selector__tile"
          onClick={onImageReference}
          onMouseMove={trackSpotlight}
          disabled={disabled}
        >
          <span className="mode-selector__badge">
            <UploadIcon />
          </span>
          <span className="mode-selector__label">Reference image</span>
          <span className="mode-selector__hint">Start from an existing image</span>
        </button>
      </div>
    </div>
  );
}
