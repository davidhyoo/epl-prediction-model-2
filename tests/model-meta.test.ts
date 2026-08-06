import { describe, it, expect } from "vitest";
import { buildModelMeta } from "@/lib/model-meta";
import type { ModelEntry } from "@/lib/types";

function model(id: string, over: Partial<ModelEntry> = {}): ModelEntry {
  return {
    id,
    name: id.toUpperCase(),
    blurb: "",
    weight: 0.25,
    accuracy: 0.5,
    logLoss: 1,
    brier: 0.6,
    avgConfidence: 0.5,
    ece: 0.1,
    calibration: [],
    gamesEvaluated: 380,
    rank: 1,
    ...over,
  };
}

describe("buildModelMeta", () => {
  it("keys the compact metric fields by model id", () => {
    const meta = buildModelMeta([
      model("forest", { name: "Random Forest", logLoss: 0.9, brier: 0.55, ece: 0.08, rank: 1, weight: 0.26 }),
      model("elo", { name: "Elo Baseline", logLoss: 1.1, brier: 0.62, ece: 0.14, rank: 4, weight: 0.24 }),
    ]);

    expect(Object.keys(meta)).toEqual(["forest", "elo"]);
    expect(meta.forest.name).toBe("Random Forest");
    expect(meta.forest.logLoss).toBe(0.9);
    expect(meta.forest.rank).toBe(1);
    expect(meta.elo.rank).toBe(4);
  });

  it("returns an empty map for no models", () => {
    expect(buildModelMeta([])).toEqual({});
  });

  it("exposes name, blurb, accuracy and the calibration metrics", () => {
    const meta = buildModelMeta([model("xgb")]);
    expect(Object.keys(meta.xgb).sort()).toEqual(
      ["accuracy", "blurb", "brier", "ece", "logLoss", "name", "rank", "weight"].sort(),
    );
  });

  it("preserves null metrics for an unevaluated (pre-season) model", () => {
    const meta = buildModelMeta([
      model("ensemble", { accuracy: null, logLoss: null, brier: null, ece: null, gamesEvaluated: 0 }),
    ]);
    expect(meta.ensemble.accuracy).toBeNull();
    expect(meta.ensemble.logLoss).toBeNull();
  });
});
