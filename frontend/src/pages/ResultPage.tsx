import { ErrorBanner } from "../components/ErrorBanner";
import { Loader } from "../components/Loader";
import type { ApiError, GenerateResponse } from "../types";

interface ResultPageProps {
  generateResult: GenerateResponse | null;
  loading: boolean;
  error: ApiError | null;
  script: string;
  onRegenerate: () => void;
  onRestart: () => void;
}

export function ResultPage({
  generateResult,
  loading,
  error,
  script,
  onRegenerate,
  onRestart,
}: ResultPageProps) {
  return (
    <div className="result-page">
      <h2>Résultat</h2>
      <p className="result-page__script">{script}</p>

      {loading && <Loader label="Génération en cours… (peut prendre plusieurs minutes sur Mac mini M4)" />}

      {!loading && error && <ErrorBanner error={error} />}

      {!loading && !error && generateResult && (
        <img
          className="result-page__image"
          src={generateResult.image_base64}
          alt={script}
        />
      )}

      {!loading && (
        <div className="result-page__actions">
          <button type="button" onClick={onRegenerate}>
            Régénérer
          </button>
          <button type="button" onClick={onRestart}>
            Nouveau
          </button>
        </div>
      )}
    </div>
  );
}
