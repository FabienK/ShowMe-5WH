import { useState } from "react";
import { ModeSelector } from "../components/ModeSelector";
import { Loader } from "../components/Loader";

interface HomePageProps {
  comfyReachable: boolean | null;
  loading: boolean;
  onFreePrompt: (text: string) => void;
  onGlobalRandom: () => void;
  onPerQuestion: () => void;
}

export function HomePage({
  comfyReachable,
  loading,
  onFreePrompt,
  onGlobalRandom,
  onPerQuestion,
}: HomePageProps) {
  const [showFreePromptInput, setShowFreePromptInput] = useState(false);
  const [freePromptText, setFreePromptText] = useState("");

  const submitFreePrompt = (event: React.FormEvent) => {
    event.preventDefault();
    if (!freePromptText.trim()) return;
    onFreePrompt(freePromptText.trim());
  };

  return (
    <div className="home-page">
      <h1>Générateur d'images 4W1H</h1>
      <p className="home-page__intro">
        Construisez un script de génération d'image en répondant à 5 questions
        (What / Who / Where / When / How), ou écrivez directement votre propre prompt.
      </p>

      {comfyReachable === false && (
        <div className="comfy-warning" role="status">
          ComfyUI n'est pas détecté sur cette machine. Vous pourrez toujours préparer votre
          script, mais la génération d'image échouera tant que ComfyUI n'est pas démarré.
        </div>
      )}

      {loading ? (
        <Loader label="Préparation du script…" />
      ) : showFreePromptInput ? (
        <form className="home-page__free-prompt" onSubmit={submitFreePrompt}>
          <label htmlFor="free-prompt-textarea">Votre prompt complet</label>
          <textarea
            id="free-prompt-textarea"
            value={freePromptText}
            onChange={(event) => setFreePromptText(event.target.value)}
            rows={4}
            placeholder="Ex : un chat cyberpunk dans une ville futuriste, la nuit, plan large…"
          />
          <div className="home-page__free-prompt-actions">
            <button type="button" onClick={() => setShowFreePromptInput(false)}>
              Annuler
            </button>
            <button type="submit" disabled={!freePromptText.trim()}>
              Continuer
            </button>
          </div>
        </form>
      ) : (
        <ModeSelector
          onFreePrompt={() => setShowFreePromptInput(true)}
          onGlobalRandom={onGlobalRandom}
          onPerQuestion={onPerQuestion}
        />
      )}
    </div>
  );
}
