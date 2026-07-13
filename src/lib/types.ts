/**
 * Shared data contract for the 2026 World Cup dashboard.
 *
 * These types describe the JSON files produced by the Python ML pipeline
 * (see /ml) and consumed by the Next.js frontend. The pipeline writes the
 * canonical files to `public/data/*.json`; keep this file in sync with the
 * pipeline's serialisers (ml/predict.py, ml/evaluate.py, ml/ingest.py).
 */

export type Confederation =
  | "UEFA"
  | "CONMEBOL"
  | "CONCACAF"
  | "CAF"
  | "AFC"
  | "OFC";

export type MatchStatus = "completed" | "upcoming" | "live";

export type Stage =
  | "group"
  | "round-of-32"
  | "round-of-16"
  | "quarter-final"
  | "semi-final"
  | "third-place"
  | "final";

export type Position = "GK" | "DEF" | "MID" | "FWD";

export type Outcome = "home" | "draw" | "away";

export interface TeamColors {
  primary: string;
  secondary: string;
}

export interface TeamRef {
  code: string;
  iso2: string;
  name: string;
  colors: TeamColors;
}

export interface TeamRecord {
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
  groupRank: number | null;
}

export interface AdvanceProbabilities {
  roundOf32: number;
  roundOf16: number;
  quarter: number;
  semi: number;
  final: number;
  champion: number;
}

export interface TeamStrength {
  overall: number;
  attack: number;
  defense: number;
  form: number;
  squad: number;
  momentum: number;
  experience: number;
}

export interface ProbPoint {
  label: string;
  prob: number;
}

export interface Team {
  code: string;
  iso2: string;
  name: string;
  confederation: Confederation;
  group: string;
  colors: TeamColors;
  elo: number;
  eloInitial: number;
  fifaRank: number;
  status: "active" | "eliminated";
  eliminatedRound: Stage | null;
  strength: TeamStrength;
  record: TeamRecord;
  championProb: number;
  advance: AdvanceProbabilities;
  strengths: string[];
  weaknesses: string[];
  keyPlayerIds: string[];
  championProbHistory: ProbPoint[];
}

export interface ModelPrediction {
  model: string;
  modelName: string;
  probs: { home: number; draw: number; away: number };
  predictedOutcome: Outcome;
  winner: string;
  winnerCode: string | null;
  confidence: number;
  /** Backtest accuracy of this model so far (0-1), for context in the modal. */
  accuracy: number;
}

export interface MatchFactor {
  label: string;
  detail: string;
  favors: "home" | "away" | "neutral";
  weight: number;
}

export interface Match {
  id: string;
  stage: Stage;
  stageLabel: string;
  group: string | null;
  round: number;
  datetime: string;
  venue: string;
  city: string;
  status: MatchStatus;
  home: TeamRef;
  away: TeamRef;
  score: { home: number; away: number } | null;
  penalties: { home: number; away: number } | null;
  actualOutcome: Outcome | null;
  ensemble: ModelPrediction;
  models: ModelPrediction[];
  factors: MatchFactor[];
  predictedOutcome: Outcome;
  correct: boolean | null;
  projectedMatchup: boolean;
}

export interface PlayerStats {
  /** Real 2026 World Cup tournament stats (Wikipedia / FIFA match reports). */
  appearances: number;
  minutes: number;
  goals: number;
  /** Not published in any free World Cup source — always null, shown as "—". */
  assists: number | null;
  yellowCards: number;
  redCards: number;
  /** Goalkeepers only (null for outfield players). */
  cleanSheets: number | null;
  goalsConceded: number | null;
}

export interface PhotoCredit {
  author: string;
  license: string;
  sourceUrl: string;
}

export interface Player {
  id: string;
  name: string;
  countryCode: string;
  country: string;
  iso2: string;
  position: Position;
  detailedPosition: string;
  shirtNumber: number;
  age: number | null;
  club: string;
  clubCountry: string;
  rating: number;
  contribution: number;
  isCaptain: boolean;
  isKeyPlayer: boolean;
  /** True when the identity (name, position, age, caps, club) is real (Wikipedia). */
  real: boolean;
  caps: number | null;
  intlGoals: number | null;
  /** Free-licensed headshot path (public/headshots/…), or null for an initials avatar. */
  headshot: string | null;
  photoCredit: PhotoCredit | null;
  stats: PlayerStats;
  /** Real per-match tournament log (most recent first-to-last), Wikipedia. */
  matchLog: PlayerMatch[];
  bio: string;
}

export interface PlayerMatch {
  date: string | null;
  /** Opponent 3-letter code. */
  opponent: string;
  goalsFor: number;
  goalsAgainst: number;
  minutes: number;
  goals: number;
  yellow: number;
  red: number;
  started: boolean;
}

export interface CalibrationBin {
  predicted: number;
  observed: number;
  count: number;
}

export interface FeatureImportance {
  feature: string;
  label: string;
  importance: number;
}

export interface ModelInfo {
  id: string;
  name: string;
  type: "baseline" | "linear" | "tree" | "boosting" | "ensemble";
  description: string;
  accuracy: number;
  logLoss: number;
  brier: number;
  gamesEvaluated: number;
  avgConfidence: number;
  ece: number;
  weight: number;
  rank: number;
  lastUpdated: string;
  calibration: CalibrationBin[];
  featureImportance: FeatureImportance[];
  strengths: string;
  note: string | null;
}

export interface RankingEntry {
  code: string;
  name: string;
  iso2: string;
  value: number;
  rank: number;
  confederation: Confederation;
  group: string;
}

export interface RankingView {
  id: string;
  name: string;
  description: string;
  unit: string;
  format: "percent" | "number" | "rating";
  entries: RankingEntry[];
}

export interface Rankings {
  views: RankingView[];
}

export interface BracketMatch {
  id: string;
  stage: Stage;
  slot: number;
  home: string | null;
  away: string | null;
  homeProjected: boolean;
  awayProjected: boolean;
  score: { home: number; away: number } | null;
  penalties: { home: number; away: number } | null;
  winner: string | null;
  status: MatchStatus;
  homeProb: number | null;
  awayProb: number | null;
}

export interface BracketRound {
  stage: Stage;
  label: string;
  matches: BracketMatch[];
}

export interface Bracket {
  rounds: BracketRound[];
}

export interface ChampionOdd {
  code: string;
  name: string;
  iso2: string;
  prob: number;
}

export interface Summary {
  tournament: string;
  host: string;
  asOf: string;
  cutoff: string;
  generatedAt: string;
  totalMatches: number;
  matchesCompleted: number;
  matchesUpcoming: number;
  matchesLive: number;
  teamCount: number;
  playerCount: number;
  modelCount: number;
  featureCount: number;
  trainingMatches: number;
  topChampion: ChampionOdd;
  topContenders: ChampionOdd[];
  highestConfidenceMatchId: string;
  bestModel: {
    id: string;
    name: string;
    accuracy: number;
    logLoss: number;
    brier: number;
  };
  ensembleAccuracy: number;
  dataMode: "generated" | "cached" | "live";
}

export interface Methodology {
  pipeline: { id: string; title: string; description: string; outputs: string[] }[];
  dataSources: {
    name: string;
    kind: "generated" | "cached" | "live" | "static";
    description: string;
    license: string;
  }[];
  features: FeatureImportance[];
  models: { id: string; name: string; summary: string }[];
  notes: string[];
  generatedAt: string;
}
