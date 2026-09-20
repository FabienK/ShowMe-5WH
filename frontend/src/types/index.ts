export type QuestionKey = "what" | "who" | "where" | "when" | "how";

export interface QuestionDefinition {
  key: QuestionKey;
  label: string;
  options: string[];
}

export type AnswerInput =
  | { source: "list"; index: number }
  | { source: "free_text"; text: string }
  | { source: "random" };

export interface ResolvedAnswer {
  key: QuestionKey;
  label: string;
  source: "list" | "free_text" | "random";
  index: number | null;
  text: string;
}

export type ScriptRequest =
  | { mode: "free_prompt"; prompt: string }
  | { mode: "global_random" }
  | { mode: "per_question"; answers: Record<QuestionKey, AnswerInput> };

export type EngineType =
  | "sd_checkpoint"
  | "flux"
  | "anima"
  | "flux_schnell"
  | "flux_kontext"
  | "openai";

export interface ModelOption {
  id: string;
  label: string;
  version: string;
  estimated_time: string;
  description: string;
  engine_type: EngineType;
  checkpoint: string | null;
  lora: string | null;
  sampler: string;
  scheduler: string;
  steps: number;
  cfg: number;
  width: number;
  height: number;
  negative_prompt: string;
}

export interface ScriptResponse {
  mode: "free_prompt" | "global_random" | "per_question";
  answers: Record<QuestionKey, ResolvedAnswer> | null;
  script: string;
  style: string | null;
  models: ModelOption[];
}

export interface GenerateRequest {
  script: string;
  style: string | null;
  seed?: number | null;
  model_id?: string | null;
  reference_image?: string | null;
  denoise_strength?: number | null;
}

export interface PresetUsed {
  style: string;
  model_id: string;
  model_label: string;
  model_version: string;
  estimated_time: string;
  checkpoint: string;
  lora: string | null;
  sampler: string;
  scheduler: string;
  steps: number;
  cfg: number;
  width: number;
  height: number;
  denoise_strength: number | null;
}

export interface GenerateResponse {
  status: "success";
  image_base64: string;
  prompt_id: string;
  seed_used: number;
  preset_used: PresetUsed;
}

export interface ApiError {
  status: number;
  errorType: string;
  detail: string;
}

export type BatchItemStatus = "pending" | "running" | "success" | "error";
export type BatchStatus = "running" | "completed" | "interrupted";

export interface BatchItemResult {
  index: number;
  request: GenerateRequest;
  status: BatchItemStatus;
  image_path: string | null;
  prompt_id: string | null;
  seed_used: number | null;
  preset_used: PresetUsed | null;
  error_type: string | null;
  error_detail: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface BatchSummary {
  batch_id: string;
  status: BatchStatus;
  created_at: string;
  total_items: number;
  completed_items: number;
  error_items: number;
}

export interface BatchDetail {
  batch_id: string;
  status: BatchStatus;
  created_at: string;
  items: BatchItemResult[];
}

export interface OpenAIState {
  balance_usd: number;
  price_per_text_input_token_usd: number;
  price_per_image_input_token_usd: number;
  price_per_cached_image_input_token_usd: number;
  price_per_output_token_usd: number;
  estimated_cost_per_generation_usd: number;
}
