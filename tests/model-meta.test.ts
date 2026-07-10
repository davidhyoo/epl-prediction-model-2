import { describe, it, expect } from "vitest";
import { buildModelMeta } from "@/lib/model-meta";
import type { ModelInfo } from "@/lib/types";

function model(id: string, over: Partial<ModelInfo> = {}): ModelInfo {
  return {
    id,
    name: id.toUpperCase(),
    type: "tree",
    description: "",
    accuracy: 0.5,
    logLoss: 1,
    brier: 0.6,
    gamesEvaluated: 72,
    avgConfidence: 0.5,
    ece: 0.1,
    weight: 0.25,
    rank: 1,
    lastUpdated: "2026-07-10T00:00:00Z",
    calibration: [],
    featureImportance: [],
    strengths: "",
    note: null,
    ...over,
  };
}

describe("buildModelMeta", () => {
  it("keys metrics by model id", () => {
    const meta = buildModelMeta([
      model("rf", { logLoss: 0.9, brier: 0.55, ece: 0.08, rank: 1, weight: 0.26 }),
      model("elo", { logLoss: 1.1, brier: 0.62, ece: 0.14, rank: 4, weight: 0.24 }),
    ]);

    expect(Object.keys(meta)).toEqual(["rf", "elo"]);
    expect(meta.rf).toEqual({ logLoss: 0.9, brier: 0.55, ece: 0.08, rank: 1, weight: 0.26 });
    expect(meta.elo.rank).toBe(4);
  });

  it("returns an empty map for no models", () => {
    expect(buildModelMeta([])).toEqual({});
  });

  it("only exposes the compact metric fields", () => {
    const meta = buildModelMeta([model("xgb")]);
    expect(Object.keys(meta.xgb).sort()).toEqual(
      ["brier", "ece", "logLoss", "rank", "weight"].sort(),
    );
  });
});
