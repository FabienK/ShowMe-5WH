import { Loader } from "../components/Loader";
import type { ScriptResponse } from "../types";

interface ScriptPreviewPageProps {
  scriptResult: ScriptResponse;
  loading: boolean;
  onModify?: () => void;
  onConfirm: () => void;
}

export function ScriptPreviewPage({
  scriptResult,
  loading,
  onModify,
  onConfirm,
}: ScriptPreviewPageProps) {
  return (
    <div className="script-preview-page">
      <h2>Script assemblé</h2>
      <p className="script-preview-page__script">{scriptResult.script}</p>

      {scriptResult.answers && (
        <ul className="script-preview-page__answers">
          {Object.values(scriptResult.answers).map((answer) => (
            <li key={answer.key}>
              <strong>{answer.key}</strong> : {answer.text}
            </li>
          ))}
        </ul>
      )}

      {loading ? (
        <Loader label="Lancement de la génération…" />
      ) : (
        <div className="script-preview-page__actions">
          {onModify && (
            <button type="button" onClick={onModify}>
              Modifier
            </button>
          )}
          <button type="button" className="script-preview-page__confirm" onClick={onConfirm}>
            Lancer la génération
          </button>
        </div>
      )}
    </div>
  );
}
