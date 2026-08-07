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

export interface ScriptResponse {
  mode: "free_prompt" | "global_random" | "per_question";
  answers: Record<QuestionKey, ResolvedAnswer> | null;
  script: string;
  style: string | null;
}

export interface GenerateRequest {
  script: string;
  style: string | null;
  seed?: number | null;
}

export interface PresetUsed {
  style: string;
  checkpoint: string;
  lora: string | null;
  sampler: string;
  scheduler: string;
  steps: number;
  cfg: number;
  width: number;
  height: number;
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
