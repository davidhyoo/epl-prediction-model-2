import "server-only";
import { cache } from "react";
import { promises as fs } from "node:fs";
import path from "node:path";
import type {
  Club,
  Dataset,
  IndexData,
  Match,
  ModelsData,
  Player,
  PlayersData,
  Rankings,
  Selection,
  Standing,
  Summary,
  TitleRace,
} from "./types";
import { resolveSelection, type SearchParams } from "./league";

const DATA_DIR = path.join(process.cwd(), "public", "data");

async function readJson<T>(...segments: string[]): Promise<T> {
  const file = path.join(DATA_DIR, ...segments);
  const raw = await fs.readFile(file, "utf-8");
  return JSON.parse(raw) as T;
}

/** The dataset catalogue (available leagues/seasons + default). */
export const getIndex = cache(() => readJson<IndexData>("index.json"));

/** Resolve the selection for a request from its search params. */
export const getSelection = cache(async (params: SearchParams): Promise<Selection> => {
  const index = await getIndex();
  return resolveSelection(index, params);
});

export const getSummary = cache((sel: Selection) =>
  readJson<Summary>(sel.league, sel.season, "summary.json"),
);
export const getStandings = cache((sel: Selection) =>
  readJson<Standing[]>(sel.league, sel.season, "standings.json"),
);
export const getMatches = cache((sel: Selection) =>
  readJson<Match[]>(sel.league, sel.season, "matches.json"),
);
export const getModels = cache((sel: Selection) =>
  readJson<ModelsData>(sel.league, sel.season, "models.json"),
);
export const getClubs = cache((sel: Selection) =>
  readJson<Club[]>(sel.league, sel.season, "clubs.json"),
);
export const getPlayersData = cache((sel: Selection) =>
  readJson<PlayersData>(sel.league, sel.season, "players.json"),
);
export const getRankings = cache((sel: Selection) =>
  readJson<Rankings>(sel.league, sel.season, "rankings.json"),
);
export const getRace = cache((sel: Selection) =>
  readJson<TitleRace>(sel.league, sel.season, "race.json"),
);

export const getPlayers = cache(async (sel: Selection): Promise<Player[]> => {
  const data = await getPlayersData(sel);
  return data.players;
});

/** Load every file for a dataset in one shot (used by pages needing several). */
export const getDataset = cache(async (sel: Selection): Promise<Dataset> => {
  const [summary, standings, matches, models, clubs, playersData, rankings] = await Promise.all([
    getSummary(sel),
    getStandings(sel),
    getMatches(sel),
    getModels(sel),
    getClubs(sel),
    getPlayersData(sel),
    getRankings(sel),
  ]);
  return {
    selection: sel,
    summary,
    standings,
    matches,
    models,
    clubs,
    players: playersData.players,
    topScorers: playersData.topScorers,
    rankings,
  };
});

/* ------------------------------------------------------------------ */
/*  Lookups                                                            */
/* ------------------------------------------------------------------ */

export const getClubByCode = cache(async (sel: Selection, code: string): Promise<Club | undefined> => {
  const clubs = await getClubs(sel);
  return clubs.find((c) => c.code.toLowerCase() === code.toLowerCase());
});

export const getPlayerById = cache(async (sel: Selection, id: string): Promise<Player | undefined> => {
  const players = await getPlayers(sel);
  return players.find((p) => p.id === id);
});

export const getPlayersByClub = cache(async (sel: Selection, code: string): Promise<Player[]> => {
  const players = await getPlayers(sel);
  return players
    .filter((p) => p.club.toLowerCase() === code.toLowerCase())
    .sort((a, b) => b.rating - a.rating);
});

export const getMatchesForClub = cache(async (sel: Selection, code: string): Promise<Match[]> => {
  const matches = await getMatches(sel);
  return matches
    .filter((m) => m.home.code === code || m.away.code === code)
    .sort((a, b) => new Date(a.datetime).getTime() - new Date(b.datetime).getTime());
});

export const getMatchById = cache(async (sel: Selection, id: string): Promise<Match | undefined> => {
  const matches = await getMatches(sel);
  return matches.find((m) => m.id === id);
});

/** Lightweight index for the command palette / search. */
export const getSearchIndex = cache(async (sel: Selection) => {
  const [clubs, players] = await Promise.all([getClubs(sel), getPlayers(sel)]);
  return {
    clubs: clubs.map((c) => ({
      code: c.code,
      name: c.name,
      short: c.short,
      position: c.standing.position,
      title: c.odds.title,
    })),
    players: players.map((p) => ({
      id: p.id,
      name: p.name,
      club: p.club,
      clubName: p.clubName,
      nationIso2: p.nationIso2,
      position: p.position,
    })),
  };
});
