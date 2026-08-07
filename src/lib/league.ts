import type { IndexData, LeagueRef, Selection } from "./types";

/**
 * League + season selection is carried in the URL as `?league=..&season=..`.
 * Every page reads it server-side; the switcher in the nav pushes new values.
 * These helpers keep that logic in one place and validate against the
 * catalogue (index.json) so a bad query string always falls back to a real
 * dataset instead of 500-ing.
 */

export const LEAGUE_PARAM = "league";
export const SEASON_PARAM = "season";

export type SearchParams = Record<string, string | string[] | undefined>;

function first(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v;
}

/** Resolve a validated {league, season} from raw search params. */
export function resolveSelection(index: IndexData, params: SearchParams): Selection {
  const league = first(params[LEAGUE_PARAM]);
  const season = first(params[SEASON_PARAM]);

  const leagueRef =
    index.leagues.find((l) => l.id === league) ??
    index.leagues.find((l) => l.id === index.default.league) ??
    index.leagues[0];

  const seasonRef =
    leagueRef.seasons.find((s) => s.id === season) ??
    leagueRef.seasons.find((s) => s.id === index.default.season) ??
    leagueRef.seasons[0];

  return { league: leagueRef.id, season: seasonRef.id };
}

/** Build a URL that preserves the current selection as query params. */
export function withSelection(path: string, sel: Selection, extra?: Record<string, string>): string {
  const usp = new URLSearchParams();
  usp.set(LEAGUE_PARAM, sel.league);
  usp.set(SEASON_PARAM, sel.season);
  if (extra) for (const [k, v] of Object.entries(extra)) usp.set(k, v);
  return `${path}?${usp.toString()}`;
}

export function leagueRef(index: IndexData, id: string): LeagueRef {
  return index.leagues.find((l) => l.id === id) ?? index.leagues[0];
}

/** A vivid, accessible accent per league for UI chrome (buttons/highlights). */
export const LEAGUE_ACCENT: Record<string, string> = {
  epl: "#a855f7", // electric violet (Premier League identity)
  laliga: "#ff5a5f", // vivid red (La Liga identity)
  ucl: "#2f6bff", // UEFA Champions League blue (starball identity)
};

export function accentFor(league: string): string {
  return LEAGUE_ACCENT[league] ?? "#6366f1";
}

/** European qualification / relegation zones per league (matches the pipeline). */
export const LEAGUE_ZONES: Record<string, { ucl: number; europa: number; releg: number }> = {
  epl: { ucl: 5, europa: 7, releg: 3 },
  laliga: { ucl: 5, europa: 7, releg: 3 },
};

export function zonesFor(league: string): { ucl: number; europa: number; releg: number } {
  return LEAGUE_ZONES[league] ?? { ucl: 4, europa: 6, releg: 3 };
}

export interface ZoneConfig {
  ucl: number;
  europa: number;
  releg: number;
  labels: { ucl: string; europa: string; releg: string };
}

const DOMESTIC_ZONE_LABELS = {
  ucl: "Champions League",
  europa: "Europa League",
  releg: "Relegation",
};
/**
 * The Champions League "league phase" is a 36-team table: the top 8 go straight
 * to the Round of 16, 9th–24th enter the knockout play-offs, and 25th–36th are
 * eliminated. Those are the zone semantics for a tournament dataset.
 */
const TOURNAMENT_ZONE_LABELS = {
  ucl: "Round of 16",
  europa: "Knockout play-offs",
  releg: "Eliminated",
};

/** Zone thresholds + human labels, tournament-aware via the dataset `format`. */
export function zoneConfigFor(league: string, format?: string): ZoneConfig {
  if (format === "tournament") {
    return { ucl: 8, europa: 24, releg: 12, labels: TOURNAMENT_ZONE_LABELS };
  }
  return { ...zonesFor(league), labels: DOMESTIC_ZONE_LABELS };
}

export interface OddsLabels {
  title: string;
  ucl: string;
  europa: string;
  relegation: string;
}

/** Metric labels for the season-odds toggle, tournament-aware. */
export function oddsLabelsFor(format?: string): OddsLabels {
  if (format === "tournament") {
    return {
      title: "Win trophy",
      ucl: "Reach last 16",
      europa: "Reach knockouts",
      relegation: "Eliminated",
    };
  }
  return {
    title: "Win title",
    ucl: "Champions League",
    europa: "Europa League",
    relegation: "Relegation",
  };
}

/** The query string that pins the current selection onto internal links. */
export function queryFor(sel: Selection): string {
  return `?${LEAGUE_PARAM}=${sel.league}&${SEASON_PARAM}=${sel.season}`;
}
