import { useMemo, useState } from "react";
import { AnswerFieldEditor } from "../components/AnswerFieldEditor";
import { ModelSelector, type ModelExtra } from "../components/ModelSelector";
import { DiceIcon } from "../components/icons";
import {
  estimateTotalCost,
  estimateTotalImages,
  estimateTotalSeconds,
  formatDuration,
} from "../utils/estimate";
import { trackSpotlight } from "../utils/spotlight";
import type {
  AnswerInput,
  OpenAIState,
  QuestionDefinition,
  QuestionKey,
  ScriptResponse,
} from "../types";

interface ScriptPreviewPageProps {
  scriptResult: ScriptResponse;
  models: ScriptResponse["models"];
  questions: QuestionDefinition[];
  freePromptText: string;
  loading: boolean;
  selectedModelIds: string[];
  onToggleModel: (modelId: string) => void;
  onAnswerFieldChange: (key: QuestionKey, input: AnswerInput) => void;
  onFreePromptSubmit: (text: string) => void;
  onReroll?: () => void;
  onConfirm: () => void;
  referenceImage: string | null;
  denoiseStrength: number;
  onDenoiseChange: (value: number) => void;
  openaiBalance: OpenAIState | null;
}

function FreePromptEditor({
  initialText,
  loading,
  onSubmit,
}: {
  initialText: string;
  loading: boolean;
  onSubmit: (text: string) => void;
}) {
  const [text, setText] = useState(initialText);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || trimmed === initialText) return;
    onSubmit(trimmed);
  }

  return (
    <form className="script-preview-page__free-prompt-edit" onSubmit={handleSubmit}>
      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        disabled={loading}
        rows={3}
        aria-label="Edit the prompt"
      />
      <button
        type="submit"
        className="btn btn--accent2 btn--sm"
        disabled={loading || !text.trim() || text.trim() === initialText}
      >
        Update the prompt
      </button>
    </form>
  );
}

export function ScriptPreviewPage({
  scriptResult,
  models,
  questions,
  freePromptText,
  loading,
  selectedModelIds,
  onToggleModel,
  onAnswerFieldChange,
  onFreePromptSubmit,
  onReroll,
  onConfirm,
  referenceImage,
  denoiseStrength,
  onDenoiseChange,
  openaiBalance,
}: ScriptPreviewPageProps) {
  const selectedModels = models.filter((model) => selectedModelIds.includes(model.id));
  const canGenerate = selectedModels.length > 0;
  const totalImages = estimateTotalImages(selectedModels);
  const totalSeconds = estimateTotalSeconds(selectedModels);
  const totalCost = estimateTotalCost(selectedModels, openaiBalance);
  const modelsFiltered = referenceImage != null && models.length !== scriptResult.models.length;
  const showModelSelector = models.length > 1;

  const modelExtras = useMemo(() => {
    const extras: Record<string, ModelExtra> = {};
    for (const model of models) {
      if (model.engine_type !== "openai") continue;
      if (!openaiBalance) {
        extras[model.id] = { note: "GPT Image 2 — checking balance…" };
        continue;
      }
      const cost = openaiBalance.estimated_cost_per_generation_usd;
      const insufficientBalance = openaiBalance.balance_usd < cost;
      extras[model.id] = {
        note: `$${cost.toFixed(2)}/generation — Estimated balance: $${openaiBalance.balance_usd.toFixed(2)}${
          insufficientBalance ? " (too low)" : ""
        }`,
        disabled: insufficientBalance,
      };
    }
    return extras;
  }, [models, openaiBalance]);

  return (
    <div className="script-preview-page">
      {onReroll && (
        <div className="script-preview-page__toolbar">
          <button
            type="button"
            className="icon-button"
            onClick={onReroll}
            disabled={loading}
            aria-label="Reroll a random script"
            title="Reroll a random script"
          >
            <DiceIcon />
          </button>
        </div>
      )}

      {referenceImage && (
        <div className="script-preview-page__reference">
          <img
            src={referenceImage}
            alt="Reference image"
            className="script-preview-page__reference-image"
          />
          <div className="script-preview-page__denoise">
            <label htmlFor="denoise-slider">
              Transformation strength: {denoiseStrength.toFixed(2)}
            </label>
            <input
              id="denoise-slider"
              type="range"
              min={0.1}
              max={1}
              step={0.05}
              value={denoiseStrength}
              disabled={loading}
              onChange={(event) => onDenoiseChange(Number(event.target.value))}
            />
          </div>
        </div>
      )}

      <p
        className="script-preview-page__script script-preview-page__script--hero"
        onMouseMove={trackSpotlight}
      >
        {scriptResult.script}
      </p>

      {scriptResult.answers ? (
        <ul className="answer-field-list">
          {questions.map((question) => {
            const answer = scriptResult.answers?.[question.key];
            if (!answer) return null;
            return (
              <AnswerFieldEditor
                key={question.key}
                question={question}
                answer={answer}
                disabled={loading}
                onChange={(input) => onAnswerFieldChange(question.key, input)}
              />
            );
          })}
        </ul>
      ) : (
        <FreePromptEditor
          initialText={freePromptText}
          loading={loading}
          onSubmit={onFreePromptSubmit}
        />
      )}

      {showModelSelector && (
        <>
          <p className="script-preview-page__section-label">Model</p>
          <ModelSelector
            models={models}
            selectedIds={selectedModelIds}
            onToggle={onToggleModel}
            disabled={loading}
            modelExtras={modelExtras}
          />
        </>
      )}

      {modelsFiltered && (
        <p className="script-preview-page__models-filtered-note">
          Flux schnell isn't available with a reference image.
        </p>
      )}

      <div className="script-preview-page__actions">
        <button
          type="button"
          className="btn btn--primary"
          onClick={onConfirm}
          disabled={!canGenerate || loading}
        >
          {canGenerate
            ? `Generate ${totalImages} image${totalImages > 1 ? "s" : ""} (${formatDuration(totalSeconds)}${
                totalCost > 0 ? `, + $${totalCost.toFixed(2)} OpenAI` : ""
              })`
            : "Choose at least one model"}
        </button>
      </div>
    </div>
  );
}
