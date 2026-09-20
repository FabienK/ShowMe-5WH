import { useState } from "react";
import type { AnswerInput, QuestionDefinition, ResolvedAnswer } from "../types";
import { OptionList } from "./OptionList";
import { DiceIcon, FreePromptIcon, ListIcon } from "./icons";

interface AnswerFieldEditorProps {
  question: QuestionDefinition;
  answer: ResolvedAnswer;
  onChange: (input: AnswerInput) => void;
  disabled?: boolean;
}

type Panel = "none" | "custom" | "list";

function shortLabel(label: string): string {
  return label.split(" — ")[0];
}

export function AnswerFieldEditor({
  question,
  answer,
  onChange,
  disabled,
}: AnswerFieldEditorProps) {
  const [panel, setPanel] = useState<Panel>("none");
  const [customText, setCustomText] = useState("");

  function togglePanel(next: Panel) {
    setPanel((current) => (current === next ? "none" : next));
  }

  function handleCustomSubmit(event: React.FormEvent) {
    event.preventDefault();
    const text = customText.trim();
    if (!text) return;
    onChange({ source: "free_text", text });
    setCustomText("");
    setPanel("none");
  }

  function handleListSelect(index: number) {
    setPanel("none");
    onChange({ source: "list", index });
  }

  function handleRandom() {
    setPanel("none");
    onChange({ source: "random" });
  }

  return (
    <li className="answer-field">
      <div className="answer-field__row">
        <span className="answer-field__label" title={question.label}>
          {shortLabel(question.label)}
        </span>
        <span className="answer-field__value">{answer.text}</span>
        <span className="answer-field__icons">
          <button
            type="button"
            className={`icon-button${panel === "custom" ? " icon-button--active" : ""}`}
            onClick={() => togglePanel("custom")}
            disabled={disabled}
            aria-label={`${question.label} — free answer`}
            title="Free entry"
          >
            <FreePromptIcon />
          </button>
          <button
            type="button"
            className={`icon-button${panel === "list" ? " icon-button--active" : ""}`}
            onClick={() => togglePanel("list")}
            disabled={disabled}
            aria-label={`${question.label} — choose from the list`}
            title="Choose from the list"
          >
            <ListIcon />
          </button>
          <button
            type="button"
            className="icon-button"
            onClick={handleRandom}
            disabled={disabled}
            aria-label={`${question.label} — random`}
            title="Random"
          >
            <DiceIcon />
          </button>
        </span>
      </div>

      {panel === "custom" && (
        <form className="answer-field__custom" onSubmit={handleCustomSubmit}>
          <input
            type="text"
            value={customText}
            onChange={(event) => setCustomText(event.target.value)}
            disabled={disabled}
            aria-label={`${question.label} — free answer`}
            placeholder="Your own answer…"
            autoFocus
          />
          <button
            type="submit"
            className="btn btn--accent2 btn--sm"
            disabled={disabled || !customText.trim()}
          >
            Confirm
          </button>
        </form>
      )}

      {panel === "list" && (
        <OptionList options={question.options} onSelect={handleListSelect} disabled={disabled} />
      )}
    </li>
  );
}
