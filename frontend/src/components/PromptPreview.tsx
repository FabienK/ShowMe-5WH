import type { AnswerInput, QuestionDefinition, QuestionKey } from "../types";

type PromptPreviewItem =
  | { key: QuestionKey; kind: "text"; text: string }
  | { key: QuestionKey; kind: "pending" };

function buildPromptPreview(
  questions: QuestionDefinition[],
  answers: Partial<Record<QuestionKey, AnswerInput>>,
): PromptPreviewItem[] {
  return questions.map((question) => {
    const input = answers[question.key];
    if (input?.source === "free_text") return { key: question.key, kind: "text", text: input.text };
    if (input?.source === "list") {
      const text = question.options[input.index - 1];
      if (text) return { key: question.key, kind: "text", text };
    }
    return { key: question.key, kind: "pending" };
  });
}

interface PromptPreviewProps {
  questions: QuestionDefinition[];
  answers: Partial<Record<QuestionKey, AnswerInput>>;
}

// Aperçu du prompt qui se construit au fil des réponses — un chip par
// question, "…" tant qu'elle n'est pas encore répondue. Utilisé par le
// questionnaire "Assistant", que ce soit dans le flux "Générateur"
// (QuestionPage) ou dans un item du composeur de batch.
export function PromptPreview({ questions, answers }: PromptPreviewProps) {
  const preview = buildPromptPreview(questions, answers);

  return (
    <div className="prompt-preview">
      <span className="prompt-preview__label">Prompt</span>
      <div className="prompt-preview__chips">
        {preview.map((item) => (
          <span key={item.key} className={`prompt-chip prompt-chip--${item.kind}`}>
            {item.kind === "text" ? item.text : "…"}
          </span>
        ))}
      </div>
    </div>
  );
}
