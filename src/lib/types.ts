/**
 * Shared data contract for the Data Driven Soccer league dashboard (EPL + La Liga).
 *
 * These types describe the JSON files produced by the Python ML pipeline
 * (see /ml, in particular ml/club_evaluate.py) and consumed by the Next.js
 * frontend. The pipeline writes one folder per dataset:
 *
 *   public/data/{league}/{season}/{summary,standings,matches,models,clubs,players,rankings}.json
 *   public/data/index.json   (catalogue of available datasets + the default)
 *
 * Keep this file in sync with ml/club_evaluate.py.
 */

export type Outcome = "home" | "draw" | "away";
export type MatchStatus = "completed" | "upcoming" | "live";
export type Position = "GK" | "DEF" | "MID" | "FWD";
export type SeasonRole = "validation" | "deliverable";

/* ------------------------------------------------------------------ */
/*  Catalogue (index.json)                                             */
/* ------------------------------------------------------------------ */

export interface SeasonRef {
  id: string;
  label: string;
  role: SeasonRole;
}

export interface LeagueRef {
  id: string;
  name: string;
  short: string;
  country: string;
  iso2: string;
  accent: string;
  seasons: SeasonRef[];
}

export interface DatasetRef {
  league: string;
  season: string;
  played: number;
  players: number;
}

export interface IndexData {
  generatedAt: string;
  default: { league: string; season: string };
  leagues: LeagueRef[];
  datasets: DatasetRef[];
}

/** A validated {league, season} selection resolved from the URL. */
export interface Selection {
  league: string;
  season: string;
}

/* ------------------------------------------------------------------ */
/*  summary.json                                                       */
/* ------------------------------------------------------------------ */

export interface LeagueMeta {
  id: string;
  name: string;
  short: string;
  country: string;
  iso2: string;
  accent: string;
}

export interface Summary {
  league: LeagueMeta;
  season: SeasonRef;
  lastUpdated: string;
  totalMatches: number;
  played: number;
  upcoming: number;
  clubs: number;
  champion: { code: string; name: string; probability: number } | null;
  topScorer: { id: string; name: string; club: string; goals: number } | null;
  bestModel: { id: string; name: string; accuracy: number } | null;
  highestConfidence:
    | { id: string; home: string; away: string; predicted: Outcome; confidence: number }
    | null;
}

/* ------------------------------------------------------------------ */
/*  standings.json                                                     */
/* ------------------------------------------------------------------ */

export type FormResult = "W" | "D" | "L";

export interface Standing {
  code: string;
  played: number;
  win: number;
  draw: number;
  loss: number;
  gf: number;
  ga: number;
  gd: number;
  pts: number;
  form: FormResult[];
  expectedPoints: number;
  position: number;
}

/* ------------------------------------------------------------------ */
/*  matches.json                                                       */
/* ------------------------------------------------------------------ */

export interface ClubRef {
  code: string;
  name: string;
  short: string;
  primary: string;
  secondary: string;
  wiki: string;
}

export interface Probabilities {
  home: number;
  draw: number;
  away: number;
}

export interface MatchFactor {
  feature: string;
  label: string;
  value: number;
  impact: number;
  direction: Outcome;
}

export interface MatchPrediction {
  ensemble: Probabilities;
  models: Record<string, Probabilities>;
  predicted: Outcome;
  confidence: number;
  topFactors: MatchFactor[];
}

export interface Scorer {
  player: string;
  team: string;
  minute: string;
  penalty: boolean;
  ownGoal: boolean;
}

export interface MatchStats {
  shots?: { home: number; away: number };
  shotsOnTarget?: { home: number; away: number };
  corners?: { home: number; away: number };
  fouls?: { home: number; away: number };
  yellows?: { home: number; away: number };
  reds?: { home: number; away: number };
  marketOdds?: Probabilities;
  referee?: string | null;
}

export interface Match {
  id: string;
  round: number;
  date: string;
  datetime: string;
  status: MatchStatus;
  home: ClubRef;
  away: ClubRef;
  homeGoals: number | null;
  awayGoals: number | null;
  eloHome: number;
  eloAway: number;
  prediction: MatchPrediction;
  scorers: Scorer[];
  matchStats: MatchStats | null;
  marketOdds: Probabilities | null;
  actual: Outcome | null;
  predictionCorrect: boolean | null;
}

/* ------------------------------------------------------------------ */
/*  models.json                                                        */
/* ------------------------------------------------------------------ */

export interface CalibrationBin {
  predicted: number;
  observed: number;
  count: number;
}

export interface ModelEntry {
  id: string;
  name: string;
  blurb: string;
  weight: number;
  accuracy: number | null;
  logLoss: number | null;
  brier: number | null;
  avgConfidence: number | null;
  ece: number | null;
  calibration: CalibrationBin[];
  gamesEvaluated: number;
  rank: number;
}

export interface ModelsData {
  leaderboard: ModelEntry[];
  meta: { evaluated: number };
  weights: Record<string, number>;
}

/* ------------------------------------------------------------------ */
/*  clubs.json                                                         */
/* ------------------------------------------------------------------ */

export interface ClubStrength {
  elo: number;
  overall: number;
  attack: number;
  defense: number;
  form: number;
  gfAvg: number;
  gaAvg: number;
  ppg: number;
}

export interface ClubOdds {
  title: number;
  ucl: number;
  europa: number;
  relegation: number;
  expectedPoints: number;
  expectedPosition: number;
  positionDist: number[];
  maxPoints: number;
  canWinTitle: boolean;
}

export interface Club {
  code: string;
  name: string;
  short: string;
  primary: string;
  secondary: string;
  wiki: string;
  standing: Standing;
  strength: ClubStrength;
  odds: ClubOdds;
  keyPlayers: string[];
  squadSize: number;
  playedMatches: string[];
  upcomingMatches: string[];
  strengthsText: string[];
  weaknessesText: string[];
}

/* ------------------------------------------------------------------ */
/*  players.json                                                       */
/* ------------------------------------------------------------------ */

export interface PhotoCredit {
  author: string;
  license: string;
  sourceUrl: string;
}

export interface Player {
  id: string;
  name: string;
  wiki: string | null;
  club: string;
  clubName: string;
  position: Position;
  detailedPosition: string;
  shirtNumber: number | null;
  nationIso2: string;
  nationName: string;
  headshot: string | null;
  photoCredit: PhotoCredit | null;
  goals: number;
  penalties: number;
  goalMinutes: string[];
  assists: number | null;
  appearances: number | null;
  minutes: number | null;
  yellowCards: number | null;
  redCards: number | null;
  clubStrength: number;
  rating: number;
}

export interface PlayersData {
  players: Player[];
  topScorers: string[];
}

/* ------------------------------------------------------------------ */
/*  rankings.json                                                      */
/* ------------------------------------------------------------------ */

export interface RankingEntry {
  code: string;
  value: number;
  rank?: number;
}

export type RankingKey =
  | "title"
  | "strength"
  | "form"
  | "attack"
  | "defense"
  | "squad"
  | "elo"
  | "momentum";

export type Rankings = Record<RankingKey, RankingEntry[]>;

/* ------------------------------------------------------------------ */
/*  Combined dataset bundle                                            */
/* ------------------------------------------------------------------ */

export interface Dataset {
  selection: Selection;
  summary: Summary;
  standings: Standing[];
  matches: Match[];
  models: ModelsData;
  clubs: Club[];
  players: Player[];
  topScorers: string[];
  rankings: Rankings;
}
