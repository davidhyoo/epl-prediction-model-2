import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import type { Match, Team, ModelInfo, Summary, Rankings, Bracket, Player } from "@/lib/types";

const DATA = path.join(process.cwd(), "public", "data");
const read = <T>(file: string): T =>
  JSON.parse(readFileSync(path.join(DATA, file), "utf-8")) as T;

const matches = read<Match[]>("matches.json");
const teams = read<Team[]>("teams.json");
const models = read<ModelInfo[]>("models.json");
const summary = read<Summary>("summary.json");
const rankings = read<Rankings>("rankings.json");
const bracket = read<Bracket>("bracket.json");
const players = read<Player[]>("players.json");

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

  it("produces a full prediction for every match", () => {
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.ensemble.confidence).toBeGreaterThan(0);
    }
  });

  it("records the advancing side for knockout ties settled after 90 minutes", () => {
    const decidedLate = matches.filter(
      (m) => m.status === "completed" && (m.aet || m.penalties !== null),
    );
    // A deep, completed tournament always has at least one extra-time/penalty tie.
    expect(decidedLate.length).toBeGreaterThan(0);
    for (const m of decidedLate) {
      expect(m.resultWinner === "home" || m.resultWinner === "away").toBe(true);
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

describe("players.json", () => {
  it("carries the full 1,248-strong field of real squads", () => {
    expect(players).toHaveLength(1248);
    const real = players.filter((p) => p.real).length;
    expect(real).toBeGreaterThan(1248 * 0.9);
  });

  it("attaches free-licensed headshots to most players, with attribution", () => {
    const withPhoto = players.filter((p) => p.headshot);
    expect(withPhoto.length).toBeGreaterThan(800);
    for (const p of withPhoto) {
      expect(p.headshot).toMatch(/^\/headshots\/[A-Z]{3}-\d{2}\.jpg$/);
      expect(p.photoCredit?.author).toBeTruthy();
      expect(p.photoCredit?.license).toBeTruthy();
      expect(p.photoCredit?.sourceUrl).toMatch(/^https?:\/\//);
    }
  });

  it("keeps model-generated ratings in a sane, spread-out range", () => {
    for (const p of players) {
      expect(p.rating).toBeGreaterThanOrEqual(50);
      expect(p.rating).toBeLessThanOrEqual(95);
    }
    const distinct = new Set(players.map((p) => p.rating)).size;
    expect(distinct).toBeGreaterThan(50); // not all clamped to a single ceiling value
  });

  it("uses real, non-fabricated tournament stats", () => {
    let totalGoals = 0;
    let maxGoals = 0;
    for (const p of players) {
      const s = p.stats;
      expect(s.appearances).toBeGreaterThanOrEqual(0);
      expect(s.minutes).toBeGreaterThanOrEqual(0);
      expect(s.goals).toBeGreaterThanOrEqual(0);
      expect(s.yellowCards).toBeGreaterThanOrEqual(0);
      expect(s.redCards).toBeGreaterThanOrEqual(0);
      // Assists are not published in any free World Cup source — never fabricated.
      expect(s.assists).toBeNull();
      // Minutes can never exceed appearances × the longest match (120' with extra time).
      expect(s.minutes).toBeLessThanOrEqual(s.appearances * 120);
      if (p.position === "GK") {
        expect(typeof s.goalsConceded).toBe("number");
      } else {
        // Goalkeeping-only stats are null for outfield players.
        expect(s.cleanSheets).toBeNull();
        expect(s.goalsConceded).toBeNull();
      }
      totalGoals += s.goals;
      maxGoals = Math.max(maxGoals, s.goals);
    }
    // A real, deep-into-the-knockouts World Cup has a lot of goals and a clear
    // golden-boot leader — a sanity check that we joined real data, not zeros.
    expect(totalGoals).toBeGreaterThan(100);
    expect(maxGoals).toBeGreaterThanOrEqual(5);
    expect(players.some((p) => p.position === "GK" && (p.stats.cleanSheets ?? 0) > 0)).toBe(true);
  });

  it("attaches a real per-match log consistent with the season totals", () => {
    for (const p of players) {
      expect(Array.isArray(p.matchLog)).toBe(true);
      expect(p.matchLog.length).toBeLessThanOrEqual(p.stats.appearances);
      let logGoals = 0;
      for (const m of p.matchLog) {
        expect(m.opponent).toMatch(/^[A-Z]{3}$/);
        expect(m.minutes).toBeGreaterThanOrEqual(0);
        expect(m.minutes).toBeLessThanOrEqual(120);
        expect(m.goals).toBeGreaterThanOrEqual(0);
        logGoals += m.goals;
      }
      // Per-match goals can't add up to more than the tournament total.
      expect(logGoals).toBeLessThanOrEqual(p.stats.goals);
    }
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
