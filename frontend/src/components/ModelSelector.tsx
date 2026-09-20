import { trackSpotlight } from "../utils/spotlight";
import type { ModelOption } from "../types";

export interface ModelExtra {
  note?: string;
  disabled?: boolean;
}

interface ModelSelectorProps {
  models: ModelOption[];
  selectedIds: string[];
  onToggle: (modelId: string) => void;
  disabled?: boolean;
  // Décoration facultative par modèle (ex. coût/solde OpenAI) — calculée par
  // la page appelante, ce composant reste purement présentationnel et ne
  // connaît aucun moteur spécifique.
  modelExtras?: Record<string, ModelExtra>;
}

export function ModelSelector({
  models,
  selectedIds,
  onToggle,
  disabled,
  modelExtras,
}: ModelSelectorProps) {
  if (models.length <= 1) return null;

  return (
    <div className="model-selector">
      {models.map((model) => {
        const checked = selectedIds.includes(model.id);
        const extra = modelExtras?.[model.id];
        const optionDisabled = disabled || extra?.disabled;
        return (
          <button
            key={model.id}
            type="button"
            className={`model-selector__option${
              checked ? " model-selector__option--selected" : ""
            }${extra?.disabled ? " model-selector__option--warning" : ""}`}
            onClick={() => onToggle(model.id)}
            onMouseMove={trackSpotlight}
            disabled={optionDisabled}
            aria-pressed={checked}
          >
            <span className="model-selector__title">
              {model.label}
              <span className="model-selector__meta">
                {" "}
                · {model.version} · {model.estimated_time}
              </span>
            </span>
            <span className="model-selector__description">{model.description}</span>
            {extra?.note && <span className="model-selector__note">{extra.note}</span>}
          </button>
        );
      })}
    </div>
  );
}
