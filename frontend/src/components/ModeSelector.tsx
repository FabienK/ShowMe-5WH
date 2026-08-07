interface ModeSelectorProps {
  onFreePrompt: () => void;
  onGlobalRandom: () => void;
  onPerQuestion: () => void;
  disabled?: boolean;
}

export function ModeSelector({
  onFreePrompt,
  onGlobalRandom,
  onPerQuestion,
  disabled,
}: ModeSelectorProps) {
  return (
    <div className="mode-selector">
      <button type="button" onClick={onFreePrompt} disabled={disabled}>
        Prompt libre
      </button>
      <button type="button" onClick={onGlobalRandom} disabled={disabled}>
        Tout générer pour moi
      </button>
      <button type="button" onClick={onPerQuestion} disabled={disabled}>
        Répondre question par question
      </button>
    </div>
  );
}
