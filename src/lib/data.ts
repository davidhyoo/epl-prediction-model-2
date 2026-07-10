import "server-only";
import { cache } from "react";
import { promises as fs } from "node:fs";
import path from "node:path";
import type {
  Bracket,
  Match,
  Methodology,
  ModelInfo,
  Player,
  Rankings,
  Summary,
  Team,
} from "./types";

const DATA_DIR = path.join(process.cwd(), "public", "data");

async function readData<T>(name: string): Promise<T> {
  const file = path.join(DATA_DIR, name);
  const raw = await fs.readFile(file, "utf-8");
  return JSON.parse(raw) as T;
}

export const getSummary = cache(() => readData<Summary>("summary.json"));
export const getTeams = cache(() => readData<Team[]>("teams.json"));
export const getMatches = cache(() => readData<Match[]>("matches.json"));
export const getPlayers = cache(() => readData<Player[]>("players.json"));
export const getModels = cache(() => readData<ModelInfo[]>("models.json"));
export const getRankings = cache(() => readData<Rankings>("rankings.json"));
export const getBracket = cache(() => readData<Bracket>("bracket.json"));
export const getMethodology = cache(() => readData<Methodology>("methodology.json"));

export const getTeamByCode = cache(async (code: string): Promise<Team | undefined> => {
  const teams = await getTeams();
  return teams.find((t) => t.code.toLowerCase() === code.toLowerCase());
});

export const getPlayerById = cache(async (id: string): Promise<Player | undefined> => {
  const players = await getPlayers();
  return players.find((p) => p.id === id);
});

export const getPlayersByCountry = cache(async (code: string): Promise<Player[]> => {
  const players = await getPlayers();
  return players
    .filter((p) => p.countryCode.toLowerCase() === code.toLowerCase())
    .sort((a, b) => b.rating - a.rating);
});

export const getMatchesForTeam = cache(async (code: string): Promise<Match[]> => {
  const matches = await getMatches();
  return matches
    .filter((m) => m.home.code === code || m.away.code === code)
    .sort((a, b) => new Date(a.datetime).getTime() - new Date(b.datetime).getTime());
});

export const getMatchById = cache(async (id: string): Promise<Match | undefined> => {
  const matches = await getMatches();
  return matches.find((m) => m.id === id);
});

/** Lightweight index for the command palette / search. */
export const getSearchIndex = cache(async () => {
  const [teams, players] = await Promise.all([getTeams(), getPlayers()]);
  return {
    teams: teams.map((t) => ({
      code: t.code,
      iso2: t.iso2,
      name: t.name,
      group: t.group,
      championProb: t.championProb,
    })),
    players: players.map((p) => ({
      id: p.id,
      name: p.name,
      country: p.country,
      iso2: p.iso2,
      position: p.position,
      club: p.club,
    })),
  };
});
