import type { ModelInfo } from "./types";

export type ModelMeta = Record<
  string,
  Pick<ModelInfo, "logLoss" | "brier" | "ece" | "rank" | "weight">
>;

/** Build a compact lookup of per-model metrics for the prediction modal. */
export function buildModelMeta(models: ModelInfo[]): ModelMeta {
  const map: ModelMeta = {};
  for (const m of models) {
    map[m.id] = { logLoss: m.logLoss, brier: m.brier, ece: m.ece, rank: m.rank, weight: m.weight };
  }
  return map;
}
