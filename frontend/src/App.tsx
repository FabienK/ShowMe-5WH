import { ErrorBanner } from "./components/ErrorBanner";
import { HomePage } from "./pages/HomePage";
import { QuestionPage } from "./pages/QuestionPage";
import { ScriptPreviewPage } from "./pages/ScriptPreviewPage";
import { ResultPage } from "./pages/ResultPage";
import { useGenerationFlow } from "./state/useGenerationFlow";

function App() {
  const flow = useGenerationFlow();

  return (
    <main className="app">
      {flow.step !== "result" && flow.error && <ErrorBanner error={flow.error} />}

      {flow.step === "home" && (
        <HomePage
          comfyReachable={flow.comfyReachable}
          loading={flow.loading}
          onFreePrompt={flow.chooseFreePrompt}
          onGlobalRandom={flow.chooseGlobalRandom}
          onPerQuestion={flow.chooseAnswerQuestionByQuestion}
        />
      )}

      {flow.step === "question" && (
        <QuestionPage
          questions={flow.questions}
          currentQuestionIndex={flow.currentQuestionIndex}
          loading={flow.loading}
          onAnswer={flow.submitAnswerForCurrentQuestion}
          onBack={flow.goToPreviousQuestion}
        />
      )}

      {flow.step === "preview" && flow.scriptResult && (
        <ScriptPreviewPage
          scriptResult={flow.scriptResult}
          loading={flow.loading}
          onModify={
            flow.scriptResult.mode === "per_question"
              ? flow.chooseAnswerQuestionByQuestion
              : undefined
          }
          onConfirm={flow.confirmAndGenerate}
        />
      )}

      {flow.step === "result" && (
        <ResultPage
          generateResult={flow.generateResult}
          loading={flow.loading}
          error={flow.error}
          script={flow.scriptResult?.script ?? ""}
          onRegenerate={flow.regenerate}
          onRestart={flow.restart}
        />
      )}
    </main>
  );
}

export default App;
