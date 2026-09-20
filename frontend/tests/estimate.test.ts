import { describe, expect, it } from "vitest";
import { estimateTotalCost, imagesPerModel } from "../src/utils/estimate";
import type { ModelOption, OpenAIState } from "../src/types";

function makeModel(overrides: Partial<ModelOption>): ModelOption {
  return {
    id: "model-1",
    label: "Modèle",
    version: "v1",
    estimated_time: "~20s",
    description: "",
    engine_type: "sd_checkpoint",
    checkpoint: "checkpoint.safetensors",
    lora: null,
    sampler: "euler",
    scheduler: "normal",
    steps: 20,
    cfg: 7,
    width: 512,
    height: 512,
    negative_prompt: "",
    ...overrides,
  };
}

const OPENAI_STATE: OpenAIState = {
  balance_usd: 5,
  price_per_text_input_token_usd: 0.000005,
  price_per_image_input_token_usd: 0.000008,
  price_per_cached_image_input_token_usd: 0.000002,
  price_per_output_token_usd: 0.00003,
  estimated_cost_per_generation_usd: 0.03,
};

describe("imagesPerModel", () => {
  it("returns 1 for openai — must not silently double the real API spend", () => {
    expect(imagesPerModel(makeModel({ engine_type: "openai" }))).toBe(1);
  });

  it("still returns 2 for a plain sd_checkpoint model", () => {
    expect(imagesPerModel(makeModel({ engine_type: "sd_checkpoint" }))).toBe(2);
  });
});

describe("estimateTotalCost", () => {
  it("is 0 when no OpenAI model is selected", () => {
    const models = [makeModel({ engine_type: "sd_checkpoint" })];
    expect(estimateTotalCost(models, OPENAI_STATE)).toBe(0);
  });

  it("is 0 when the OpenAI balance hasn't loaded yet", () => {
    const models = [makeModel({ engine_type: "openai" })];
    expect(estimateTotalCost(models, null)).toBe(0);
  });

  it("sums the estimated per-generation cost for selected OpenAI models", () => {
    const models = [makeModel({ id: "openai-1", engine_type: "openai" })];
    expect(estimateTotalCost(models, OPENAI_STATE)).toBeCloseTo(0.03);
  });
});
