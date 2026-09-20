import { useRef } from "react";
import { ImageReferenceUploader } from "../components/ImageReferenceUploader";
import { ModelSelector } from "../components/ModelSelector";
import { ErrorBanner } from "../components/ErrorBanner";
import { QuestionCard } from "../components/QuestionCard";
import { PromptPreview } from "../components/PromptPreview";
import { AnswerFieldEditor } from "../components/AnswerFieldEditor";
import { ArrowLeftIcon, AssistantIcon, CloseIcon, FreePromptIcon } from "../components/icons";
import { useBatchComposer, type BatchDraftItem } from "../state/useBatchComposer";
import { estimateTotalImages } from "../utils/estimate";

interface BatchComposerPageProps {
  onLaunched: () => void;
}

const RESOLVE_DEBOUNCE_MS = 400;

function itemImageCount(item: BatchDraftItem): number {
  return estimateTotalImages(item.models.filter((model) => item.modelIds.includes(model.id)));
}

export function BatchComposerPage({ onLaunched }: BatchComposerPageProps) {
  const {
    items,
    questions,
    addItem,
    removeItem,
    removingIds,
    updateItem,
    setItemMode,
    resolveModelsForItem,
    submitAssistantAnswer,
    updateAssistantAnswerField,
    goToPreviousAssistantQuestion,
    resetAssistant,
    toggleItemModel,
    canLaunch,
    launching,
    error,
    launchBatch,
  } = useBatchComposer();

  // Évite un appel /api/script à chaque frappe : le texte s'affiche tout de
  // suite (updateItem), la résolution du style/modèle attend une pause.
  const debounceTimers = useRef<Record<string, number>>({});

  function handleScriptChange(itemId: string, script: string) {
    updateItem(itemId, { script });
    window.clearTimeout(debounceTimers.current[itemId]);
    debounceTimers.current[itemId] = window.setTimeout(() => {
      resolveModelsForItem(itemId, script);
    }, RESOLVE_DEBOUNCE_MS);
  }

  async function handleLaunch() {
    const batchId = await launchBatch();
    if (batchId) onLaunched();
  }

  const totalImages = items.reduce((sum, item) => sum + itemImageCount(item), 0);

  return (
    <div className="batch-composer-page">
      <h2>Create a batch</h2>
      <p className="batch-composer-page__intro">
        Compose a list of images to generate in sequence. The batch runs server-side: you can
        close this tab, it keeps going in the background — find the results in History.
      </p>

      {error && <ErrorBanner error={error} />}

      <ul className="batch-composer-page__items">
        {items.map((item, index) => (
          <li
            className={`batch-composer-page__item${
              removingIds.has(item.id) ? " batch-composer-page__item--leaving" : ""
            }`}
            key={item.id}
          >
            <div className="batch-composer-page__item-header">
              <h3>Item {index + 1}</h3>
              {items.length > 1 && (
                <button
                  type="button"
                  className="icon-button"
                  onClick={() => removeItem(item.id)}
                  aria-label="Remove this item"
                  title="Remove this item"
                >
                  <CloseIcon />
                </button>
              )}
            </div>

            <div className="batch-composer-page__mode-toggle" role="group" aria-label="Input mode">
              <button
                type="button"
                className={`batch-composer-page__mode-button${
                  item.inputMode === "free_text" ? " batch-composer-page__mode-button--active" : ""
                }`}
                onClick={() => setItemMode(item.id, "free_text")}
                aria-pressed={item.inputMode === "free_text"}
              >
                <FreePromptIcon />
                Free text
              </button>
              <button
                type="button"
                className={`batch-composer-page__mode-button${
                  item.inputMode === "assistant" ? " batch-composer-page__mode-button--active" : ""
                }`}
                onClick={() => setItemMode(item.id, "assistant")}
                disabled={questions.length === 0}
                aria-pressed={item.inputMode === "assistant"}
              >
                <AssistantIcon />
                Assistant
              </button>
            </div>

            {item.inputMode === "free_text" && (
              <textarea
                value={item.script}
                onChange={(event) => handleScriptChange(item.id, event.target.value)}
                placeholder="Describe the image to generate…"
                rows={3}
                aria-label={`Prompt for item ${index + 1}`}
              />
            )}

            {item.inputMode === "assistant" && !item.assistantComplete && questions[item.assistantQuestionIndex] && (
              <div className="batch-composer-page__assistant">
                <div className="batch-composer-page__assistant-header">
                  <p className="batch-composer-page__assistant-progress">
                    Question {item.assistantQuestionIndex + 1} / {questions.length}
                  </p>
                  {item.assistantQuestionIndex > 0 && (
                    <button
                      type="button"
                      className="icon-button"
                      onClick={() => goToPreviousAssistantQuestion(item.id)}
                      aria-label="Previous question"
                      title="Previous question"
                    >
                      <ArrowLeftIcon />
                    </button>
                  )}
                </div>
                <PromptPreview questions={questions} answers={item.assistantAnswers} />
                <QuestionCard
                  question={questions[item.assistantQuestionIndex]}
                  onAnswer={(input) => submitAssistantAnswer(item.id, input)}
                />
              </div>
            )}

            {item.inputMode === "assistant" && item.assistantComplete && (
              <div className="batch-composer-page__assistant-result">
                <p className="batch-composer-page__assistant-script">{item.script}</p>
                {item.resolvedAnswers && (
                  <ul className="answer-field-list">
                    {questions.map((question) => {
                      const answer = item.resolvedAnswers?.[question.key];
                      if (!answer) return null;
                      return (
                        <AnswerFieldEditor
                          key={question.key}
                          question={question}
                          answer={answer}
                          onChange={(input) => updateAssistantAnswerField(item.id, question.key, input)}
                        />
                      );
                    })}
                  </ul>
                )}
                <button
                  type="button"
                  className="batch-composer-page__assistant-restart"
                  onClick={() => resetAssistant(item.id)}
                >
                  Restart the questionnaire
                </button>
              </div>
            )}

            {item.models.length > 0 && (
              <ModelSelector
                models={item.models}
                selectedIds={item.modelIds}
                onToggle={(modelId) => toggleItemModel(item.id, modelId)}
              />
            )}
            {item.models.length === 1 && (
              <p className="batch-composer-page__auto-model">
                Model selected automatically: {item.models[0].label}
              </p>
            )}

            <ImageReferenceUploader
              value={item.referenceImage}
              onChange={(referenceImage) => updateItem(item.id, { referenceImage })}
            />

            {item.referenceImage && (
              <div className="batch-composer-page__denoise">
                <label htmlFor={`denoise-${item.id}`}>
                  Transformation strength: {item.denoiseStrength.toFixed(2)}
                </label>
                <input
                  id={`denoise-${item.id}`}
                  type="range"
                  min={0.1}
                  max={1}
                  step={0.05}
                  value={item.denoiseStrength}
                  onChange={(event) =>
                    updateItem(item.id, { denoiseStrength: Number(event.target.value) })
                  }
                />
              </div>
            )}
          </li>
        ))}
      </ul>

      <div className="batch-composer-page__actions">
        <button type="button" onClick={addItem} disabled={launching}>
          Add an item
        </button>
        <button
          type="button"
          className="batch-composer-page__launch"
          onClick={handleLaunch}
          disabled={!canLaunch || launching}
        >
          {launching
            ? "Launching…"
            : `Launch batch (${totalImages} image${totalImages > 1 ? "s" : ""})`}
        </button>
      </div>
    </div>
  );
}
