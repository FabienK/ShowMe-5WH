import type { ModelOption, OpenAIState } from "../types";

// Flux dev/Kontext (~12 min) ne génèrent qu'une image ; OpenAI (payant, voir
// estimateTotalCost) aussi, pour ne pas doubler silencieusement la dépense
// réelle par clic ; tous les autres modèles en génèrent 2.
export function imagesPerModel(model: ModelOption): number {
  return model.engine_type === "flux" ||
    model.engine_type === "flux_kontext" ||
    model.engine_type === "openai"
    ? 1
    : 2;
}

// Parse "~20s" / "~2 min" / "~2 min 30" -> secondes.
export function parseEstimatedSeconds(estimatedTime: string): number {
  if (!estimatedTime) return 0;

  const secondsMatch = estimatedTime.match(/~(\d+)s/);
  if (secondsMatch) return Number(secondsMatch[1]);

  const minutesMatch = estimatedTime.match(/~(\d+)\s*min(?:\s+(\d+))?/);
  if (minutesMatch) {
    const minutes = Number(minutesMatch[1]);
    const seconds = minutesMatch[2] ? Number(minutesMatch[2]) : 0;
    return minutes * 60 + seconds;
  }

  return 0;
}

export function formatDuration(totalSeconds: number): string {
  if (totalSeconds < 60) return `~${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return seconds > 0 ? `~${minutes} min ${seconds}` : `~${minutes} min`;
}

// File de génération : modèles les plus rapides en premier, chaque modèle
// répété selon imagesPerModel() — permet d'afficher les images au fur et à
// mesure en commençant par les plus rapides.
export function buildGenerationQueue(models: ModelOption[]): ModelOption[] {
  return [...models]
    .sort((a, b) => parseEstimatedSeconds(a.estimated_time) - parseEstimatedSeconds(b.estimated_time))
    .flatMap((model) => Array.from({ length: imagesPerModel(model) }, () => model));
}

export function estimateTotalImages(models: ModelOption[]): number {
  return models.reduce((total, model) => total + imagesPerModel(model), 0);
}

export function estimateTotalSeconds(models: ModelOption[]): number {
  return models.reduce(
    (total, model) => total + imagesPerModel(model) * parseEstimatedSeconds(model.estimated_time),
    0,
  );
}

// Coût OpenAI estimé pour la sélection courante ; 0 si aucun modèle OpenAI
// sélectionné (les modèles locaux n'ont pas de coût). Le coût réel décrémenté
// après génération vient toujours des tokens effectivement consommés (voir
// backend/app/services/openai_generator.py) — cette estimation ne sert qu'à
// l'affichage avant l'appel.
export function estimateTotalCost(models: ModelOption[], openaiState: OpenAIState | null): number {
  if (!openaiState) return 0;
  return models.reduce(
    (total, model) =>
      model.engine_type === "openai"
        ? total + imagesPerModel(model) * openaiState.estimated_cost_per_generation_usd
        : total,
    0,
  );
}
