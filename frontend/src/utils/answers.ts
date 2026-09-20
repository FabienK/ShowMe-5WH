import type { AnswerInput, ResolvedAnswer } from "../types";

// Reconstruit un AnswerInput "équivalent" à partir d'une réponse déjà résolue
// par le backend — utilisé quand on ré-envoie les 5 réponses à /api/script
// après avoir modifié une seule d'entre elles.
export function toAnswerInput(resolved: ResolvedAnswer): AnswerInput {
  if (resolved.source === "free_text") {
    return { source: "free_text", text: resolved.text };
  }
  return { source: "list", index: resolved.index ?? 1 };
}
