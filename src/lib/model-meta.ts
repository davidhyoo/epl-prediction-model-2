import type { ModelEntry } from "./types";

export type ModelMeta = Record<
  string,
  Pick<ModelEntry, "logLoss" | "brier" | "ece" | "rank" | "weight" | "accuracy" | "name" | "blurb">
>;

/** Build a compact lookup of per-model metrics for the prediction modal. */
export function buildModelMeta(models: ModelEntry[]): ModelMeta {
  const map: ModelMeta = {};
  for (const m of models) {
    map[m.id] = {
      name: m.name,
      blurb: m.blurb,
      logLoss: m.logLoss,
      brier: m.brier,
      ece: m.ece,
      rank: m.rank,
      weight: m.weight,
      accuracy: m.accuracy,
    };
  }
  return map;
}
