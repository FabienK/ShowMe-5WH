import { useState } from "react";
import { ErrorBanner } from "./components/ErrorBanner";
import { HomePage } from "./pages/HomePage";
import { QuestionPage } from "./pages/QuestionPage";
import { ScriptPreviewPage } from "./pages/ScriptPreviewPage";
import { ResultPage } from "./pages/ResultPage";
import { BatchComposerPage } from "./pages/BatchComposerPage";
import { HistoryPage } from "./pages/HistoryPage";
import { SettingsPage } from "./pages/SettingsPage";
import { useGenerationFlow } from "./state/useGenerationFlow";
import { ClockIcon, HomeIcon, ListIcon, SettingsIcon } from "./components/icons";

type View = "generator" | "batch" | "history" | "settings";

function App() {
  const flow = useGenerationFlow();
  const [view, setView] = useState<View>("generator");

  return (
    <main className={`app${flow.step === "question" ? " app--wide" : ""}`}>
      <nav className="app__nav">
        <button
          type="button"
          className={`app__nav-item${view === "generator" ? " app__nav-item--active" : ""}`}
          onClick={() => {
            // Déjà sur l'onglet Générateur en plein milieu du flux : un
            // second clic ramène à l'accueil, sans bouton dédié sur chaque
            // page (voir QuestionPage — plus de bouton "Accueil" isolé).
            if (view === "generator" && flow.step !== "home") {
              flow.restart();
            }
            setView("generator");
          }}
          aria-label={view === "generator" && flow.step !== "home" ? "Back to home" : "Generator"}
        >
          <HomeIcon />
          <span className="app__nav-label">Generator</span>
        </button>
        <button
          type="button"
          className={`app__nav-item${view === "batch" ? " app__nav-item--active" : ""}`}
          onClick={() => setView("batch")}
          aria-label="Create a batch"
        >
          <ListIcon />
          <span className="app__nav-label">Create a batch</span>
        </button>
        <button
          type="button"
          className={`app__nav-item${view === "history" ? " app__nav-item--active" : ""}`}
          onClick={() => setView("history")}
          aria-label="History"
        >
          <ClockIcon />
          <span className="app__nav-label">History</span>
        </button>
        <button
          type="button"
          className={`app__nav-item${view === "settings" ? " app__nav-item--active" : ""}`}
          onClick={() => setView("settings")}
          aria-label="Settings"
        >
          <SettingsIcon />
          <span className="app__nav-label">Settings</span>
        </button>
      </nav>

      {view === "batch" && (
        <BatchComposerPage onLaunched={() => setView("history")} />
      )}

      {view === "history" && <HistoryPage />}

      {view === "settings" && <SettingsPage onBalanceUpdated={flow.refreshOpenAIBalance} />}

      {view === "generator" && (
        <>
      {flow.step !== "result" && flow.error && <ErrorBanner error={flow.error} />}

      {flow.step === "home" && (
        <HomePage
          comfyReachable={flow.comfyReachable}
          loading={flow.loading}
          onFreePrompt={flow.chooseFreePrompt}
          onGlobalRandom={flow.chooseGlobalRandom}
          onPerQuestion={flow.chooseAnswerQuestionByQuestion}
          onImageReference={flow.chooseImageReference}
        />
      )}

      {flow.step === "question" && (
        <QuestionPage
          questions={flow.questions}
          currentQuestionIndex={flow.currentQuestionIndex}
          answers={flow.answers}
          loading={flow.loading}
          onAnswer={flow.submitAnswerForCurrentQuestion}
          onBack={flow.goToPreviousQuestion}
        />
      )}

      {flow.step === "preview" && flow.scriptResult && (
        <ScriptPreviewPage
          scriptResult={flow.scriptResult}
          models={flow.availableModels}
          questions={flow.questions}
          freePromptText={flow.freePromptText}
          loading={flow.loading}
          selectedModelIds={flow.selectedModelIds}
          onToggleModel={flow.toggleModelSelection}
          onAnswerFieldChange={flow.updateAnswerField}
          onFreePromptSubmit={flow.chooseFreePrompt}
          onReroll={
            flow.scriptResult.mode === "global_random" ? flow.chooseGlobalRandom : undefined
          }
          onConfirm={flow.confirmAndGenerate}
          referenceImage={flow.referenceImage}
          denoiseStrength={flow.denoiseStrength}
          onDenoiseChange={flow.setDenoiseStrength}
          openaiBalance={flow.openaiBalance}
        />
      )}

      {flow.step === "result" && (
        <ResultPage
          results={flow.results}
          pendingModels={flow.pendingModels}
          loading={flow.loading}
          error={flow.error}
          script={flow.scriptResult?.script ?? ""}
          onRegenerate={flow.regenerate}
          onModify={flow.backToPreview}
          onRestart={flow.restart}
        />
      )}
        </>
      )}
    </main>
  );
}

export default App;
