/**
 * Client-component render safety tests (plain Node env, no jsdom).
 *
 * The HTTP crawler only exercises the server-rendered *skeleton* of the
 * players / matches explorers (they fetch their data in the browser) and never
 * mounts the click-only prediction modal. These tests close that gap by
 * rendering the real components against the real cached JSON with
 * `renderToStaticMarkup`, which executes each component's body — the exact code
 * that runs client-side on click. A missing/undefined field (e.g. `scorers`,
 * `prediction.models`, `topFactors`) would throw here just as it would in the
 * browser.
 */
import * as React from "react";
import fs from "node:fs";
import path from "node:path";
import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { PredictionModal } from "@/components/match/prediction-modal";
import { MatchCard } from "@/components/match/match-card";
import { PlayerAvatar } from "@/components/player-avatar";
import { RatingPill } from "@/components/rating-pill";
import { Flag } from "@/components/flag";
import { ClubBadge } from "@/components/club-badge";
import { buildModelMeta } from "@/lib/model-meta";
import type { Match, ModelsData, Player, Club } from "@/lib/types";

const DATA = path.join(process.cwd(), "public", "data");

interface IndexShape {
  datasets: { league: string; season: string }[];
}
// Derive the dataset matrix from the catalogue so it always tracks whatever the
// pipeline shipped (e.g. UCL rolling from 2024-25 to 2026-27) — never a stale
// hardcoded list that 404s when a season is retired.
const DATASETS = (
  JSON.parse(fs.readFileSync(path.join(DATA, "index.json"), "utf8")) as IndexShape
).datasets.map((d) => [d.league, d.season] as const);

function readJson<T>(league: string, season: string, file: string): T {
  return JSON.parse(fs.readFileSync(path.join(DATA, league, season, file), "utf8")) as T;
}

describe("PredictionModal mounts for every match in every dataset", () => {
  for (const [league, season] of DATASETS) {
    it(`${league}/${season}`, () => {
      const matches = readJson<Match[]>(league, season, "matches.json");
      const models = readJson<ModelsData>(league, season, "models.json");
      const modelMeta = buildModelMeta(models.leaderboard);
      // A preseason tournament (draw pending) legitimately ships 0 fixtures; the
      // per-match loop simply doesn't run. Every other dataset must have games.
      const isCupPreseason = league === "ucl" && matches.length === 0;
      if (!isCupPreseason) expect(matches.length).toBeGreaterThan(0);
      // Executes the modal body (scorers/models/topFactors access) per match.
      for (const m of matches) {
        expect(() =>
          renderToStaticMarkup(
            <PredictionModal match={m} open onOpenChange={() => {}} modelMeta={modelMeta} />,
          ),
        ).not.toThrow();
      }
    });
  }
});

describe("MatchCard renders for every match in every dataset", () => {
  for (const [league, season] of DATASETS) {
    it(`${league}/${season}`, () => {
      const matches = readJson<Match[]>(league, season, "matches.json");
      for (const m of matches) {
        expect(() =>
          renderToStaticMarkup(<MatchCard match={m} onOpenPrediction={() => {}} />),
        ).not.toThrow();
      }
    });
  }
});

describe("Player row leaf components render for every player", () => {
  for (const [league, season] of DATASETS) {
    it(`${league}/${season}`, () => {
      const players = readJson<{ players: Player[] }>(league, season, "players.json").players;
      expect(players.length).toBeGreaterThan(0);
      // Mirrors the exact leaf components a players-explorer row renders.
      for (const p of players) {
        expect(() =>
          renderToStaticMarkup(
            <div>
              <PlayerAvatar name={p.name} src={p.headshot} size="sm" />
              <Flag iso2={p.nationIso2} size="sm" />
              <RatingPill rating={Math.round(p.rating)} />
              <span>{p.goals}</span>
              <span>{p.assists ?? "—"}</span>
              <span>{p.clubName}</span>
              <span>{p.nationName}</span>
              <span>{p.position}</span>
            </div>,
          ),
        ).not.toThrow();
      }
    });
  }
});

describe("ClubBadge renders for every club in every dataset", () => {
  for (const [league, season] of DATASETS) {
    it(`${league}/${season}`, () => {
      const clubs = readJson<Club[]>(league, season, "clubs.json");
      for (const c of clubs) {
        expect(() =>
          renderToStaticMarkup(
            <ClubBadge code={c.code} primary={c.primary} secondary={c.secondary} />,
          ),
        ).not.toThrow();
      }
    });
  }
});
