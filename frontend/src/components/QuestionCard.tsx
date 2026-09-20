import { useState } from "react";
import type { AnswerInput, QuestionDefinition } from "../types";
import { OptionList } from "./OptionList";
import { DiceIcon, FreePromptIcon } from "./icons";
import { trackSpotlight } from "../utils/spotlight";

interface QuestionCardProps {
  question: QuestionDefinition;
  onAnswer: (input: AnswerInput) => void;
  disabled?: boolean;
}

export function QuestionCard({ question, onAnswer, disabled }: QuestionCardProps) {
  const [freeText, setFreeText] = useState("");

  const submitFreeText = (event: React.FormEvent) => {
    event.preventDefault();
    if (!freeText.trim()) return;
    onAnswer({ source: "free_text", text: freeText.trim() });
    setFreeText("");
  };

  const chooseRandom = () => {
    const randomIndex = Math.floor(Math.random() * question.options.length) + 1;
    onAnswer({ source: "list", index: randomIndex });
  };

  return (
    <div className="question-card card" onMouseMove={trackSpotlight}>
      <h2>{question.label}</h2>

      <OptionList
        options={question.options}
        onSelect={(index) => onAnswer({ source: "list", index })}
        disabled={disabled}
      />

      <div className="question-card__footer">
        <form className="question-card__free-text" onSubmit={submitFreeText}>
          <span
            className="question-card__free-text-icon"
            aria-hidden="true"
            title="Free answer"
          >
            <FreePromptIcon />
          </span>
          <input
            id="free-text-input"
            type="text"
            aria-label="Free answer"
            value={freeText}
            onChange={(event) => setFreeText(event.target.value)}
            disabled={disabled}
            placeholder="Your own answer…"
          />
          <button
            type="submit"
            className="btn btn--accent2 btn--sm"
            disabled={disabled || !freeText.trim()}
          >
            Confirm
          </button>
        </form>

        <button
          type="button"
          className="icon-button question-card__random"
          onClick={chooseRandom}
          disabled={disabled}
          aria-label="Let the app decide for this question"
          title="Let the app decide for this question"
        >
          <DiceIcon />
        </button>
      </div>
    </div>
  );
}
