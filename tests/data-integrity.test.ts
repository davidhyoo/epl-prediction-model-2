import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import type { Match, Team, ModelInfo, Summary, Rankings, Bracket } from "@/lib/types";

const DATA = path.join(process.cwd(), "public", "data");
const read = <T>(file: string): T =>
  JSON.parse(readFileSync(path.join(DATA, file), "utf-8")) as T;

const matches = read<Match[]>("matches.json");
const teams = read<Team[]>("teams.json");
const models = read<ModelInfo[]>("models.json");
const summary = read<Summary>("summary.json");
const rankings = read<Rankings>("rankings.json");
const bracket = read<Bracket>("bracket.json");

const sumsToOne = (a: number, b: number, c: number, tol = 0.02) =>
  Math.abs(a + b + c - 1) < tol;

describe("matches.json", () => {
  it("contains the full 104-match schedule", () => {
    expect(matches).toHaveLength(104);
  });

  it("gives every match a full slate of model probabilities that sum to 1", () => {
    for (const m of matches) {
      expect(m.models.length).toBeGreaterThanOrEqual(5);
      for (const mp of m.models) {
        expect(sumsToOne(mp.probs.home, mp.probs.draw, mp.probs.away)).toBe(true);
      }
      expect(sumsToOne(m.ensemble.probs.home, m.ensemble.probs.draw, m.ensemble.probs.away)).toBe(
        true,
      );
    }
  });

  it("never leaks results: upcoming matches carry no score, completed matches do", () => {
    for (const m of matches) {
      if (m.status === "upcoming") {
        expect(m.score).toBeNull();
      }
      if (m.status === "completed") {
        expect(m.score).not.toBeNull();
      }
    }
  });

  it("still produces a prediction for every upcoming match", () => {
    const upcoming = matches.filter((m) => m.status === "upcoming");
    expect(upcoming.length).toBeGreaterThan(0);
    for (const m of upcoming) {
      expect(m.ensemble.confidence).toBeGreaterThan(0);
    }
  });
});

describe("teams.json", () => {
  it("lists all 48 qualified nations", () => {
    expect(teams).toHaveLength(48);
  });

  it("keeps championship probabilities in [0, 1] and summing to ~1", () => {
    let total = 0;
    for (const t of teams) {
      expect(t.championProb).toBeGreaterThanOrEqual(0);
      expect(t.championProb).toBeLessThanOrEqual(1);
      total += t.championProb;
    }
    expect(Math.abs(total - 1)).toBeLessThan(0.02);
  });

  it("pins eliminated teams to a 0% title chance", () => {
    const eliminated = teams.filter((t) => t.status === "eliminated");
    expect(eliminated.length).toBeGreaterThan(0);
    for (const t of eliminated) {
      expect(t.championProb).toBe(0);
    }
  });
});

describe("models.json", () => {
  it("evaluates five models on completed matches only", () => {
    expect(models).toHaveLength(5);
    for (const m of models) {
      expect(m.gamesEvaluated).toBeGreaterThan(0);
      expect(Number.isFinite(m.logLoss)).toBe(true);
      expect(Number.isFinite(m.brier)).toBe(true);
      expect(m.accuracy).toBeGreaterThanOrEqual(0);
      expect(m.accuracy).toBeLessThanOrEqual(1);
    }
  });

  it("distributes ensemble weight across the base models (~1 total)", () => {
    const base = models.filter((m) => m.type !== "ensemble");
    const total = base.reduce((s, m) => s + m.weight, 0);
    expect(Math.abs(total - 1)).toBeLessThan(0.02);
  });

  it("assigns a unique rank to each model", () => {
    const ranks = models.map((m) => m.rank).sort((a, b) => a - b);
    expect(ranks).toEqual([1, 2, 3, 4, 5]);
  });

  it("keeps calibration bins within [0, 1]", () => {
    for (const m of models) {
      for (const bin of m.calibration) {
        expect(bin.predicted).toBeGreaterThanOrEqual(0);
        expect(bin.predicted).toBeLessThanOrEqual(1);
        expect(bin.observed).toBeGreaterThanOrEqual(0);
        expect(bin.observed).toBeLessThanOrEqual(1);
      }
    }
  });
});

describe("summary.json", () => {
  it("reconciles completed + upcoming with the total", () => {
    expect(summary.matchesCompleted + summary.matchesUpcoming + summary.matchesLive).toBe(
      summary.totalMatches,
    );
    expect(summary.totalMatches).toBe(matches.length);
  });

  it("documents the cached real-data mode", () => {
    expect(summary.dataMode).toBe("cached");
  });

  it("names a top champion that exists in the field", () => {
    const codes = new Set(teams.map((t) => t.code));
    expect(codes.has(summary.topChampion.code)).toBe(true);
  });
});

describe("rankings.json + bracket.json", () => {
  it("exposes multiple ranking views, each covering the field", () => {
    expect(rankings.views.length).toBeGreaterThanOrEqual(7);
    for (const v of rankings.views) {
      expect(v.entries.length).toBe(48);
    }
  });

  it("builds a knockout bracket from the round of 32 through the final", () => {
    const stages = bracket.rounds.map((r) => r.stage);
    expect(stages).toContain("round-of-32");
    expect(stages).toContain("final");
  });
});
