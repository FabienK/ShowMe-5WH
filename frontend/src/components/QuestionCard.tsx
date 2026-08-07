import { useState } from "react";
import type { AnswerInput, QuestionDefinition } from "../types";
import { OptionList } from "./OptionList";

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

  return (
    <div className="question-card">
      <h2>{question.label}</h2>

      <OptionList
        options={question.options}
        onSelect={(index) => onAnswer({ source: "list", index })}
        disabled={disabled}
      />

      <form className="question-card__free-text" onSubmit={submitFreeText}>
        <label htmlFor="free-text-input">Ou réponse libre</label>
        <div className="question-card__free-text-row">
          <input
            id="free-text-input"
            type="text"
            value={freeText}
            onChange={(event) => setFreeText(event.target.value)}
            disabled={disabled}
            placeholder="Votre propre réponse…"
          />
          <button type="submit" disabled={disabled || !freeText.trim()}>
            Valider
          </button>
        </div>
      </form>

      <button
        type="button"
        className="question-card__random"
        onClick={() => onAnswer({ source: "random" })}
        disabled={disabled}
      >
        L'app décide pour cette question
      </button>
    </div>
  );
}
