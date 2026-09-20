import type {
  ApiError,
  BatchDetail,
  BatchSummary,
  GenerateRequest,
  GenerateResponse,
  OpenAIState,
  QuestionDefinition,
  ScriptRequest,
  ScriptResponse,
} from "../types";

async function parseError(response: Response): Promise<ApiError> {
  let detail = response.statusText;
  let errorType = "unknown_error";

  try {
    const body = await response.json();
    if (body && typeof body.detail === "object" && body.detail !== null) {
      errorType = body.detail.error_type ?? errorType;
      detail = body.detail.detail ?? detail;
    } else if (typeof body.detail === "string") {
      detail = body.detail;
    } else if (Array.isArray(body.detail)) {
      detail = body.detail.map((item: { msg?: string }) => item.msg).join(" ; ");
    }
  } catch {
    // Réponse non-JSON : on garde le statusText par défaut.
  }

  return { status: response.status, errorType, detail };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as T;
}

export function getQuestions(): Promise<QuestionDefinition[]> {
  return request<{ questions: QuestionDefinition[] }>("/api/questions").then(
    (data) => data.questions,
  );
}

export function getComfyUIStatus(): Promise<boolean> {
  return request<{ reachable: boolean }>("/api/comfyui/status").then(
    (data) => data.reachable,
  );
}

export function postScript(body: ScriptRequest): Promise<ScriptResponse> {
  return request<ScriptResponse>("/api/script", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function postGenerate(body: GenerateRequest): Promise<GenerateResponse> {
  return request<GenerateResponse>("/api/generate", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function postBatch(items: GenerateRequest[]): Promise<{ batch_id: string }> {
  return request<{ batch_id: string }>("/api/batches", {
    method: "POST",
    body: JSON.stringify({ items }),
  });
}

export function getBatches(): Promise<BatchSummary[]> {
  return request<{ batches: BatchSummary[] }>("/api/batches").then((data) => data.batches);
}

export function getBatch(batchId: string): Promise<BatchDetail> {
  return request<BatchDetail>(`/api/batches/${batchId}`);
}

export function getOpenAIBalance(): Promise<OpenAIState> {
  return request<OpenAIState>("/api/openai/balance");
}

export function putOpenAIBalance(balanceUsd: number): Promise<OpenAIState> {
  return request<OpenAIState>("/api/openai/balance", {
    method: "PUT",
    body: JSON.stringify({ balance_usd: balanceUsd }),
  });
}
