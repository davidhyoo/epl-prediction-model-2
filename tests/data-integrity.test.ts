import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import type {
  Club,
  IndexData,
  Match,
  ModelsData,
  PlayersData,
  Rankings,
  Standing,
  Summary,
} from "@/lib/types";

const DATA = path.join(process.cwd(), "public", "data");
const read = <T>(...seg: string[]): T =>
  JSON.parse(readFileSync(path.join(DATA, ...seg), "utf-8")) as T;

const index = read<IndexData>("index.json");

const sumsToOne = (a: number, b: number, c: number, tol = 0.02) =>
  Math.abs(a + b + c - 1) < tol;

describe("index.json", () => {
  it("declares a default dataset that exists in the catalogue", () => {
    const { league, season } = index.default;
    expect(index.datasets.some((d) => d.league === league && d.season === season)).toBe(true);
  });

  it("lists two leagues, each with a validation and a deliverable season", () => {
    expect(index.leagues.length).toBeGreaterThanOrEqual(2);
    for (const lg of index.leagues) {
      const roles = lg.seasons.map((s) => s.role);
      expect(roles).toContain("validation");
      expect(roles).toContain("deliverable");
    }
  });
});

// Validate every published dataset the catalogue advertises.
for (const ds of index.datasets) {
  const label = `${ds.league}/${ds.season}`;
  const dir = [ds.league, ds.season];

  describe(`dataset ${label}`, () => {
    const summary = read<Summary>(...dir, "summary.json");
    const standings = read<Standing[]>(...dir, "standings.json");
    const matches = read<Match[]>(...dir, "matches.json");
    const models = read<ModelsData>(...dir, "models.json");
    const clubs = read<Club[]>(...dir, "clubs.json");
    const playersData = read<PlayersData>(...dir, "players.json");
    const rankings = read<Rankings>(...dir, "rankings.json");
    const players = playersData.players;
    const preseason = summary.played === 0;

    it("has a 20-club, 380-match league season", () => {
      expect(clubs).toHaveLength(20);
      expect(standings).toHaveLength(20);
      expect(matches).toHaveLength(380);
      expect(summary.totalMatches).toBe(380);
    });

    it("reconciles the completed/upcoming split with the schedule", () => {
      const completed = matches.filter((m) => m.status === "completed").length;
      const notCompleted = matches.length - completed;
      expect(summary.played).toBe(completed);
      expect(summary.upcoming).toBe(notCompleted);
      expect(summary.played + summary.upcoming).toBe(matches.length);
    });

    it("gives every match calibrated probabilities that sum to 1", () => {
      for (const m of matches) {
        const e = m.prediction.ensemble;
        expect(sumsToOne(e.home, e.draw, e.away)).toBe(true);
        for (const probs of Object.values(m.prediction.models)) {
          expect(sumsToOne(probs.home, probs.draw, probs.away)).toBe(true);
        }
        expect(["home", "draw", "away"]).toContain(m.prediction.predicted);
      }
    });

    it("never leaks results: only completed matches carry a score + graded prediction", () => {
      for (const m of matches) {
        if (m.status === "completed") {
          expect(m.homeGoals).not.toBeNull();
          expect(m.awayGoals).not.toBeNull();
          expect(m.actual).not.toBeNull();
          expect(typeof m.predictionCorrect).toBe("boolean");
        } else {
          expect(m.homeGoals).toBeNull();
          expect(m.awayGoals).toBeNull();
          // Preseason matches omit these keys entirely; graded fields must be
          // absent or null, never a real outcome.
          expect(m.actual ?? null).toBeNull();
          expect(m.predictionCorrect ?? null).toBeNull();
        }
      }
    });

    it("grades each completed prediction consistently with the actual result", () => {
      for (const m of matches) {
        if (m.status !== "completed") continue;
        const hg = m.homeGoals as number;
        const ag = m.awayGoals as number;
        const actual = hg > ag ? "home" : hg < ag ? "away" : "draw";
        expect(m.actual).toBe(actual);
        expect(m.predictionCorrect).toBe(m.prediction.predicted === actual);
      }
    });

    it("produces a standings table with unique positions 1..20", () => {
      const positions = standings.map((s) => s.position).sort((a, b) => a - b);
      expect(positions).toEqual(Array.from({ length: 20 }, (_, i) => i + 1));
      for (const s of standings) {
        expect(s.pts).toBe(s.win * 3 + s.draw);
        expect(s.played).toBe(s.win + s.draw + s.loss);
        expect(s.gd).toBe(s.gf - s.ga);
      }
    });

    it("keeps every season-odds fraction inside [0, 1] with a valid position distribution", () => {
      for (const c of clubs) {
        for (const v of [c.odds.title, c.odds.ucl, c.odds.europa, c.odds.relegation]) {
          expect(v).toBeGreaterThanOrEqual(0);
          expect(v).toBeLessThanOrEqual(1);
        }
        expect(c.odds.positionDist).toHaveLength(20);
        const distTotal = c.odds.positionDist.reduce((s, x) => s + x, 0);
        expect(Math.abs(distTotal - 1)).toBeLessThan(0.02);
      }
      // Title odds across the league sum to ~1 (exactly one champion).
      const titleTotal = clubs.reduce((s, c) => s + c.odds.title, 0);
      expect(Math.abs(titleTotal - 1)).toBeLessThan(0.02);
    });

    it("ranks the model leaderboard 1..N with a self-normalising ensemble", () => {
      if (preseason) {
        // No completed matches yet: models are unranked until backtesting runs.
        for (const m of models.leaderboard) {
          expect(m.rank).toBeNull();
        }
      } else {
        const ranks = models.leaderboard.map((m) => m.rank).sort((a, b) => (a as number) - (b as number));
        expect(ranks).toEqual(models.leaderboard.map((_, i) => i + 1));
      }
      const weightTotal = Object.values(models.weights).reduce((s, w) => s + w, 0);
      if (Object.keys(models.weights).length > 0) {
        expect(Math.abs(weightTotal - 1)).toBeLessThan(0.02);
      }
      for (const m of models.leaderboard) {
        for (const bin of m.calibration) {
          expect(bin.predicted).toBeGreaterThanOrEqual(0);
          expect(bin.predicted).toBeLessThanOrEqual(1);
          expect(bin.observed).toBeGreaterThanOrEqual(0);
          expect(bin.observed).toBeLessThanOrEqual(1);
        }
      }
    });

    it("evaluates models only when there are completed matches", () => {
      if (preseason) {
        expect(models.meta.evaluated).toBe(0);
        for (const m of models.leaderboard) {
          expect(m.accuracy).toBeNull();
          expect(m.gamesEvaluated).toBe(0);
        }
      } else {
        expect(models.meta.evaluated).toBe(summary.played);
        for (const m of models.leaderboard) {
          expect(m.accuracy).toBeGreaterThanOrEqual(0);
          expect(m.accuracy).toBeLessThanOrEqual(1);
          expect(Number.isFinite(m.logLoss as number)).toBe(true);
          expect(Number.isFinite(m.brier as number)).toBe(true);
        }
      }
    });

    it("carries a real, credited squad with sane ratings", () => {
      expect(players.length).toBeGreaterThan(300);
      const codes = new Set(clubs.map((c) => c.code));
      for (const p of players) {
        expect(codes.has(p.club)).toBe(true);
        expect(["GK", "DEF", "MID", "FWD"]).toContain(p.position);
        expect(p.rating).toBeGreaterThanOrEqual(30);
        expect(p.rating).toBeLessThanOrEqual(100);
        expect(p.goals).toBeGreaterThanOrEqual(0);
      }
      // Ratings must be spread out, not clamped to one ceiling value.
      const distinct = new Set(players.map((p) => Math.round(p.rating))).size;
      expect(distinct).toBeGreaterThan(20);
    });

    it("attaches only well-formed, attributed headshots", () => {
      const withPhoto = players.filter((p) => p.headshot);
      expect(withPhoto.length).toBeGreaterThan(0);
      for (const p of withPhoto) {
        expect(p.headshot).toMatch(new RegExp(`^/headshots/${ds.league}/[^/]+\\.jpg$`));
        expect(p.photoCredit?.author).toBeTruthy();
        expect(p.photoCredit?.license).toBeTruthy();
        expect(p.photoCredit?.sourceUrl).toMatch(/^https?:\/\//);
      }
    });

    it("keeps top scorers pointing at real players ordered by goals", () => {
      const byId = new Map(players.map((p) => [p.id, p]));
      let prev = Infinity;
      for (const id of playersData.topScorers) {
        const p = byId.get(id);
        expect(p).toBeDefined();
        expect((p as (typeof players)[number]).goals).toBeLessThanOrEqual(prev);
        prev = (p as (typeof players)[number]).goals;
      }
    });

    it("exposes eight ranking views, each covering all 20 clubs", () => {
      const keys = Object.keys(rankings);
      expect(keys).toHaveLength(8);
      for (const key of keys) {
        expect(rankings[key as keyof Rankings]).toHaveLength(20);
      }
    });
  });
}
